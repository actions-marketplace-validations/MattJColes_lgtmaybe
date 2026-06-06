# Use lgtmaybe as a GitHub Action

Use this guide to add lgtmaybe to a repository as a GitHub Actions workflow
that runs automatically on pull requests.

## Security requirement: pull_request_target

All lgtmaybe workflows must use the `pull_request_target` trigger, not
`pull_request`. This is non-negotiable:

- `pull_request_target` runs in the context of the **base branch**, so it can
  access secrets and write to the PR.
- lgtmaybe **never checks out or executes PR code** — it fetches the diff via
  the GitHub API only. The PR author cannot inject code that runs in the
  reviewer's environment.

## Minimal workflow — openai

```yaml
name: pr-review

on:
  pull_request_target:
    types: [opened, synchronize, reopened]

permissions:
  pull-requests: write
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Run lgtmaybe
        uses: ghcr.io/lgtmaybe/lgtmaybe@latest
        with:
          pr-url: ${{ github.event.pull_request.html_url }}
          provider: openai
          model: gpt-4o-mini
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Minimal workflow — anthropic

```yaml
- name: Run lgtmaybe
  uses: ghcr.io/lgtmaybe/lgtmaybe@latest
  with:
    pr-url: ${{ github.event.pull_request.html_url }}
    provider: anthropic
    model: claude-3-5-haiku-20241022
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Minimal workflow — openrouter

```yaml
- name: Run lgtmaybe
  uses: ghcr.io/lgtmaybe/lgtmaybe@latest
  with:
    pr-url: ${{ github.event.pull_request.html_url }}
    provider: openrouter
    model: meta-llama/llama-3.3-70b-instruct
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

## Keyless cloud workflows

For Bedrock (AWS OIDC) and Vertex (GCP WIF) — which require no API keys in
secrets — see the dedicated guides:

- [Review with Bedrock OIDC](./review-with-bedrock-oidc.md)
- [Review with Vertex WIF](./review-with-vertex-wif.md)

## Action inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `pr-url` | Yes | — | Full URL of the pull request |
| `provider` | Yes | — | One of: `openai`, `openrouter`, `anthropic`, `bedrock`, `vertex`, `ollama` |
| `model` | Yes | — | Model identifier for the chosen provider |
| `api-base` | No | — | Custom API base URL (required for `ollama`) |
| `config` | No | `.lgtmaybe.yml` | Path to config file relative to repo root |

## Environment variables read by lgtmaybe

| Variable | Provider | Description |
|---|---|---|
| `GITHUB_TOKEN` | All | GitHub token for reading the PR and posting the review |
| `OPENAI_API_KEY` | openai | OpenAI API key |
| `ANTHROPIC_API_KEY` | anthropic | Anthropic API key |
| `OPENROUTER_API_KEY` | openrouter | OpenRouter API key |
| `VERTEXAI_PROJECT` | vertex | GCP project ID |
| `VERTEXAI_LOCATION` | vertex | GCP region (default: `us-central1`) |

Bedrock and Vertex read ambient cloud credentials — no key variable needed.

## Adding a config file

Place a `.lgtmaybe.yml` at the repo root to control severity thresholds, path
filters, and cost caps. See
[Configure .lgtmaybe.yml](./configure-lgtmaybe-yml.md) for all options.

## Pin the action to a digest

For supply-chain safety, pin the image digest instead of a tag:

```yaml
uses: ghcr.io/lgtmaybe/lgtmaybe@sha256:abc123...
```
