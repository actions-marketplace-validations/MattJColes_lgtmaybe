# Auth Model

lgtmaybe supports five providers with three distinct auth approaches. The design
principle is **no static cloud credentials**: cloud providers use ambient,
short-lived tokens; only key-based SaaS providers (openai, anthropic,
openrouter) require an API key, and even those stay in secrets rather than being
committed to config.

## Why keyless for cloud

Static credentials — an AWS access key pair or a GCP service-account JSON file
— have a fixed lifetime and broad scope. If they leak from a CI log, a secrets
manager misconfiguration, or a compromised runner, an attacker retains access
until the key is manually rotated.

OIDC (AWS) and Workload Identity Federation (GCP) issue tokens that:

- Expire in minutes, not years
- Are scoped to a single workflow run
- Cannot be extracted from CI logs (they are never set as static environment
  variables)
- Are tied to the specific repository and branch via the OIDC claim set

For these reasons, lgtmaybe treats Bedrock and Vertex as **ambient-credential
only** providers. There is no `--api-key` flag for them.

## Chain of responsibility

When lgtmaybe starts, it resolves credentials for the selected provider using a
chain:

1. **Provider identity** — which provider was chosen?
2. **Ambient cloud creds** — for Bedrock and Vertex, the chain stops here.
   If no ambient creds exist, lgtmaybe fails immediately with a clear
   "how to auth this provider" message. It does not fall back to a key.
3. **API key** — for openai, anthropic, and openrouter, lgtmaybe reads the
   key from the environment (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
   `OPENROUTER_API_KEY`). The `--api-key` flag can override this at the CLI.
4. **None** — ollama requires no credentials. Only `--api-base` is needed
   to reach the local or remote server.

## Provider auth summary

| Provider | Credential type | How to supply |
|---|---|---|
| openai | API key | `OPENAI_API_KEY` env var or `--api-key` |
| anthropic | API key | `ANTHROPIC_API_KEY` env var or `--api-key` |
| openrouter | API key | `OPENROUTER_API_KEY` env var or `--api-key` |
| bedrock | Ambient AWS creds | GitHub OIDC role or local `~/.aws`; IAM requires only `bedrock:InvokeModel*` |
| vertex | Ambient GCP creds | GitHub WIF or local ADC (`gcloud auth application-default login`) |
| ollama | None | `--api-base` pointing to the local or remote server |

## Least-privilege IAM

For Bedrock, the minimum IAM policy is `bedrock:InvokeModel` and (if streaming)
`bedrock:InvokeModelWithResponseStream` on the specific model ARN. No other AWS
permissions are needed or requested.

For Vertex, `roles/aiplatform.user` on the project is sufficient.
`roles/editor` or `roles/owner` must not be used.

## API keys in secrets, not config

For openai, anthropic, and openrouter, the key must live in a GitHub Actions
secret (or an equivalent secret store). It must never be committed to
`.lgtmaybe.yml` or any other file in the repository. lgtmaybe does not log or
display key values.
