# lgtmaybe

Provider-agnostic PR reviewer. Five providers, one flag, no static keys for
cloud providers. Posts inline review comments and a summary.

📖 **Full documentation:** <https://mattjcoles.github.io/lgtmaybe/>

## What it reviews

lgtmaybe reviews the **changed lines in a pull request** — nothing else. It
fetches the PR diff from the GitHub API (it never checks out or runs your code)
and looks only at what the PR adds or changes, not the whole repository.
Generated and non-reviewable files — lockfiles, minified bundles, vendored
directories, binaries — are skipped automatically, and secrets are redacted from
the diff before it is sent to the model.

**How the scope is bounded.** Every run is capped so a large PR can't blow up
latency or cost:

- `max_files` (default 50) — reviews the top-N changed files and notes how many were skipped.
- `max_input_tokens` (default 100k) — batches the diff to fit the model's budget.
- `min_severity` (default `info`) plus `include_paths` / `exclude_paths` — focus the review on what you care about.

See [Configure .lgtmaybe.yml](docs/how-to/configure-lgtmaybe-yml.md) for every knob.

**What you get back.** Each finding is structured data — file, line, severity, a
title, an explanation, and an optional suggested fix — so it renders the same
everywhere:

- **On a GitHub PR** — an inline comment on the exact changed line for each finding, plus one summary comment naming the model and approximate cost. Re-running updates the same comments instead of duplicating them, and a clean PR gets a 👍 **LGTM!**.
- **On the CLI** (`--dry-run`) — the summary line followed by the findings as a JSON array on stdout; nothing is posted to GitHub.

A fuller walkthrough with example output is in
[What gets reviewed](docs/explanation/what-gets-reviewed.md).

## Quick start (60 seconds, local, zero cost)

```bash
pip install lgtmaybe
export GITHUB_TOKEN=ghp_your_token_here

lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider ollama \
  --model qwen3.6:27b \
  --api-base http://localhost:11434 \
  --dry-run
```

See [Getting Started](docs/tutorial/getting-started.md) for the full first-run
walkthrough.

## Providers

| Provider | Auth |
|---|---|
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` |
| `bedrock` | Ambient AWS creds — GitHub OIDC, no static key |
| `vertex` | Ambient GCP creds — Workload Identity Federation, no key |
| `ollama` | None — local only, zero cost |

## Documentation

Browse the rendered docs at <https://mattjcoles.github.io/lgtmaybe/>, or read the
Markdown sources below.

**Tutorial** — learn by doing

- [Getting Started](docs/tutorial/getting-started.md) — your first review with ollama

**How-to guides** — task recipes

- [Run locally with ollama](docs/how-to/run-locally-with-ollama.md)
- [Review with Bedrock OIDC](docs/how-to/review-with-bedrock-oidc.md)
- [Review with Vertex WIF](docs/how-to/review-with-vertex-wif.md)
- [Use as a GitHub Action](docs/how-to/use-as-github-action.md)
- [Configure .lgtmaybe.yml](docs/how-to/configure-lgtmaybe-yml.md)
- [Releasing (maintainers)](docs/how-to/releasing.md)

**Reference** — look things up

- [Configuration Reference](docs/reference/config.md) — all config fields and schemas (generated)

**Explanation** — understand the design

- [What gets reviewed](docs/explanation/what-gets-reviewed.md) — scope, caps, and what the output looks like
- [Architecture](docs/explanation/architecture.md) — ports and adapters, the review pipeline
- [Auth Model](docs/explanation/auth-model.md) — why keyless cloud, how credential resolution works
- [Data and Privacy](docs/explanation/data-and-privacy.md) — what is sent where, secret redaction, ollama local mode

## Use as a GitHub Action

```yaml
name: lgtmaybe

on:
  pull_request_target:
  issue_comment:
    types: [created]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    if: ${{ github.event_name == 'pull_request_target' || github.event.issue.pull_request }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: lgtmaybe/lgtmaybe@v1
        with:
          provider: openai
          model: gpt-5.5
          api_key: ${{ secrets.OPENAI_API_KEY }}
```

Copy-paste workflows for every provider live in
[`examples/workflows/`](examples/workflows/). Cloud providers (Bedrock, Vertex)
are **keyless** — pass `aws_role_arn` / `gcp_wif_provider` and the action does
the OIDC/WIF exchange for you (needs `id-token: write`). See
[Use as a GitHub Action](docs/how-to/use-as-github-action.md).

## Distribution

- **CLI** — `pip install lgtmaybe`
- **GitHub Action** — `uses: lgtmaybe/lgtmaybe@v1`

## License

MIT — see `LICENSE`.
