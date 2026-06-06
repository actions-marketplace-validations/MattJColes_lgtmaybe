# Getting Started with lgtmaybe

This tutorial walks you through your first PR review using **ollama** — a fully
local model that costs nothing and requires no API keys. By the end you will
have posted a real review comment on a pull request.

## What you need

- Python 3.12 or later
- [ollama](https://ollama.com) running locally
- A GitHub personal access token with `repo` scope (or `pull_requests: write`
  for a fine-grained token)
- A GitHub pull request URL to review

## Step 1 — Install lgtmaybe

```bash
pip install lgtmaybe
```

Verify the install:

```bash
lgtmaybe --version
```

## Step 2 — Start ollama and pull a model

```bash
ollama serve          # starts the local server on http://localhost:11434
ollama pull llama3    # or any model you prefer
```

Leave `ollama serve` running in a separate terminal.

## Step 3 — Export your GitHub token

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

lgtmaybe reads `GITHUB_TOKEN` from the environment; no config file needed for
this first run.

## Step 4 — Run a dry run first

Before posting anything to GitHub, use `--dry-run` to see what the reviewer
would say:

```bash
lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider ollama \
  --model llama3 \
  --api-base http://localhost:11434 \
  --dry-run
```

lgtmaybe fetches the PR diff via the GitHub API, sends it to your local llama3
instance, and prints the findings to stdout. Nothing is written to GitHub.

## Step 5 — Post a real review

Remove `--dry-run` to post the review:

```bash
lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider ollama \
  --model llama3 \
  --api-base http://localhost:11434
```

lgtmaybe posts inline comments for each finding and a summary comment on the PR.
Re-running it is safe — it updates the existing summary comment rather than
creating a duplicate.

## What happened under the hood

lgtmaybe ran five pipeline stages:

1. **fetch** — pulled the PR diff and metadata from the GitHub REST API
2. **compress** — stripped generated files, binaries, and lockfiles
3. **prompt** — built a structured prompt asking for JSON output
4. **parse** — validated the model's JSON against the `ReviewFinding` schema
5. **post** — batched the findings into a single GitHub review request

## Next steps

- To configure severity thresholds, path filters, and token caps, see
  [Configure .lgtmaybe.yml](../how-to/configure-lgtmaybe-yml.md).
- To use a cloud provider with no API keys, see
  [Review with Bedrock OIDC](../how-to/review-with-bedrock-oidc.md) or
  [Review with Vertex WIF](../how-to/review-with-vertex-wif.md).
- To use lgtmaybe in a GitHub Actions workflow, see
  [Use as a GitHub Action](../how-to/use-as-github-action.md).
