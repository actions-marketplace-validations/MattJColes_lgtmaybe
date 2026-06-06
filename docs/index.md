# lgtmaybe

Provider-agnostic PR reviewer. Five providers, one flag, no static keys for
cloud providers. It posts inline review comments and a summary on a pull request.

lgtmaybe reviews the **changed lines in a pull request** — it fetches the PR diff
from the GitHub API (it never checks out or runs your code), skips generated and
binary files, redacts secrets, and returns structured findings: a comment on the
exact changed line plus one summary. A clean PR gets a 👍 **LGTM!**.

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
