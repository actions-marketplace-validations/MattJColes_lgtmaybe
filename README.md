# lgtmaybe

Provider-agnostic PR reviewer. Five providers, one flag, no keys in secrets for
cloud. Posts inline review comments + a summary.

> Status: under construction. See `CLAUDE.md` for the build plan and
> `manual-steps.md` for the human-only setup.

## Providers

`openai` · `openrouter` · `anthropic` · `bedrock` (keyless OIDC) ·
`vertex` (keyless WIF) · `ollama` (local, zero cost)

## Distribution

- **CLI** — `pip install lgtmaybe`
- **GitHub Action** — Docker container action from GHCR

## License

MIT — see `LICENSE`.
