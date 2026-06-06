# lgtmaybe — manual steps

things an agent cant do for you — provider-side cloud trust, registry config, and
marketplace listing. work top to bottom.

---

## A. provider credentials (needed to run a real review)
pick whichever providers you'll actually demo. you do **not** need all five.

### key-based (openai / openrouter / anthropic)
- [ ] generate an api key in that provider's console.
- [ ] add it as a github **repo secret** (e.g. `OPENAI_KEY`, `ANTHROPIC_KEY`, `OPENROUTER_KEY`).

### bedrock (keyless, via OIDC) — the wedge, worth doing
- [ ] in AWS, create an IAM **OIDC identity provider** for `token.actions.githubusercontent.com`.
- [ ] create an IAM **role** with a trust policy scoped to your repo (`repo:<org>/lgtmaybe:*`).
- [ ] attach a least-privilege policy: `bedrock:InvokeModel` + `bedrock:InvokeModelWithResponseStream` on the specific model ARNs only.
- [ ] note the **role ARN** — it becomes the `aws_role_arn` action input. no static key is ever stored.
- [ ] confirm the models you want are enabled in the target region (model access request in the Bedrock console).

### vertex (keyless, via workload identity federation)
- [ ] create a GCP **workload identity pool** + a github provider in it.
- [ ] create a service account with `roles/aiplatform.user` (or narrower).
- [ ] grant the github principal permission to impersonate that SA, scoped to your repo.
- [ ] note the **WIF provider resource name** — it becomes `gcp_wif_provider`.

## B. repo permissions for the action
- [ ] the workflow needs `permissions: id-token: write` (for OIDC) and `pull-requests: write` (to post comments).
- [ ] decide the trigger: `pull_request_target` (so secrets are available) — and confirm the action never checks out PR code, only reads the diff.

## C. publishing

`.github/workflows/release.yml` does the work on a `v*.*.*` tag (guard → pypi +
ghcr → github release + floating `v1`). The human-only pieces:

### one-time setup
- [ ] on pypi, add a **trusted publisher** for this repo: workflow `release.yml`, environment `pypi` (no `PYPI_TOKEN` secret — auth is via OIDC).
- [ ] create the repo **environment** named `pypi` (Settings → Environments).
- [ ] after the first release, set the **GHCR package visibility to public** so consumers can `docker pull` it (Packages → lgtmaybe → Package settings).
- [ ] first release only: from the release page, tick **"Publish this Action to the GitHub Marketplace"**, accept terms, pick categories (`code-review`, `continuous-integration`).

### each release
- [ ] bump `version` in `pyproject.toml`, then push a matching tag (e.g. `v1.0.0`) — the guard job rejects a mismatch.

## D. before you go public
- [ ] dogfood lgtmaybe on its own PRs so the README example is real.
- [ ] re-check the least-privilege IAM/WIF scopes before the repo goes public.
