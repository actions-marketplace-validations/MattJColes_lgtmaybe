# Run Locally with ollama

Use this guide to review pull requests using a local ollama model — zero API
cost, zero egress, no keys required.

## Prerequisites

- lgtmaybe installed (`pip install lgtmaybe`)
- [ollama](https://ollama.com) installed and running
- `GITHUB_TOKEN` set in the environment

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

```bash
lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider ollama \
  --model qwen3.6:27b \
  --api-base http://localhost:11434
```

## Use a remote ollama instance

If ollama runs on another machine (e.g. a Tailscale peer):

```bash
lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider ollama \
  --model qwen3.6:27b \
  --api-base http://100.x.x.x:11434
```

No authentication is added — ollama has no built-in auth. Ensure network access
is restricted at the host or firewall level.

## Use inside Docker (GitHub Action)

When running inside a Docker container, substitute `host.docker.internal` for
`localhost`:

```bash
--api-base http://host.docker.internal:11434
```

## Dry run to inspect findings without posting

```bash
lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider ollama \
  --model qwen3.6:27b \
  --api-base http://localhost:11434 \
  --dry-run
```

Findings are printed to stdout; nothing is written to GitHub.

## Troubleshooting

**`Connection refused` on port 11434** — ensure `ollama serve` is running and
the `--api-base` URL is reachable.

**Model not found** — run `ollama pull <model>` before using it.

**Review is empty or truncated** — the diff may exceed the model's context
window. Add a path filter in `.lgtmaybe.yml` to reduce diff size, or set
`max_files` to a lower value.
