# What gets reviewed

This page explains what lgtmaybe looks at, how it bounds the work, and what the
output looks like — on a GitHub PR and on the command line.

## What it looks at

lgtmaybe reviews the **diff of a pull request** — the lines the PR adds or
changes — not the whole repository. It fetches that diff from the GitHub REST
API and **never checks out or executes your code**, so a malicious PR can't run
anything in the reviewer's environment. The diff is treated as untrusted input
throughout, including against prompt-injection attempts hidden in PR text.

To review changes in context rather than in isolation, lgtmaybe also pads each
changed hunk with a few **surrounding lines** read from the head revision of the
changed file. The model uses these to understand the change — the enclosing
function, nearby definitions — but only ever comments on the changed lines. How
many lines are added is budget-scaled and capped by `context_lines` (default 20,
`0` disables it). This content is fetched read-only via the API and redacted
like the diff.

Before the diff reaches the model it is cleaned:

- **Non-reviewable files are skipped** — lockfiles, minified/bundled assets,
  vendored directories, and binaries. Reviewing them is noise and wastes tokens.
- **Secrets are redacted** — anything that looks like a key or token is stripped
  from the diff before it leaves your environment for the provider.

## Correctness & logic

The substance of a change, not just style. The model is prompted to actively
hunt the bugs a change introduces and grade them by impact:

- **Null / None dereferences** — a value that can be empty used without a guard.
- **Off-by-one & boundary errors** — `<` vs `<=`, fencepost mistakes, empty- and
  single-element edge cases.
- **Mismatched or inverted ranges** — `start`/`end` swapped, a lower bound above
  its upper bound.
- **Unhandled error / exception paths** — failures silently swallowed or state
  left half-updated.
- **Incorrect conditionals** — inverted booleans, `and`/`or` mix-ups, missing
  branches.
- **Resource leaks & ordering** — handles or locks not released, use-after-close,
  bad concurrent sequencing.

## Security review

Security findings are first-class. The model is prompted with an OWASP-aligned
checklist and told to grade what it finds `high` or `critical` and name the
vulnerability class in the title. It actively looks for:

- **Injection** — SQL/NoSQL, OS command, and template/LDAP injection.
- **Cross-site scripting (XSS)** — unescaped user input rendered into HTML/JS.
- **Hardcoded secrets** — keys, tokens, passwords, or private keys in the diff.
- **Broken authn / authz** — missing permission checks, IDOR, auth bypass.
- **Path traversal / unsafe file access** — user input in file paths, `../`.
- **SSRF** — server-side fetches of user-controlled URLs without allow-listing.
- **Insecure deserialization & unsafe eval** — `pickle`/`yaml.load`/`eval` on
  untrusted data.
- **Weak cryptography** — MD5/SHA1 for passwords, ECB mode, disabled TLS
  verification, predictable randomness for security tokens.
- **Sensitive-data exposure** — secrets or PII in logs, error responses, or
  analytics: passwords, API keys, tokens/session IDs, SSNs, or payment-card data.
- **Resource / DoS safety** — missing timeouts, unbounded loops or allocations.

This shapes *what* the reviewer flags. It is separate from how lgtmaybe protects
**itself** from a malicious PR — see
[Data and Privacy](data-and-privacy.md) for secret redaction and prompt-injection
defence.

## Deprecation & dependency health

Beyond bugs and vulnerabilities, the reviewer also flags **factually outdated**
code when the diff shows it — these are objective, not stylistic:

- deprecated language/framework APIs (with the modern replacement suggested when
  known),
- targeting an end-of-life runtime or language version,
- adding or pinning an end-of-life / abandoned dependency, and
- pinning a dependency to a version with a known security advisory.

The reviewer only raises these when the diff itself shows the change; it does not
speculate about code it cannot see.

## Test coverage & documentation

Two lighter-weight checks round out a review:

- **Missing tests** — when the diff adds a new function, branch, or error case
  with no accompanying test, the reviewer raises a `low`/`medium` finding and
  puts a concrete, runnable test in the finding's `suggestion` field, matching
  the project's existing test idiom. Renames, comments, and trivial formatting
  changes are left alone.
- **Documentation gaps** — public/exported surfaces added without a docstring, or
  a name or signature that contradicts what the code does, are flagged at
  `info`/`low`. This is deliberately restrained: private helpers and self-evident
  code are not nagged about, so well-named code is left to document itself.

## Performance

The reviewer also watches for performance regressions the change introduces,
graded by impact (`low` up to `high` when the cost scales with input size or sits
in a hot path):

- **N+1 queries / calls in a loop** — a query, request, or other expensive call
  issued once per iteration that could be batched or hoisted out.
- **Inefficient algorithms** — accidentally quadratic (`O(n²)`) work where linear
  is feasible, or a linear scan where a set/dict lookup would do.
- **Redundant computation** — recomputing the same value inside a loop instead of
  hoisting or memoising it.
- **Unnecessary allocations & copies** — building large intermediates or copying
  big buffers on a hot path when streaming or in-place work suffices.
- **Blocking I/O on a hot path** — synchronous I/O, sleeps, or lock contention
  where non-blocking handling is expected.
- **Unbounded / over-fetching queries** — loading whole tables into memory or
  missing pagination/limits.

It sticks to changes the diff actually shows and avoids micro-optimisations with
no measurable impact.

## Complexity

A lighter, restrained lens that flags code harder to read, test, or maintain than
it needs to be (`info`/`medium`), preferring a concrete simplification in the
`suggestion` field:

- **High cyclomatic complexity / deep nesting** — many branches or deeply nested
  conditionals and loops that would read better with early returns.
- **Over-long, low-cohesion functions** — a function doing several unrelated
  things that should be split apart.
- **Duplicated logic** — non-trivial logic repeated in the diff that should be
  extracted into a shared helper.
- **Excessive parameters / boolean-flag arguments**, **convoluted expressions**,
  and **dead / unreachable code**.

Like the documentation lens, it stays quiet on self-evident, already-simple code.

## How the scope is bounded

Every run is bounded so a large PR can't run away on latency. All of these are
configurable in `.lgtmaybe.yml` (see
[Configure .lgtmaybe.yml](../how-to/configure-lgtmaybe-yml.md)):

| Knob | Default | Effect |
|---|---|---|
| `max_files` | 50 | Reviews the top-N changed files; posts a "reviewed top N of M" notice if there are more. |
| `max_input_tokens` | 100,000 | Batches the diff so each model call stays within budget. |
| `categories` | all seven | Which review lenses to run; each runs as its own model call. Narrowing the list means fewer calls. |
| `context_lines` | 20 | Ceiling on surrounding lines added around each hunk; the budget may use fewer. `0` disables context expansion. |
| `min_severity` | `info` | Drops findings below the chosen floor (`info` → `low` → `medium` → `high` → `critical`). |
| `include_paths` / `exclude_paths` | — | Glob filters to focus the review. |

> These bound a **single run**, not the number of runs. On a public repo, anyone
> who can open a PR or comment can trigger a run, and each run calls your chosen
> LLM provider — see the cost disclaimer in
> [Use as a GitHub Action](../how-to/use-as-github-action.md).

## What a finding contains

Findings are structured data, not prose, so they render identically everywhere.
Each finding has:

| Field | Meaning |
|---|---|
| `path` | File the comment attaches to |
| `line` | Line in the diff |
| `side` | `RIGHT` (added/changed) or `LEFT` (removed) |
| `severity` | `info` / `low` / `medium` / `high` / `critical` |
| `title` | One-line summary |
| `body` | The explanation |
| `suggestion` | Optional suggested replacement code |

Each review category (security, correctness, deprecation, tests, documentation,
performance, complexity)
runs as its own concurrent model call with a focused prompt; their findings are
merged and de-duplicated. A self-reflection pass then runs over the merged set
and drops low-confidence findings, so the model's first guesses are filtered
before anything is posted.

## What the response looks like

### On a GitHub pull request

lgtmaybe posts **one review** containing:

- an **inline comment** on the exact changed line for each finding, and
- a **summary comment** that names the model used.

The summary carries a hidden marker (`<!-- lgtmaybe -->`), so re-running on the
same PR **updates** the existing review instead of creating duplicates. When a
PR is clean (no findings, and every file was within the caps), the summary is a
simple:

```
👍 LGTM!

0 findings · model claude-sonnet-4-6
```

If the file cap kicked in, the summary says so (e.g. "Reviewed the top 50 of 120
changed files"). lgtmaybe never fails silently — any error is surfaced back to
the PR as a short comment.

### On the command line

`lgtmaybe review` runs the same pipeline over your local `git` diff and prints
the findings — it posts nothing and needs no GitHub token. By default it diffs
the current branch against the default branch; `--working` reviews uncommitted
edits and `--base <ref>` picks a different base. The default output is a readable
listing followed by the summary line:

```console
$ lgtmaybe review --provider ollama --model qwen3.6:27b --api-base http://localhost:11434
src/app.py:2  [MEDIUM] Import order
  sys should be sorted before os

1 finding · model qwen3.6:27b
```

`--format` selects the output. `--json` is shorthand for `--format json`, which
prints the findings as a JSON array so the same structured data can be piped into
other tooling:

```console
$ lgtmaybe review --provider ollama --model qwen3.6:27b --api-base http://localhost:11434 --json
[{"path": "src/app.py", "line": 2, "side": "RIGHT", "severity": "medium",
  "title": "Import order", "body": "sys should be sorted before os",
  "suggestion": null}]
```

`--format agent` turns the findings into plain correction instructions an AI
coding agent can read and apply — a local review-and-fix loop. See
[Fix findings with an AI agent](../how-to/fix-findings-with-an-ai-agent.md).

## See also

- [Getting Started](../tutorial/getting-started.md) — run your first review
- [Architecture](architecture.md) — the fetch → compress → prompt → parse → post pipeline
- [Data and Privacy](data-and-privacy.md) — what is sent where
