# Review with Azure OpenAI

Use this guide to run lgtmaybe against **Azure OpenAI** — your models hosted on
your own Azure resource, billed through your Azure subscription.

## How it works

Azure OpenAI serves each model from a per-resource endpoint and authenticates
with a resource key. lgtmaybe needs two things:

- **`AZURE_API_KEY`** — a key for your Azure OpenAI resource.
- **`AZURE_API_BASE`** — the resource endpoint, e.g.
  `https://<resource>.openai.azure.com`.

litellm reads `AZURE_API_VERSION` directly from the environment and falls back
to a sensible default, so you only need to set it when you must pin a specific
API version. Unlike Bedrock and Vertex, Azure is **key-based** — the key lives
in a GitHub Actions secret, never in `.lgtmaybe.yml`.

## One-time Azure setup

Do this once in the Azure portal (or with the `az` CLI):

1. Create an **Azure OpenAI** resource and note its **endpoint**
   (`https://<resource>.openai.azure.com`) — this is `AZURE_API_BASE`.
2. **Deploy** the model you want (e.g. `gpt-4o`) and note the **deployment
   name** — this is what you pass as `model`, *not* the upstream OpenAI name.
3. Copy a **key** from the resource's *Keys and Endpoint* blade — this is
   `AZURE_API_KEY`.
4. Store both as repo secrets (`AZURE_API_KEY`, `AZURE_API_BASE`).

## Workflow example

```yaml
name: lgtmaybe

on:
  pull_request_target:
  issue_comment:
    types: [created]

permissions:
  contents: read
  pull-requests: write     # required to post review comments

jobs:
  review:
    if: ${{ github.event_name == 'pull_request_target' || github.event.issue.pull_request }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: lgtmaybe/lgtmaybe@v1
        with:
          provider: azure
          model: my-gpt-4o-deployment   # your deployment name
          api_key: ${{ secrets.AZURE_API_KEY }}
          api_base: ${{ secrets.AZURE_API_BASE }}
```

## Choosing the model name

For Azure, `model` is the **deployment name** you chose in the portal, not the
underlying OpenAI model id. A deployment of `gpt-4o` named `my-gpt-4o-deployment`
is referenced as `model: my-gpt-4o-deployment`. litellm routes it as
`azure/<deployment-name>`.

## Running locally

Set the two environment variables and review your current branch's changes:

```bash
export AZURE_API_KEY="…"
export AZURE_API_BASE="https://<resource>.openai.azure.com"

lgtmaybe review \
  --provider azure \
  --model my-gpt-4o-deployment
```

You can also pass them inline with `--api-key` and `--api-base` instead of the
environment variables.

## Troubleshooting

**`azure requires an API key`** / **`azure requires the resource endpoint`** —
one of `AZURE_API_KEY` / `AZURE_API_BASE` (or `--api-key` / `--api-base`) is
missing. The error names the one to set.

**`DeploymentNotFound` / 404** — `model` must be the **deployment name**, not the
upstream OpenAI model id, and the deployment must exist on the resource that
`AZURE_API_BASE` points at.

**`Unsupported API version`** — pin one explicitly by setting `AZURE_API_VERSION`
(e.g. `2024-08-01-preview`) in the environment.
