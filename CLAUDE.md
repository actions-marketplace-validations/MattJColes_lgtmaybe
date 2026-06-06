# CLAUDE.md

Guidance for agents working in **lgtmaybe** — a provider-agnostic PR reviewer.
Read this before writing code. It encodes decisions that are **made, not options**.

## What this is

A PR reviewer that posts inline review comments + a summary. The user picks the
LLM backend with a `--provider` flag, drops a key into GitHub secrets (or wires
OIDC/WIF for cloud providers), and gets a review. One core, two distribution
variants:

- **PyPI CLI** — `pip install lgtmaybe`
- **GitHub Action** — Docker container action pulling a GHCR image

**The wedge:** first-class **Bedrock + Vertex with keyless OIDC/WIF**. Five
providers, one flag, no keys in secrets for cloud. We do not try to out-feature
pr-agent; we win on auth + simplicity. Reuse its proven mechanics, don't clone
its surface.

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
  retries / fallback / cost.
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
  composable stages.
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
   - **Track A** — provider/litellm wrapper: retries, fallback, **cost reporting**.
   - **Track B** — github adapter + diff handling; **skip generated/binary files**
     (lockfiles, minified, vendored).
   - **Track C** — hardening: **prompt-injection defense** (PR text trying to
     steer the reviewer), **secret redaction in diffs before they leave for the
     LLM**, fork-PR exposure (already handled by `pull_request_target` + no checkout).
   - **CLI track** — PyPI packaging, `--dry-run` for local dev.
3. **Integration (sequential, last):** wire stages; surface errors (**a failed
   review posts a comment, never fails silently**); fold cost into the summary.

Every task carries its inputs/outputs and an acceptance test so an agent can
self-verify without asking. The acceptance test *is* the red step — start there.

## Conventions

- **Docs:** `manual-steps.md` holds the human-only setup (cloud roles,
  registries, marketplace).
- Treat diff content as untrusted everywhere it flows.
- Errors surface to the user; never swallow them.

[litellm]: https://github.com/BerriAI/litellm
