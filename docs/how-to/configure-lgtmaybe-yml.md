# Configure .lgtmaybe.yml

Place a `.lgtmaybe.yml` file at the root of your repository to control how
lgtmaybe reviews pull requests. CLI flags override file values; the file
provides defaults for all runs.

## Full example

```yaml
provider: openai
model: gpt-5.5
min_severity: low
include_paths:
  - "src/**"
  - "lib/**"
exclude_paths:
  - "**/__pycache__/**"
  - "**/*.min.js"
max_files: 30
max_input_tokens: 80000
categories:
  - security
  - correctness
  - tests
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
| openai | `gpt-5.5` |
| anthropic | `claude-sonnet-4-6`, `claude-haiku-4-5` |
| openrouter | `anthropic/claude-sonnet-4-6` |
| bedrock | `anthropic.claude-sonnet-4-6`, `anthropic.claude-haiku-4-5` |
| vertex | `gemini-3-pro`, `gemini-3.5-flash` |
| ollama | `qwen3.6:27b`, `gemma4:e4b` |

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

### categories

Which review lenses to run. The reviewer asks for each category in its own
concurrent model call and merges the findings, so a focused prompt concentrates
on one concern at a time. One or more of `security`, `correctness`,
`deprecation`, `tests`, `documentation`, `performance`, `complexity`. Narrowing
the list trades thoroughness for fewer model calls (and lower token usage).

```yaml
categories:
  - security
  - correctness
```

Default: all seven categories.

### context_lines

Ceiling on the number of unchanged lines added above and below each changed hunk,
read from the head revision of the file so the model can review a change in the
context of its surrounding code. The actual number used is the smaller of this
ceiling and what the token budget allows, so it shrinks automatically on large
PRs. Set it to `0` to disable context expansion and review the bare diff (no
extra file content is fetched).

```yaml
context_lines: 10   # at most 10 lines either side of each hunk; 0 disables
```

Default: `20`.

### timeout

Per-request timeout in seconds for each model call. Left unset, lgtmaybe picks a
**provider-aware default**: **300 s for ollama** (local models are slow) and 60 s
for cloud providers. Set it explicitly to raise it for a large local model.

```yaml
timeout: 900   # 15 minutes per call, e.g. for a big model on CPU
```

Default: auto (ollama 300 s, cloud 60 s). See
[Run locally with ollama](run-locally-with-ollama.md#slow-models-and-timeouts).

### structured_output

Constrain the model to emit the findings JSON schema using the provider's native
JSON mode (litellm `response_format`). This keeps models — especially local ones —
from returning prose or reasoning instead of findings. Leave it on unless a
particular model/provider doesn't support structured output, in which case the
lenient parser is the fallback.

```yaml
structured_output: false   # only if your model rejects JSON-schema mode
```

Default: `true`.

## CLI flag overrides

Every config field can be overridden at the command line:

```bash
lgtmaybe review \
  --provider anthropic \
  --model claude-haiku-4-5 \
  --min-severity high
```

Flags take precedence over `.lgtmaybe.yml`.
