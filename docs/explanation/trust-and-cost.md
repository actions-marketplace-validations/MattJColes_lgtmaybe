# Trust and Cost

This document explains lgtmaybe's trust and cost model: who can cause a review
to run, why that matters financially, and how the default workflows keep a
stranger from spending your provider budget. It is background for the
step-by-step setup in
[Use as a GitHub Action](../how-to/use-as-github-action.md).

## Every review costs money

A review is a call to your chosen LLM provider, and **you pay for the tokens it
uses**. ollama is the exception — it runs the model on your own machine at zero
marginal cost — but every hosted provider (OpenAI, Anthropic, OpenRouter,
Bedrock, Vertex, Azure) bills you per run.

That makes "who can start a review" a spending question, not just a permissions
question. On a public repository the raw triggers — `pull_request_target` and
`issue_comment` — fire for *anyone*: a stranger opening a fork PR, or a drive-by
`/ask` / `/review` comment, would each cost you tokens, and every push to an open
PR triggers another run. Without a gate, your provider bill is open to the
internet.

## Two kinds of bound

It helps to separate the two limits, because they protect against different
things:

- **Per-run caps bound the size of one review.** `max_files` (default 50) and
  `max_input_tokens` (default 100k) keep a single large PR from ballooning into
  a huge request. See [What gets reviewed](what-gets-reviewed.md) for how the
  diff is capped and batched.
- **The trigger gate bounds how many runs happen at all.** The caps above do
  nothing about a thousand drive-by comments; only restricting *who* can trigger
  a review does that.

You need both. The caps are on by default in the engine; the gate lives in the
workflow.

## The trust gate: author association

The example workflows in
[`examples/workflows/`](https://github.com/MattJColes/lgtmaybe/tree/main/examples/workflows)
gate the `review` job on the triggering user's
[author association](https://docs.github.com/en/graphql/reference/enums#commentauthorassociation)
— GitHub's classification of a user's relationship to the repository. The job
only runs when that association is `OWNER`, `MEMBER`, or `COLLABORATOR`:

```yaml
if: >-
  (github.event_name == 'pull_request_target' &&
   contains(fromJson('["OWNER", "MEMBER", "COLLABORATOR"]'), github.event.pull_request.author_association)) ||
  (github.event.issue.pull_request &&
   contains(fromJson('["OWNER", "MEMBER", "COLLABORATOR"]'), github.event.comment.author_association))
```

The consequence: a fork PR from a stranger has association `NONE`, so the job is
skipped and **no tokens are spent**. The same gate covers slash commands — a
`/review` or `/ask` from a non-member never runs. A maintainer can still review
an outside contributor's PR by commenting `/review` on it themselves, because
*their* association passes the gate. This is a deliberate opt-in: trust is
asserted by someone who already has it.

Because the gate lives in the workflow YAML rather than in the action's code,
it is yours to tune. Widen it by adding `CONTRIBUTOR` (auto-review anyone whose
PR has merged before), or narrow it by dropping `COLLABORATOR`. The trade-off is
purely yours to make — the action runs whatever the workflow lets through.

## Defence in depth

The author gate is the primary control, but it is a single line of YAML. For
anything spending real money, layer more underneath it:

- **Require approval for fork-PR workflow runs** in
  **Settings → Actions → General → Fork pull request workflows**, so a human
  okays the run even if the gate is ever weakened.
- **Move the provider key behind a protected `environment`**, so the secret is
  only available to runs that clear the environment's rules.
- **Set a spending limit in your provider console** as the financial backstop —
  the only control that holds no matter what the workflow does.

## Why this is safe to expose at all

Restricting *who* triggers a review is about cost. A separate mechanism keeps a
malicious PR from doing harm even when a review does run: lgtmaybe triggers on
`pull_request_target` (so it has the base-branch secrets it needs) but **never
checks out or executes PR code** — it fetches the diff through the GitHub API and
treats every byte of it as untrusted input. So an outside PR cannot exfiltrate
your secrets through the build, regardless of the gate. The full treatment of
that boundary — secret redaction, prompt-injection defence, and fork safety —
is in [Data and Privacy](data-and-privacy.md).
