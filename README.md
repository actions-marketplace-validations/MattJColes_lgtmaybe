<p align="center">
  <img src="docs/assets/logo.svg" alt="lgtmaybe logo — a shrugging face with curly-brace arms" width="128">
</p>

# lgtmaybe

Provider-agnostic PR reviewer. Five providers, one flag, no static keys for
cloud providers. Posts inline review comments and a summary.

📖 **Full documentation:** <https://mattjcoles.github.io/lgtmaybe/>

## What it reviews

lgtmaybe fetches the PR diff from the GitHub API and reviews the lines a pull
request changes. It never checks out or runs your code. To judge each change in
context it also reads a few surrounding lines from the file, but it only ever
comments on what the PR actually changed, not the whole repository.

Reviews surface the kind of thing a careful reviewer would flag: correctness
bugs, security weaknesses, and readability problems, each graded from `info` up
to `critical`. Generated and non-reviewable files (lockfiles, minified bundles,
vendored directories, binaries) are skipped automatically, and secrets are
redacted from the diff before it is sent to the model.

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
- **On the CLI** — `lgtmaybe review` reads your local `git` diff and prints the findings (a readable listing, or a JSON array with `--json`); nothing is posted to GitHub.

A fuller walkthrough with example output is in
[What gets reviewed](docs/explanation/what-gets-reviewed.md).

## Quick start (60 seconds, local, zero cost)

From inside a git repo, on a branch with changes, review your diff against the
default branch and print the findings:

```bash
pip install lgtmaybe

lgtmaybe review \
  --provider ollama \
  --model qwen3.6:27b \
  --api-base http://localhost:11434
```

No GitHub token and no pull request needed — `lgtmaybe review` reads your local
`git` diff and prints the findings. To post reviews on real pull requests, wire
up the [GitHub Action](#use-as-a-github-action). See
[Getting Started](docs/tutorial/getting-started.md) for the full walkthrough.

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

## Contributing

Test-first, green CI, scope is the gate. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see `LICENSE`.
