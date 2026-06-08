# Architecture

A map of **lgtmaybe** — a provider-agnostic PR reviewer that posts inline review
comments plus a summary. One core, two distribution variants (a PyPI CLI and a
GitHub Action), and a single `--provider` flag that selects the LLM backend.

This document is the high-level orientation: the project layout, the LLM
providers, the components inside the application, and the user-facing features.
For the *why* behind the design (ports & adapters, the pipeline, the patterns),
see [`docs/explanation/architecture.md`](docs/explanation/architecture.md); for
the decisions that are settled, see [`CLAUDE.md`](CLAUDE.md).

## Design in one breath

lgtmaybe is **hexagonal** (ports & adapters). The core defines three ports in
`core/ports.py`; the outside world (litellm, GitHub, git) plugs in as adapters.
The engine depends only on the ports, so providers and gateways swap without it
noticing — and tests inject fakes instead of patching.

```
        CLI flags / Action inputs / .lgtmaybe.yml
                          │
                          ▼
                   ReviewConfig                 (core/models.py)
                          │
   ┌──────────────────────┴───────────────────────┐
   │                    engine                      │   depends only on ports
   │   redact → split → cap → expand → batch        │
   │        → fan-out per category → parse          │
   │        → merge/dedupe → reflect → filter       │
   └───────┬───────────────────────────┬───────────┘
           │ ProviderClient            │ GitHubGateway
           ▼                           ▼
   providers/ (litellm)        github/ (REST)  ·  local/ (git)
           │                           │
           ▼                           ▼
   OpenAI · Anthropic ·         GitHub PR: inline
   OpenRouter · Bedrock ·       comments + summary
   Vertex · Azure · Ollama      (or CLI stdout)
```

## Project layout

```
lgtmaybe/
├── src/lgtmaybe/            # the application (≈3.2k LOC)
│   ├── __main__.py          # `python -m lgtmaybe` / Docker ENTRYPOINT → Click CLI
│   │
│   ├── core/                # the hexagon's centre — no outward dependencies
│   │   ├── ports.py         #   ProviderClient · GitHubGateway · ReviewEngine (frozen)
│   │   ├── models.py        #   pydantic data contracts (ReviewConfig, ReviewFinding, …)
│   │   ├── diffparse.py     #   unified-diff primitives (file split, hunk headers)
│   │   └── logging.py       #   structured JSON logs with secret redaction
│   │
│   ├── engine/              # the review pipeline (adapter-agnostic)
│   │   ├── engine.py        #   LLMReviewEngine — orchestrates every stage
│   │   ├── redact.py        #   scrub secrets from the diff before egress
│   │   ├── injection.py     #   prompt-injection defense + delimiter break-out guard
│   │   ├── compress.py      #   token-aware batching + hunk context expansion
│   │   ├── prompt.py        #   per-category system prompts (OWASP checklist, etc.)
│   │   ├── parse.py         #   lenient JSON → ReviewFinding parsing/repair
│   │   └── reflect.py       #   self-reflection pass that drops low-confidence findings
│   │
│   ├── providers/           # LLM adapter (the ProviderClient side)
│   │   ├── litellm_provider.py  # litellm wrapper: retries (tenacity) + fallback
│   │   ├── factory.py       #   (Provider, model) → configured client; timeouts; model strings
│   │   ├── credentials.py   #   chain-of-responsibility credential resolver
│   │   └── constants.py     #   shared provider defaults (e.g. ollama base URL)
│   │
│   ├── github/              # GitHub adapter (the GitHubGateway side)
│   │   ├── rest_gateway.py  #   fetch PR context · post review · in-thread replies
│   │   └── diff.py          #   diff→position map · is_reviewable() skip filter
│   │
│   ├── local/               # local-mode adapter: build a PRContext from `git`
│   ├── config/              # layered config: defaults < user file < repo file < flags
│   │   ├── loader.py        #   merge layers → ReviewConfig
│   │   └── store.py         #   ~/.config/lgtmaybe user config (never stores keys)
│   │
│   └── cli/                 # Click entrypoints + wiring
│       ├── __init__.py      #   execute_* logic; wires real adapters into the engine
│       ├── commands.py      #   command + option declarations (review/comment/action/config)
│       ├── slash.py         #   /review /improve /ask /describe slash commands
│       ├── runtime.py       #   per-invocation options bag (creds, PR URL)
│       └── render.py        #   local output: human / json / agent formats
│
├── tests/                   # mirrors src/ ; fakes in tests/fakes/, snapshots, fixtures
├── evals/                   # offline scoring harness against fixture diffs
├── docs/                    # MkDocs site: tutorial / how-to / reference / explanation
├── examples/workflows/      # one ready-to-copy GitHub workflow per posting provider
│
├── action.yml              # composite Action: keyless OIDC/WIF auth → docker run GHCR image
├── Dockerfile              # lean runtime image (uv sync --no-dev --frozen)
├── pyproject.toml          # package metadata, deps, ruff/mypy/pytest config (the CI gate)
├── CLAUDE.md               # settled decisions for contributors/agents
└── ARCHITECTURE.md         # this file
```

## LLM providers

One `--provider` flag, one [litellm] `completion()` call shape underneath. Seven
backends, each with its own native auth (resolved by the credential chain in
`providers/credentials.py`):

| Provider     | litellm prefix | Auth model                                                        |
|--------------|----------------|-------------------------------------------------------------------|
| `openai`     | `openai/`      | API key (`--api-key` / `OPENAI_API_KEY`)                          |
| `anthropic`  | `anthropic/`   | API key (`--api-key` / `ANTHROPIC_API_KEY`)                       |
| `openrouter` | `openrouter/`  | API key (`--api-key` / `OPENROUTER_API_KEY`)                      |
| `bedrock`    | `bedrock/`     | **ambient AWS creds** (GitHub OIDC role or local `~/.aws`) — no static key |
| `vertex`     | `vertex_ai/`   | **ambient GCP creds** (Workload Identity Federation or local ADC) — no static key |
| `azure`      | `azure/`       | API key **or** keyless Azure AD/Entra token (OIDC); needs the resource endpoint |
| `ollama`     | `ollama/`      | none — just an `api_base`; fully local, zero cost                 |

**The wedge:** first-class **Bedrock + Vertex with keyless OIDC/WIF**, so cloud
reviews need no static keys in GitHub secrets. The `LiteLLMProvider` adds retries
(exponential backoff + jitter, 4 attempts) and an optional `--fallback-model`.

## Components inside the application

**Core (`core/`)** — the dependency-free centre.
- **Ports** (`ports.py`): `ProviderClient`, `GitHubGateway`, `ReviewEngine` —
  the three abstract seams, frozen so the rest builds against stable signatures.
- **Models** (`models.py`): frozen pydantic contracts with `extra="forbid"` —
  `ReviewConfig`, `ReviewFinding`/`ReviewResult`, `ProviderResult`, `PRContext`,
  the `Severity`/`ReviewCategory`/`Provider` enums, and the reflection envelope.
- **Diff primitives** (`diffparse.py`) and **secret-safe structured logging**
  (`logging.py`).

**Engine (`engine/`)** — the pipeline, as composable stages:
`redact → split per file → drop non-reviewable → file-cap → expand hunks with
budget-scaled context → batch to token budget → fan out one concurrent call per
review category → parse → merge & dedupe → self-reflect → filter by severity →
findings + summary`. It fails loud (`ReviewIncompleteError`) rather than report a
false "clean" when every model call fails.

**Provider adapter (`providers/`)** — strategy + factory over litellm, with the
credential chain of responsibility and a provider-aware timeout (ollama gets a
long one, cloud short).

**GitHub adapter (`github/`)** — `RestGitHubGateway` reads PR context (diff,
files, head-revision file text — all read-only API, never a checkout) and posts a
single batched review, updated idempotently via a hidden per-provider marker
comment. `diff.py` builds the line→position map and the `is_reviewable` skip
filter (lockfiles, minified, vendored, generated, binary).

**Local adapter (`local/`)** — builds a `PRContext` by shelling out to `git`, so
`lgtmaybe review` works on a branch or working tree with no GitHub at all.

**Config (`config/`)** — layered precedence (built-in defaults → user file →
repo `.lgtmaybe.yml` → CLI flags / Action inputs); the user store deliberately
refuses to persist API keys.

**CLI (`cli/`)** — the Click surface: `review` (local), `comment` (issue_comment
slash commands), `action` (the container entrypoint that routes by event), and a
`config` group. Slash commands (`/review`, `/improve`, `/ask`, `/describe`) route
to the same engine/provider.

## Features

**Review intelligence** — per-category fan-out across seven lenses (each its own
concurrent model call, merged & de-duped):
- **Security** — OWASP-aligned checklist: injection, XSS, hardcoded secrets,
  broken authn/authz, path traversal, SSRF, insecure deserialization, weak
  crypto, sensitive-data/PII exposure, resource/DoS.
- **Correctness & logic** — null derefs, off-by-one/boundary, inverted ranges,
  unhandled error paths, bad conditionals, resource leaks.
- **Deprecation & dependency health** — deprecated APIs, EOL runtimes, abandoned
  or vulnerable dependencies (when the diff shows them).
- **Test coverage** — missing tests for changed paths, with a runnable test in
  the suggestion.
- **Documentation** — undocumented or mis-described public surfaces only.
- **Performance** — N+1 queries, accidentally quadratic work, redundant
  computation, hot-path allocations/blocking I/O, unbounded queries (graded by
  impact).
- **Complexity** — high cyclomatic complexity / deep nesting, over-long
  functions, duplicated logic, dead code (restrained, `info`/`medium`).

**Output & posting** — structured findings (path, line, severity, title, body,
optional suggestion). On GitHub: inline comments on the exact changed line + one
summary naming the model, updated idempotently (no duplicates), with a 👍 **LGTM!**
on a clean PR. On the CLI: `human`, `json`, or `agent` (instructions an AI coding
agent can apply) formats.

**Reviewer hardening** (so a malicious PR can't subvert the reviewer):
- **Fork safety** — runs on `pull_request_target` for secrets but never checks
  out or executes PR code; the diff is fetched via API and treated as untrusted.
- **Prompt-injection defense** — the diff is wrapped as untrusted data and forged
  `DIFF_START`/`DIFF_END` delimiters are neutralised so it can't break out.
- **Secret redaction** before egress — AWS/OpenAI/GitHub/Slack/Google/Stripe
  keys, PEM private keys, and quoted password / `Authorization` / connection-
  string credentials are scrubbed before the diff reaches the LLM.
- **Schema enforcement** — `extra="forbid"` rejects drifted/injected fields.

**Scope & cost control** — `max_files`, `max_input_tokens`, `context_lines`,
`min_severity`, `include_paths`/`exclude_paths`, and `categories` bound every
run; generated/binary files are skipped automatically.

**Reliability** — provider retries with fallback, provider-aware timeouts, a
self-reflection pass to cut false positives (toggle with `--no-reflect`), and
loud failure surfacing (a "review failed" comment + non-zero exit) rather than
silent passes.

**Distribution** — `pip install lgtmaybe` (PyPI CLI) and the composite GitHub
Action (keyless OIDC/WIF cloud auth, then runs the GHCR image). Release is
trusted-publishing (OIDC, no tokens) on a `v*.*.*` tag.

[litellm]: https://github.com/BerriAI/litellm
