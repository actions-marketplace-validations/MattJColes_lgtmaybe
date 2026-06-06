# Configure .lgtmaybe.yml

Place a `.lgtmaybe.yml` file at the root of your repository to control how
lgtmaybe reviews pull requests. CLI flags override file values; the file
provides defaults for all runs.

## Full example

```yaml
provider: openai
model: gpt-4o-mini
min_severity: low
include_paths:
  - "src/**"
  - "lib/**"
exclude_paths:
  - "**/__pycache__/**"
  - "**/*.min.js"
max_files: 30
max_input_tokens: 80000
max_cost_usd: 0.50
```

## Field reference

See [Reference: Config](../reference/config.md) for the full schema with
types and defaults.

### provider

Which LLM backend to use. One of `openai`, `openrouter`, `anthropic`,
`bedrock`, `vertex`, `ollama`.

```yaml
provider: anthropic
```

### model

The model identifier for the chosen provider. Format varies by provider:

| Provider | Example model IDs |
|---|---|
| openai | `gpt-4o`, `gpt-4o-mini` |
| anthropic | `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022` |
| openrouter | `meta-llama/llama-3.3-70b-instruct` |
| bedrock | `us.anthropic.claude-3-5-haiku-20241022-v1:0` |
| vertex | `gemini-2.0-flash-001` |
| ollama | `llama3`, `codellama` |

### min_severity

The minimum severity level to report. Findings below this threshold are
suppressed. Ordered low to high: `info`, `low`, `medium`, `high`, `critical`.

```yaml
min_severity: medium   # suppresses info and low findings
```

Default: `info` (all findings reported).

### include_paths / exclude_paths

Glob patterns to restrict which files in the diff are reviewed.
`include_paths` acts as an allowlist; `exclude_paths` acts as a denylist applied
after the allowlist. Both default to empty (all files included).

```yaml
include_paths:
  - "src/**"
exclude_paths:
  - "src/generated/**"
  - "**/*.lock"
```

### max_files

Maximum number of changed files to include in the review. Files beyond this
limit are skipped. Reduces token usage on large PRs.

```yaml
max_files: 30
```

Default: `50`.

### max_input_tokens

Hard cap on the number of tokens sent to the model. If the compressed diff
exceeds this limit, lgtmaybe truncates it and notes the truncation in the
summary.

```yaml
max_input_tokens: 80000
```

Default: `100000`.

### max_cost_usd

Maximum cost in US dollars for one review. If the projected cost exceeds this
value, lgtmaybe aborts before sending the request.

```yaml
max_cost_usd: 0.25
```

Default: `1.0`.

## CLI flag overrides

Every config field can be overridden at the command line:

```bash
lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider anthropic \
  --model claude-3-5-haiku-20241022 \
  --min-severity high
```

Flags take precedence over `.lgtmaybe.yml`.
