<div class="hero" markdown>

![lgtmaybe logo — a shrugging face with curly-brace arms](assets/logo.svg){ width="128" }

# lgtmaybe

</div>

Provider-agnostic PR reviewer. Five providers, one flag, and no static keys for
cloud providers. It posts inline comments and a summary straight onto the pull
request.

lgtmaybe fetches the diff from the GitHub API and reviews the lines a pull
request changes. It never checks out or runs your code. To judge each change in
context it also reads a few surrounding lines from the file, so a finding lands
with the function around it in view, but it only ever comments on what the PR
actually changed.

Reviews surface the things you'd want a careful reviewer to catch: correctness
bugs, security weaknesses, and readability problems. Every finding is graded from
`info` up to `critical` and posted as an inline comment on the exact line, with
one summary at the top. Generated files and binaries are skipped, secrets are
redacted before anything leaves for the model, and a clean PR just gets a
👍 **LGTM!**.

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
