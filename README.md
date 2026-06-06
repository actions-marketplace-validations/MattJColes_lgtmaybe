# lgtmaybe

Provider-agnostic PR reviewer. Five providers, one flag, no static keys for
cloud providers. Posts inline review comments and a summary.

## Quick start (60 seconds, local, zero cost)

```bash
pip install lgtmaybe
export GITHUB_TOKEN=ghp_your_token_here

lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider ollama \
  --model llama3 \
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

**Tutorial** — learn by doing

- [Getting Started](docs/tutorial/getting-started.md) — your first review with ollama

**How-to guides** — task recipes

- [Run locally with ollama](docs/how-to/run-locally-with-ollama.md)
- [Review with Bedrock OIDC](docs/how-to/review-with-bedrock-oidc.md)
- [Review with Vertex WIF](docs/how-to/review-with-vertex-wif.md)
- [Use as a GitHub Action](docs/how-to/use-as-github-action.md)
- [Configure .lgtmaybe.yml](docs/how-to/configure-lgtmaybe-yml.md)

**Reference** — look things up

- [Configuration Reference](docs/reference/config.md) — all config fields and schemas (generated)

**Explanation** — understand the design

- [Architecture](docs/explanation/architecture.md) — ports and adapters, the review pipeline
- [Auth Model](docs/explanation/auth-model.md) — why keyless cloud, how credential resolution works
- [Data and Privacy](docs/explanation/data-and-privacy.md) — what is sent where, secret redaction, ollama local mode

## Distribution

- **CLI** — `pip install lgtmaybe`
- **GitHub Action** — `uses: ghcr.io/lgtmaybe/lgtmaybe@latest`

## License

MIT — see `LICENSE`.
