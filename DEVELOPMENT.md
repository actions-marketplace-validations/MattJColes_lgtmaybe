# Development

How to run **lgtmaybe** locally and how its tests run — on your machine and in
GitHub Actions. For the contribution bar (TDD, scope) see
[CONTRIBUTING.md](CONTRIBUTING.md); for the decisions that are made-not-options
see [CLAUDE.md](CLAUDE.md).

## Prerequisites

- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** — the project's package manager and
  task runner. Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- **Docker** — only if you want to build/run the container action image locally.
- **[ollama](https://ollama.com/)** — only if you want to run a real review with
  zero cost and no cloud keys.

## Setup

```bash
uv sync --dev
```

This creates `.venv/` and installs the runtime + dev dependencies from the
locked `uv.lock`. Run everything through `uv run …` so it uses that venv (no
manual `activate` needed).

## Project layout

Code is organised by capability, not by technical layer. The package lives under
`src/lgtmaybe/`:

| Module | Responsibility |
|---|---|
| `core/` | Frozen contracts — `ports.py` (the hexagonal interfaces: `ProviderClient`, `GitHubGateway`, `ReviewEngine`), `models.py` (pydantic data: `ReviewConfig`, `ReviewFinding`, `ReviewCategory`, …), `diffparse.py`, `logging.py`. Nothing here imports from the adapters. |
| `providers/` | The litellm adapter (`litellm_provider.py`) plus the `factory.py` (strategy + factory behind `--provider`) and `credentials.py` (chain-of-responsibility auth resolution). |
| `github/` | The REST gateway (`rest_gateway.py`) and diff handling / the generated-file skip filter (`diff.py`). |
| `engine/` | The review pipeline as composable stages — `redact`, `compress` (batch + hunk expansion), `injection` (wrap the diff as untrusted data), `prompt` (per-category prompts), `parse`, `reflect`, and `engine.py` (the orchestrator). |
| `config/` | `.lgtmaybe.yml` loading + the `config` subcommand store. |
| `cli/` | Click command declarations (`commands.py`), runtime wiring (`runtime.py`, `__init__.py`), output rendering (`render.py`), and slash-command dispatch (`slash.py`). |
| `local/` | Builds a `PRContext` from the local `git` repo — the CLI's diff source, the local counterpart to the GitHub gateway. |

`tests/` mirrors this structure, and `tests/fakes/` holds the in-memory fakes
(`FakeProvider`, `FakeGitHub`, `FakeEngine`) that stand in for the real
adapters so tests never touch a live LLM or GitHub.

## How a review runs

One pipeline drives both the CLI and the Action; only the first and last stages
differ (local `git` vs the GitHub API):

```
fetch → redact → split + skip generated → file cap → expand hunks → batch
      → fan out one call PER CATEGORY (concurrent) → parse → merge + dedupe
      → reflect → filter by min_severity → summary → print (CLI) / post (Action)
```

The fan-out is the key non-obvious bit: the system prompt is composed per
`ReviewCategory` (security, correctness, deprecation, tests, documentation), and
the engine issues **one concurrent model call per category per batch** (a
`ThreadPoolExecutor` over the synchronous provider port), then merges and
de-duplicates the findings before the reflection pass. `ReviewConfig.categories`
selects which lenses run (default: all five) — it's a `.lgtmaybe.yml` knob, not a
CLI flag. Narrowing it means fewer model calls.

## Running locally

The fastest loop is the **local `review` command**: it reads your `git` diff and
prints findings — no GitHub token, no pull request, nothing posted anywhere.

```bash
# From inside a git repo, on any local branch — pushed or not:
uv run lgtmaybe review \
  --provider ollama \
  --model qwen3.6:35b \
  --api-base http://localhost:11434
```

`uv run lgtmaybe …` and `uv run python -m lgtmaybe …` are equivalent — the latter
is exactly what the Docker `ENTRYPOINT` runs.

### Reviewing an unpushed local branch

`review` works entirely on **local git refs** — the branch never has to be
pushed or have an open PR. It runs `git diff <base>...HEAD`, where the three-dot
form means "everything this branch added since it forked off `<base>`" (it uses
the merge-base, so changes that landed on mainline meanwhile are ignored).

`--base` chooses what mainline is. It defaults to `origin/HEAD`, falling back to
the literal `main`:

```bash
uv run lgtmaybe review --base main      # diff against your LOCAL main
uv run lgtmaybe review --base develop   # forked off a different branch
uv run lgtmaybe review --base 1a2b3c4   # or an exact commit
uv run lgtmaybe review --working        # uncommitted changes, not yet committed
```

Two cases need an explicit `--base`:

- You have an `origin` remote but haven't fetched — the default `origin/HEAD` can
  be **stale**; pass `--base main` to use your local mainline.
- There's no `origin` **and** no local branch named `main` — the default can't
  resolve and you'll get a clear `git` error; pass your actual base branch.

Useful flags for local iteration (full list: `uv run lgtmaybe review --help`):

| Flag | What it does |
|---|---|
| `--base <ref>` | Diff the branch against `<ref>` (default: remote default branch, else `main`) |
| `--working` | Review uncommitted working-tree changes instead of branch-vs-base |
| `--json` / `--format agent` | Machine-readable output (JSON array, or correction instructions for an AI agent) |
| `--min-severity medium` | Only surface findings at/above a severity |
| `--max-files 10` | Cap how many changed files are reviewed |
| `--timeout 120` | Per-request timeout — raise it for slow local models |
| `--no-reflect` | Keep low-confidence findings (helps weaker local models) |

### Picking a provider locally

`ollama` runs fully local at zero cost and needs no key. The others make real
API calls, so you pay for the token usage:

| Provider | What you need locally |
|---|---|
| `ollama` | Just `--api-base` (e.g. `http://localhost:11434`) — fully local |
| `openai` / `anthropic` / `openrouter` | `--api-key` or the matching `*_API_KEY` env var |
| `bedrock` | Ambient AWS creds (`~/.aws`) — never a static key |
| `vertex` | Ambient GCP creds (local ADC) |
| `azure` | `AZURE_API_KEY` + `--api-base`, or ambient Azure AD creds |

> The local `review` command only **prints** findings. Posting inline comments
> to a real PR happens through the GitHub Action (`comment` / `action`
> entrypoints), which needs a GitHub token and the PR event context — that is
> exercised end-to-end in CI, not from your shell.

### Inspecting config

```bash
uv run lgtmaybe config init     # write a starter .lgtmaybe.yml
uv run lgtmaybe config show     # print the resolved config
uv run lgtmaybe config get <key>
```

### Debugging a local run

litellm prints a generic banner (`Give Feedback / Get Help: …`) on **any**
provider hiccup, and the real error is the line right after it. To see what
actually happened, turn on litellm's debug logging:

```bash
LITELLM_LOG=DEBUG uv run lgtmaybe review --provider ollama --model <model> \
  --api-base http://localhost:11434
```

A few things worth knowing when a local run misbehaves:

- **`👍 LGTM! · 0 findings` on code you know is buggy** usually means the model's
  output didn't parse as the required JSON findings array (small/instruct models
  often wrap it in prose or reasoning), so each category parsed to empty. A run
  can therefore "succeed" with zero findings even though every call struggled —
  check the debug log, and prefer a model that follows the structured-output
  instruction. `parse.py` tolerates fenced JSON but not arbitrary prose.
- **Fan-out makes N concurrent calls** (one per category, five by default), so a
  slow local model multiplies wall-clock pressure. Narrow `categories` in
  `.lgtmaybe.yml` while iterating, and raise `--timeout` for large models on CPU.
- **`--no-reflect`** removes the extra confidence-filtering call — useful when a
  weaker model drops valid findings during reflection, and one fewer call to wait
  on.

## Testing

### Run the full check suite (what CI runs)

These four commands are the gate. Run all of them before opening a PR:

```bash
uv lock --check          # lockfile matches pyproject (no drift)
uv run ruff check .      # lint
uv run ruff format --check .   # format (omit --check to auto-format)
uv run mypy              # types (strict mode)
uv run pytest -q         # tests
```

### Just the tests

```bash
uv run pytest -q                       # whole suite, quiet
uv run pytest tests/engine -q          # one directory
uv run pytest tests/engine/test_redact.py::test_name   # one test
uv run pytest -k injection             # by keyword
```

Tests are behavioural — they call functions and assert results, using the fakes
in `tests/fakes/` (fake provider, fake GitHub gateway) so nothing reaches a real
LLM or the GitHub API. Test layout mirrors `src/`:

- `tests/engine/` — redaction, prompt-injection defense, prompt, parse, caps, fan-out, the pipeline
- `tests/providers/` — factory, credential resolution, retries, the provider matrix
- `tests/github/` — diff handling, review posting, the REST gateway
- `tests/cli/` — CLI flags, slash commands, the `action` entrypoint, e2e wiring
- `tests/core/`, `tests/local/` — diff parsing, local git context
- `tests/docs/` + `tests/snapshots/` — committed schema snapshots and the
  generated-reference freshness check (see below)

### Regenerating generated artifacts

Two things are generated from the pydantic models and checked in CI, so they
fail the suite if they drift after you change `core/models.py`:

- **Schema snapshots** (`tests/snapshots/*.json`) — the frozen JSON schema of each
  contract model.
- **Config reference** (`docs/reference/config.md`) — generated by
  `docs/generate_reference.py`.

Regenerate both after a contract change:

```bash
uv run python docs/generate_reference.py        # refresh docs/reference/config.md
# snapshots: update the committed JSON to the model's current schema, e.g.
uv run python -c "import json; from pathlib import Path; \
from lgtmaybe.core import models as m; \
[Path(f'tests/snapshots/{n}.json').write_text(json.dumps(getattr(m,n).model_json_schema(), indent=2, sort_keys=True)+'\n') \
for n in ('ReviewFinding','ProviderResult','PRContext','ReviewConfig')]"
```

### The deprecation gate

`pytest` is configured (`pyproject.toml`) to treat `DeprecationWarning` and
`PendingDeprecationWarning` as **errors** — using a deprecated API fails the
suite. If the warning comes from a third-party library you don't control, add a
narrow `ignore::DeprecationWarning:thatlib` to `filterwarnings` rather than
weakening the rule. `tests/test_code_quality.py` asserts the gate stays wired.

### Building and testing the container image

The GitHub Action ships as a container. Build and smoke-test it locally:

```bash
docker build -t lgtmaybe:dev .
docker run --rm lgtmaybe:dev --help
```

### Previewing the docs

```bash
uv run --group docs mkdocs serve   # http://127.0.0.1:8000
```

## Testing in GitHub Actions

Two distinct CI workflows cover two different things.

### 1. `ci.yml` — the per-PR gate (always runs)

Runs on every pull request and on pushes to `main`. It installs uv, syncs dev
deps, and runs the **exact five checks** listed above (`uv lock --check`, ruff
lint, ruff format check, mypy, pytest). This is the gate every PR must pass —
green CI + a test is the merge bar. It makes **no** external calls and needs **no**
secrets, so it runs on forks too.

Reproduce it locally by running those five commands; there is nothing
CI-specific about them.

### 2. `action-e2e.yml` — real-provider end-to-end smoke test (opt-in)

This is **not** part of normal CI. It makes **real, billed** provider calls and
needs repo secrets, so it only runs when a PR carries the **`lgtmaybe-e2e`**
label. It builds the action image from the current checkout and has every hosted
provider review the labelled PR through `action.yml` end to end — build image →
keyless/keyed auth → fetch diff → call model → post review.

To run it:

1. Open a small throwaway PR.
2. Add the `lgtmaybe-e2e` label.
3. Each provider runs as its own matrix job (`fail-fast: false`, so one failure
   doesn't mask the rest). A **green** job means that provider authenticated,
   reached the model, and posted without erroring — the job's exit status is the
   real signal (the summaries overwrite each other on the PR, which is cosmetic).

It requires these repo secrets (cloud providers are keyless via OIDC/WIF):

```
OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY   # key providers
AWS_ROLE_ARN                                            # bedrock (OIDC)
GCP_WIF_PROVIDER, GCP_SERVICE_ACCOUNT                   # vertex (WIF)
AZURE_API_BASE, AZURE_CLIENT_ID, AZURE_TENANT_ID        # azure (OIDC)
```

`ollama` is local-only (no hosted runner, no key), so it is covered by the
pytest suite (`tests/cli/test_provider_threading.py`), not by this workflow.

### Other workflows

- **`audit.yml`** — `pip-audit` over the locked runtime deps (weekly cron +
  on dependency-touching changes). A known CVE upstream surfaces here, not as a
  per-PR gate.
- **`docs.yml`** — builds/publishes the docs site.
- **`release.yml`** — on a `v*.*.*` tag: PyPI trusted publishing + GHCR image push.
