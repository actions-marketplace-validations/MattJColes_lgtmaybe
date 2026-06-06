# lgtmaybe — manual steps

things an agent cant do for you. work top to bottom; each block says *when* in the build it's needed.

---

## A. before any code (day one)
- [ ] create github org/repo `lgtmaybe` (confirm `lgtm-ai` isnt yours — it's a different project).
- [ ] `pip install build twine` and push a `0.0.1` placeholder to pypi to hold the name. real release comes later.
- [ ] enable branch protection on `main`: require CI green, require a PR.

## B. provider credentials (needed to run a real review)
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

## C. repo permissions for the action
- [ ] the workflow needs `permissions: id-token: write` (for OIDC) and `pull-requests: write` (to post comments).
- [ ] decide the trigger: `pull_request_target` (so secrets are available) — and confirm the action never checks out PR code, only reads the diff.

## D. publishing (step 4 of the plan)

### pypi CLI via trusted publishing (no token in secrets)
- [ ] on pypi, add a **trusted publisher** for the repo + the release workflow name + environment.
- [ ] no `PYPI_TOKEN` secret needed — the release workflow authenticates via OIDC.

### GHCR image
- [ ] confirm `packages: write` permission in the release workflow; GHCR uses the built-in `GITHUB_TOKEN`, nothing manual beyond that.

### marketplace listing
- [ ] add an `action.yml` with `name`, `description`, `branding` (icon + colour).
- [ ] tag a release (`v1.0.0`) and a floating `v1`.
- [ ] from the release page, tick **"Publish this Action to the GitHub Marketplace"**, accept terms, pick categories (`code-review`, `continuous-integration`).

## E. before you announce / blog it
- [ ] run lgtmaybe on its own repo (dogfood) so the README screenshot is real.
- [ ] write the data/privacy statement: which provider sees the diff, and that cloud variants send no static keys.
- [ ] sanity-check the least-privilege IAM/WIF scopes one more time before the repo goes public.
