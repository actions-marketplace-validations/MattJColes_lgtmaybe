# Data and Privacy

This document states precisely what data lgtmaybe sends to external services,
what is redacted before egress, which providers are fully local, and how
credentials are handled. No data flows occur beyond what is described here.

## What is sent to the LLM provider

lgtmaybe sends one request per review containing:

- The **compressed PR diff** — the unified diff of changed files, after
  generated files, lockfiles, minified assets, and vendored code have been
  stripped.
- **Surrounding context lines** — a budget-scaled number of unchanged lines
  immediately above and below each changed hunk, read from the head revision of
  the **changed files only**. This gives the model the surrounding function and
  definitions so it makes fewer false-positive findings. The amount is capped by
  `context_lines` (default 20, `0` disables it) and shrinks as the diff grows;
  this content is redacted just like the diff. It is fetched read-only via the
  GitHub API — your code is never checked out or executed.
- **PR metadata** — the repository name, PR number, base and head SHAs, and
  the list of changed file paths.
- A **system prompt** — the fixed instructions that tell the model to return
  structured JSON findings.

Nothing else is sent. lgtmaybe does not send:

- PR title, description, or comments
- Repository contents beyond the changed files (only their hunks plus the
  surrounding context lines described above)
- Committer identity or email addresses
- Any data from the repository's git history

## Secret redaction before egress

Before the diff is sent to any external provider, lgtmaybe scans it for
patterns that resemble secrets — API keys, tokens, connection strings, private
keys — and replaces the matched values with `[REDACTED]`. This happens inside
the **compress** stage, before the prompt is built, so redacted values never
reach the LLM or appear in logs.

Redaction is a best-effort defence. Do not commit real secrets to your
repository and rely on this alone.

## Prompt-injection defence

PR diff content is treated as untrusted input throughout the pipeline. The
system prompt instructs the model to ignore any instructions embedded in the
diff or PR body that attempt to alter reviewer behaviour. lgtmaybe does not
execute any code from the PR.

## Ollama: fully local, zero egress

When `--provider ollama` is used, the diff and all other data are sent only to
the ollama server you specify via `--api-base`. If that server is
`http://localhost:11434`, no data leaves your machine. If it is a remote host
(Tailscale peer, self-hosted VM), data is sent only to that host.

Ollama itself is not operated by lgtmaybe. Review ollama's own documentation
for its data handling.

## Cloud providers: data handling

When using Bedrock or Vertex, the compressed and redacted diff is sent over
HTTPS to the respective cloud provider's inference endpoint. Review each
provider's data handling policies:

- **AWS Bedrock** — [AWS Bedrock data protection](https://docs.aws.amazon.com/bedrock/latest/userguide/data-protection.html)
- **Google Vertex AI** — [Vertex AI data governance](https://cloud.google.com/vertex-ai/docs/general/data-governance)
- **OpenAI** — [OpenAI API data privacy](https://openai.com/policies/api-data-privacy)
- **Anthropic** — [Anthropic usage policy](https://www.anthropic.com/legal/aup)
- **OpenRouter** — [OpenRouter privacy policy](https://openrouter.ai/privacy)

## Credentials

lgtmaybe never logs, stores, or transmits API keys. For Bedrock and Vertex,
short-lived ambient credentials are used and are never written to disk by
lgtmaybe. See [Auth Model](./auth-model.md) for details.

## GitHub token

`GITHUB_TOKEN` is used to:

1. Read the PR diff and metadata via the GitHub REST API.
2. Post the review (inline comments + summary) back to the PR.

The token is not sent to any LLM provider. It requires the minimum scopes:
`contents: read` and `pull-requests: write`.

## Fork pull requests

lgtmaybe uses the `pull_request_target` trigger, which runs in the context of
the **base branch**. PR code from the fork is never checked out or executed.
The diff is fetched exclusively through the GitHub API. This prevents a
malicious PR from gaining access to repository secrets.
