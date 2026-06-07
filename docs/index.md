<div class="hero" markdown>

![lgtmaybe logo — a shrugging face with curly-brace arms](assets/logo.svg){ width="128" }

# lgtmaybe

</div>

Provider-agnostic PR reviewer. Five providers, one flag, and no static keys for
cloud providers. It posts inline comments and a summary straight onto the pull
request.

lgtmaybe reviews the lines a change touches, and it runs in two places: as a
GitHub Action on a pull request, or locally from the command line against your
`git` diff before you push. As an Action it fetches the diff from the GitHub API
and never checks out or runs your code; locally it reads your working branch.
Either way it pads each change with a few surrounding lines, so a finding lands
with the function around it in view, but it only ever comments on the lines that
actually changed.

Reviews surface the things you'd want a careful reviewer to catch:

- **Correctness bugs and readability problems** — the substance of a change, not just style nits.
- **Security vulnerabilities** — an OWASP-aligned sweep: injection, XSS, hardcoded secrets, broken authn/authz, path traversal, SSRF, insecure deserialization, weak crypto, and resource/DoS safety.
- **Deprecated and end-of-life code** — deprecated APIs and end-of-life or vulnerable dependencies, flagged when the diff shows them (with the modern replacement suggested where known).
- **Severity grading** — every finding is rated from `info` up to `critical`, so you can set the floor that matters to you.
- **Inline, on the exact line** — each finding is a comment where the problem is, with one summary at the top (on the CLI, the same findings print to your terminal).

Generated files and binaries are skipped, secrets are redacted and the diff is
treated as untrusted input (hardened against prompt injection) before anything
leaves for the model, and a clean PR just gets a 👍 **LGTM!**.

## Start here

<div class="grid cards" markdown>

- **Tutorial** — [Getting started](tutorial/getting-started.md): your first review with ollama, locally and free.
- **How-to** — task recipes: [run locally](how-to/run-locally-with-ollama.md), [Bedrock OIDC](how-to/review-with-bedrock-oidc.md), [Vertex WIF](how-to/review-with-vertex-wif.md), [GitHub Action](how-to/use-as-github-action.md).
- **Reference** — [Configuration](reference/config.md): every config field and schema.
- **Explanation** — [What gets reviewed](explanation/what-gets-reviewed.md), [Architecture](explanation/architecture.md), [Auth model](explanation/auth-model.md), [Data & privacy](explanation/data-and-privacy.md).

</div>

## Providers

| Provider | Auth |
|---|---|
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` |
| `bedrock` | Ambient AWS creds — GitHub OIDC, no static key |
| `vertex` | Ambient GCP creds — Workload Identity Federation, no key |
| `ollama` | None — local only, zero cost |
