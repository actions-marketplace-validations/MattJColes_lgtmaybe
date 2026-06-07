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

## How the scope is bounded

Every run is bounded so a large PR can't run away on latency or cost. All of
these are configurable in `.lgtmaybe.yml` (see
[Configure .lgtmaybe.yml](../how-to/configure-lgtmaybe-yml.md)):

| Knob | Default | Effect |
|---|---|---|
| `max_files` | 50 | Reviews the top-N changed files; posts a "reviewed top N of M" notice if there are more. |
| `max_input_tokens` | 100,000 | Batches the diff so each model call stays within budget. |
| `context_lines` | 20 | Ceiling on surrounding lines added around each hunk; the budget may use fewer. `0` disables context expansion. |
| `min_severity` | `info` | Drops findings below the chosen floor (`info` → `low` → `medium` → `high` → `critical`). |
| `include_paths` / `exclude_paths` | — | Glob filters to focus the review. |

> Cost note: these bound a **single run**, not the number of runs. On a public
> repo, anyone who can open a PR or comment can trigger a run — see the cost
> disclaimer in [Use as a GitHub Action](../how-to/use-as-github-action.md).

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

A self-reflection pass runs after the first draft and drops low-confidence
findings, so the model's first guesses are filtered before anything is posted.

## What the response looks like

### On a GitHub pull request

lgtmaybe posts **one review** containing:

- an **inline comment** on the exact changed line for each finding, and
- a **summary comment** that names the model and the approximate cost.

The summary carries a hidden marker (`<!-- lgtmaybe -->`), so re-running on the
same PR **updates** the existing review instead of creating duplicates. When a
PR is clean (no findings, and every file was within the caps), the summary is a
simple:

```
👍 LGTM!

0 findings · model claude-sonnet-4-6 · approx cost $0.0123
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

1 finding · model qwen3.6:27b · approx cost $0.0000
```

Add `--json` to print the findings as a JSON array instead, so the same
structured data can be piped into other tooling:

```console
$ lgtmaybe review --provider ollama --model qwen3.6:27b --api-base http://localhost:11434 --json
[{"path": "src/app.py", "line": 2, "side": "RIGHT", "severity": "medium",
  "title": "Import order", "body": "sys should be sorted before os",
  "suggestion": null}]
```

## See also

- [Getting Started](../tutorial/getting-started.md) — run your first review
- [Architecture](architecture.md) — the fetch → compress → prompt → parse → post pipeline
- [Data and Privacy](data-and-privacy.md) — what is sent where
