# Releasing lgtmaybe (maintainers)

Publishing is automated by `.github/workflows/release.yml`: on a `v*.*.*` tag it
runs guard (tag must equal the `pyproject.toml` version) → PyPI + GHCR →
GitHub release + moves the floating `v1` tag. PyPI uses **trusted publishing**
(OIDC) and GHCR uses the built-in `GITHUB_TOKEN`, so no publish tokens live in
secrets.

The only human-only pieces:

## One-time setup

- On PyPI, add a **trusted publisher** for this repo: workflow `release.yml`,
  environment `pypi` (no `PYPI_TOKEN` secret — auth is via OIDC).
- Create the repo **environment** named `pypi` (Settings → Environments).
- After the first release, set the **GHCR package visibility to public** so
  consumers can `docker pull` the image (Packages → lgtmaybe → Package settings).
- First release only: from the GitHub release page, tick **"Publish this Action
  to the GitHub Marketplace"**, accept the terms, and pick the categories
  `code-review` and `continuous-integration`.

## Each release

1. Bump `version` in `pyproject.toml`.
2. Push a matching tag, e.g. `git tag v1.0.0 && git push origin v1.0.0` — the
   guard job rejects a tag that doesn't match the version.

## Before going public

- Dogfood lgtmaybe on its own PRs so the README example is real.
- Re-check the least-privilege IAM/WIF scopes (see the
  [Bedrock](./review-with-bedrock-oidc.md) and [Vertex](./review-with-vertex-wif.md)
  guides) before the repo goes public.
