# CLAUDE.md

Guidance for agents working in **lgtmaybe** — a provider-agnostic PR reviewer.
Read this before writing code. It encodes decisions that are **made, not options**.

## What this is

A PR reviewer that posts inline review comments + a summary. The user picks the
LLM backend with a `--provider` flag, drops a key into GitHub secrets (or wires
OIDC/WIF for cloud providers), and gets a review. One core, two distribution
variants:

- **PyPI CLI** — `pip install lgtmaybe`
- **GitHub Action** — composite action (`action.yml`) that does keyless OIDC/WIF
  auth, then runs a GHCR image via the `action` entrypoint

**The wedge:** first-class **Bedrock + Vertex with keyless OIDC/WIF**. Five
providers, one flag, no keys in secrets for cloud. We win on auth + simplicity.

## Non-negotiables

- **TDD, always: red → green → refactor.** Write the acceptance test from a
  task's stated in/out *first*, watch it fail, write the minimum code to pass,
  then refactor. CI rejects a PR whose diff adds code without a test.
- **Structured output only.** The model returns JSON (`severity`, `file`,
  `line`, `body`, `suggestion`). Never parse prose.
- **Fork safety.** Trigger on `pull_request_target` so the review has secrets,
  but **never check out or execute PR code** — fetch the diff via API only.
  Treat all diff content as untrusted input.
- **No static cloud keys.** Bedrock uses ambient AWS creds; Vertex uses ambient
  GCP creds. Never accept or require a service-account JSON or static AWS key.

## Key decisions (do not relitigate)

- **Language:** Python.
- **Provider spine:** [litellm] — normalises openai, openrouter, anthropic,
  bedrock, vertex, ollama to one `completion()` call. A thin wrapper on top adds
  retries / fallback.
- **License:** MIT (already in `LICENSE`).
- **Posting:** REST review API — batched inline comments + one summary.
  Idempotent updates via a hidden marker comment.

### Auth model — resolved by provider (chain of responsibility)

| Provider               | Auth                                                              |
|------------------------|------------------------------------------------------------------|
| openai / openrouter / anthropic | API key from `secrets.*` / env / `--api-key`            |
| bedrock                | ambient AWS creds (GitHub OIDC role, or local `~/.aws`); IAM `bedrock:InvokeModel*` only |
| vertex                 | ambient GCP creds (WIF, or local ADC)                            |
| ollama                 | none — just an `api_base` (localhost, host.docker.internal, tailscale host); fully local, zero cost |

Resolver order: chosen provider → try ambient cloud creds if that's its native
mode → else API key → ollama needs neither → else **fail with a clear "how to
auth this provider" message**.

## Architecture — ports & adapters (hexagonal)

This is what lets tracks build in parallel against frozen contracts.

- `core/ports.py` — the ports (interfaces). **Frozen in the foundation step.**
- litellm / github classes — the adapters.
- **Engine is a pipeline:** `fetch → compress → prompt → parse → post`, as
  composable stages. The prompt/parse stage **fans out per `ReviewCategory`** —
  one concurrent model call per lens — and merges + de-dupes the findings.
- **Provider choice:** strategy + factory. The `--provider` flag selects a
  strategy; a small factory builds the `ProviderClient` (litellm keeps it tiny).
- **Credential resolution:** chain of responsibility (see auth table).
- **Dependency injection:** inject ports into the engine — this is what makes
  fakes + dry-run drop in.

**Deliberately skipped** (don't add without a written reason): repository
pattern, event bus, plugin framework.

## Parallel build structure

1. **Foundation (sequential, first):** freeze the contracts in `core/ports.py`,
   plus structured logging for CI debugging. Everything downstream codes against
   these frozen ports.
2. **Parallel tracks**, each against frozen contracts:
   - **Track A** — provider/litellm wrapper: retries, fallback.
   - **Track B** — github adapter + diff handling; **skip generated/binary files**
     (lockfiles, minified, vendored).
   - **Track C** — hardening: **prompt-injection defense** (PR text trying to
     steer the reviewer — `engine/injection.py` wraps the diff as untrusted data
     **and neutralises forged `DIFF_START`/`DIFF_END` delimiters** so an attacker
     diff can't break out of the data block), **secret redaction in diffs before
     they leave for the LLM** (`engine/redact.py` covers AWS/OpenAI/GitHub
     (classic + fine-grained)/Slack/Google/Stripe keys, PEM private-key blocks,
     and quoted password / `Authorization` / connection-string credentials),
     fork-PR exposure (already handled by `pull_request_target` + no checkout).
   - **CLI track** — PyPI packaging; a local `lgtmaybe review` of your `git` diff
     (prints findings, no GitHub) for local dev.
3. **Integration (sequential, last) — DONE:** the tracks are wired together.
   `cli.build_review_context` swaps the fakes for the real `LiteLLMProvider` +
   `RestGitHubGateway`; `python -m lgtmaybe` (the Docker ENTRYPOINT) is the live
   Click CLI. Delivered in this step:
   - **`review` command** — full PR review, posts inline comments + summary.
   - **`comment` command** — handles the `issue_comment` event and routes slash
     commands to the same engine/provider: `/review` + `/improve` post a review,
     `/ask <q>` + `/describe` reply in-thread (`post_issue_comment`, an
     adapter-only method beyond the frozen port).
   - **Guards (in the engine):** generated/binary files skipped via
     `is_reviewable`; **file cap** reviews the top-N and posts a "reviewed top N
     of M" notice.
   - **Context expansion:** `get_pr_context` also fetches the head text of
     reviewable files via the API (read-only, never a checkout) into
     `PRContext.file_contents`; the engine (`compress.expand_hunks`) pads each
     hunk with budget-scaled surrounding lines, capped by
     `ReviewConfig.context_lines` (default 20, `0` disables), redacted like the
     diff. Inline positions stay bound to the **real** diff, so a finding on a
     context-only line maps to nothing and is dropped — never mis-posted.
   - **Error surfacing:** any failure posts a short "review failed" comment and
     the CLI exits non-zero (`ClickException`) — never fails silently.
   - **Per-category fan-out:** the system prompt is composed per `ReviewCategory`
     (security, correctness, deprecation, tests, documentation; `engine/prompt.py`)
     and the engine runs each category as its own **concurrent** `provider.complete`
     call per batch (a `ThreadPoolExecutor` over the sync port), then **merges and
     de-dupes** the findings (`engine._dedupe`, keyed on path/line/side/title) before
     reflection. `ReviewConfig.categories` selects the lenses (default: all five).
   - **Summary line:** names the **model** used (no cost — lgtmaybe does not
     compute or report cost).
   - **Clean review:** zero findings on a fully-reviewed PR posts `👍 LGTM!`
     (comment only — no GitHub approval state) — still naming the model.
4. **Packaging (sequential, last) — DONE:** the two distribution variants over
   one core. Delivered in this step:
   - **`action` entrypoint** — the container command. Routes by
     `GITHUB_EVENT_NAME` (`issue_comment` → slash command, else → full review with
     the PR URL derived from the event), reads inputs from `INPUT_*`. The `review`
     / `comment` / `action` commands share `execute_review` / `execute_comment`.
     `--fallback-model` threads through to the provider.
   - **`action.yml`** — composite action; keyless cloud auth built in (pass
     `aws_role_arn` / `gcp_wif_provider` and it runs the OIDC/WIF exchange), then
     `docker run`s the GHCR image. Inputs: provider, model, fallback_model,
     api_key, aws_role_arn, gcp_wif_provider, config_path (+ region/SA/token/image).
   - **`Dockerfile`** — lean runtime: `uv sync --no-dev --frozen`, venv on PATH,
     `python -m lgtmaybe` (no uv at run time).
   - **`.github/workflows/release.yml`** — on `v*.*.*`: guard (tag == pyproject
     version) → PyPI **trusted publishing** (OIDC, env `pypi`, no token) + GHCR
     push (`{{version}}`, `v{major}`, `latest`) → GitHub release + floating `v1`.
   - **`examples/workflows/`** — one per posting provider (cloud + API-key);
     `id-token: write` for cloud. ollama is local-only (CLI), not a workflow.
   - **Model IDs in docs are kept current** per platform (litellm-native form).

Every task carries its inputs/outputs and an acceptance test so an agent can
self-verify without asking. The acceptance test *is* the red step — start there.

## Conventions

- **Docs:** human-only setup lives in `docs/how-to/` next to the feature it
  serves — cloud trust in the Bedrock/Vertex guides, publishing + marketplace in
  `docs/how-to/releasing.md`. **`DEVELOPMENT.md`** at the repo root is the
  contributor guide: how to run the CLI locally (incl. an unpushed branch via
  `--base`) and run the tests / CI gate.
- Treat diff content as untrusted everywhere it flows.
- Errors surface to the user; never swallow them.

## Security-review coverage

Two distinct concerns, kept separate:

- **The reviewer's own hardening** (so a malicious PR can't subvert *us*):
  prompt-injection defense with delimiter break-out neutralisation, broad secret
  redaction before egress, structured-output schema enforcement (`extra=forbid`
  rejects drifted/injected fields), and fork safety via `pull_request_target`
  with no checkout.
- **What the reviewer looks for** (so it catches issues in *your* PR): the system
  prompt (`engine/prompt.py`) carries an **OWASP-aligned security checklist** —
  injection, XSS, hardcoded secrets, broken authn/authz, path traversal, SSRF,
  insecure deserialization, weak crypto, sensitive-data exposure (secrets/PII —
  passwords, tokens, SSNs, card data — leaking into logs), resource/DoS safety —
  graded `high`/`critical`. Alongside security it also scans for
  **correctness/logic bugs** (edge cases, null/None derefs, off-by-one and
  boundary errors, mismatched/inverted ranges, unhandled error paths;
  "Correctness & logic" section), **missing tests** for changed code paths
  (flagged `low`/`medium`, with a runnable test in the finding's `suggestion`
  field; "Test coverage" section), and **documentation gaps** on public APIs
  (`info`/`low`, restrained to public surfaces; "Documentation" section).

Both are covered by tests in `tests/engine/` (`test_redact.py`, `test_injection.py`,
`test_prompt.py`, `test_parse.py`, `test_engine.py`) and `tests/github/test_diff.py`.
When you touch redaction, injection, the prompt, or the skip filter, extend those
suites — a security change without a test is exactly what CI rejects.

The reviewer also flags **deprecated APIs and end-of-life / vulnerable
dependencies** in the PRs it reviews (prompt section "Deprecation & dependency
health"; covered by `test_prompt.py`). Every scan category is asserted in
`test_prompt.py` (`test_prompt_asks_for_logic_and_edge_case_review`,
`test_prompt_asks_for_test_coverage`, `test_prompt_asks_for_documentation_review`,
`test_prompt_names_pii_and_secrets_in_logs`) — extend those when you change the
prompt's checklist.

## Code-quality & dependency hygiene

Split by whether it can be deterministic, because that decides where it lives:

- **Deterministic → per-PR gate.** Deprecated-API use is a hard error
  (`filterwarnings = error::DeprecationWarning` in `pyproject.toml`;
  `tests/test_code_quality.py` also imports every module under that filter and
  asserts the gate stays wired). Lockfile drift is caught by `uv lock --check`
  in CI. Outdated *syntax* is caught by ruff's `UP` rules. Don't weaken the
  deprecation gate to silence third-party noise — add a narrow per-library
  `ignore` instead.
- **Not deterministic → background/scheduled.** "Is a newer version available?"
  and "does a dep have a known CVE?" depend on what's published upstream at
  check-time, so they can't be a reproducible gate. They run on a schedule:
  `.github/dependabot.yml` (weekly grouped update PRs for the `uv` + GitHub
  Actions ecosystems, plus security-update PRs) and `.github/workflows/audit.yml`
  (`pip-audit` on the locked runtime deps — weekly cron + on dependency-touching
  pushes/PRs, never a blanket per-PR gate so an upstream CVE can't break an
  unrelated build).

[litellm]: https://github.com/BerriAI/litellm
