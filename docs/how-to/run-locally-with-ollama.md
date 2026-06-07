# Run Locally with ollama

Use this guide to review your local changes with a local ollama model — zero API
cost, zero egress, no keys required. The CLI reviews your `git` diff and prints
the findings; to post reviews on real pull requests, use the
[GitHub Action](use-as-github-action.md).

## Prerequisites

- lgtmaybe installed (`pip install lgtmaybe`)
- [ollama](https://ollama.com) installed and running
- A local git repository with changes to review

## Pull the model you want

```bash
ollama pull qwen3.6:27b        # good general-purpose model
ollama pull codellama     # code-focused alternative
```

List available models:

```bash
ollama list
```

## Run the review

From inside the repo, on the branch you want reviewed:

```bash
lgtmaybe review \
  --provider ollama \
  --model qwen3.6:27b \
  --api-base http://localhost:11434
```

This diffs your current branch against the default branch and prints the
findings. Add `--working` to review only your uncommitted edits, or `--base <ref>`
to diff against a different base.

## Use a remote ollama instance

If ollama runs on another machine (e.g. a Tailscale peer):

```bash
lgtmaybe review \
  --provider ollama \
  --model qwen3.6:27b \
  --api-base http://100.x.x.x:11434
```

No authentication is added — ollama has no built-in auth. Ensure network access
is restricted at the host or firewall level.

## Inside the GitHub Action's container

The Action runs lgtmaybe in a container, so ollama on the runner host is reached
at `host.docker.internal` rather than `localhost`. Set it in `.lgtmaybe.yml`,
since the Action reads its provider settings from config:

```yaml
provider: ollama
model: qwen3.6:27b
api_base: http://host.docker.internal:11434
```

## Get findings as JSON

The CLI prints a readable listing by default and never posts anywhere. Add
`--json` for a machine-readable array you can pipe into other tooling:

```bash
lgtmaybe review \
  --provider ollama \
  --model qwen3.6:27b \
  --api-base http://localhost:11434 \
  --json
```

## Let an AI agent apply the fixes

`--format agent` prints the findings as correction instructions an AI coding
agent (such as Claude Code) can read and apply, so you can review and fix a
branch locally before opening a PR. See
[Fix findings with an AI agent](fix-findings-with-an-ai-agent.md).

## Troubleshooting

**`Connection refused` on port 11434** — ensure `ollama serve` is running and
the `--api-base` URL is reachable.

**Model not found** — run `ollama pull <model>` before using it.

**Review is empty or truncated** — the diff may exceed the model's context
window. Add a path filter in `.lgtmaybe.yml` to reduce diff size, or set
`max_files` to a lower value.
