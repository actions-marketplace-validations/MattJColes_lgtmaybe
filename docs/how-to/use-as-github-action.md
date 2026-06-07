# Use lgtmaybe as a GitHub Action

Use this guide to add lgtmaybe to a repository as a GitHub Actions workflow
that reviews pull requests automatically.

Ready-to-copy workflows for every cloud and API-key provider live in
[`examples/workflows/`](https://github.com/MattJColes/lgtmaybe/tree/main/examples/workflows).
ollama runs the model on your own machine, so it is local-only — use the
[CLI](run-locally-with-ollama.md) rather than a posting workflow.

## Security requirement: pull_request_target

All lgtmaybe workflows use the `pull_request_target` trigger, not
`pull_request`. This is non-negotiable:

- `pull_request_target` runs in the context of the **base branch**, so it can
  access secrets and write to the PR.
- lgtmaybe **never checks out or executes PR code** — it fetches the diff via
  the GitHub API only. The PR author cannot inject code that runs in the
  reviewer's environment.

The action derives the PR from the triggering event, so there is no `pr-url`
input to set. On an `issue_comment` event it routes the slash command
(`/review`, `/ask`, `/describe`, `/improve`) to the same engine.

> **⚠️ Cost disclaimer.** Each run calls your chosen LLM provider and **you pay
> for those tokens**. On a public repository the default triggers let *anyone* —
> including strangers opening fork PRs or posting `/ask` / `/review` comments —
> spend your provider budget, and every push to a PR triggers another run. The
> built-in `max_files` and `max_input_tokens` settings bound a single run, but
> not the number of runs. You are responsible for your provider
> spend: gate the workflow to trusted authors, use a cheap model, and set
> spending limits in your provider console.

## Minimal workflow — openai

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
      - uses: actions/checkout@v4 # base repo only — for .lgtmaybe.yml config
      - uses: lgtmaybe/lgtmaybe@v1
        with:
          provider: openai
          model: gpt-5.5
          api_key: ${{ secrets.OPENAI_API_KEY }}
```

## Other key-based providers

Swap the `provider`, `model`, and `api_key` inputs:

```yaml
# anthropic
- uses: lgtmaybe/lgtmaybe@v1
  with:
    provider: anthropic
    model: claude-sonnet-4-6
    api_key: ${{ secrets.ANTHROPIC_API_KEY }}

# openrouter
- uses: lgtmaybe/lgtmaybe@v1
  with:
    provider: openrouter
    model: anthropic/claude-sonnet-4-6
    api_key: ${{ secrets.OPENROUTER_API_KEY }}
```

For these, the one-time setup is just: generate an API key in the provider's
console and add it as a repo secret (Settings → Secrets and variables → Actions),
then reference it as `api_key` above.

## Keyless cloud workflows

Bedrock (AWS OIDC) and Vertex (GCP WIF) need **no API keys in secrets** — the
action performs the keyless token exchange for you when you pass `aws_role_arn`
or `gcp_wif_provider`. Both require `id-token: write` permission. See:

- [Review with Bedrock OIDC](./review-with-bedrock-oidc.md)
- [Review with Vertex WIF](./review-with-vertex-wif.md)

## Action inputs

| Input | Default | Description |
|---|---|---|
| `provider` | — | One of: `openai`, `openrouter`, `anthropic`, `bedrock`, `vertex`, `ollama` |
| `model` | — | Model identifier for the chosen provider |
| `fallback_model` | — | Model to retry with if the primary model fails |
| `api_key` | — | API key for key-based providers (leave empty for bedrock/vertex) |
| `aws_role_arn` | — | IAM role ARN to assume via OIDC for bedrock (keyless) |
| `aws_region` | `us-east-1` | AWS region for bedrock |
| `gcp_wif_provider` | — | Workload Identity Federation provider resource name for vertex |
| `gcp_service_account` | — | GCP service account email to impersonate via WIF |
| `config_path` | `.lgtmaybe.yml` | Path to the config file, relative to repo root |
| `github_token` | `${{ github.token }}` | Token for reading the PR and posting the review |
| `image` | `ghcr.io/lgtmaybe/lgtmaybe:v1` | Override the container image (advanced) |

The action sets the `GITHUB_TOKEN` and provider credentials for the container
itself — you do not pass them as `env`.

## Adding a config file

Place a `.lgtmaybe.yml` at the repo root to control severity thresholds, path
filters, and cost caps. See
[Configure .lgtmaybe.yml](./configure-lgtmaybe-yml.md) for all options.

## Pin to a specific version

`@v1` is a floating tag that tracks the latest `v1.x.x` release. To pin exactly,
use a full version tag:

```yaml
uses: lgtmaybe/lgtmaybe@v1.0.0
```
