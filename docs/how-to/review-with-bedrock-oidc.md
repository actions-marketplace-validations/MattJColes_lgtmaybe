# Review with AWS Bedrock (keyless OIDC)

Use this guide to run lgtmaybe with **AWS Bedrock** using GitHub's OIDC token
— no static AWS credentials stored in secrets.

## How it works

GitHub Actions issues a short-lived OIDC token. AWS STS exchanges that token
for temporary IAM credentials scoped to a role you control. The action performs
that exchange for you (pass `aws_role_arn`) and lgtmaybe picks up the ambient
credentials automatically — no `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`
in your secrets.

## One-time AWS setup

This is the human-only part — do it once in your AWS account:

1. Create an IAM **OIDC identity provider** for `token.actions.githubusercontent.com`.
2. Create an IAM **role** with a trust policy scoped to your repo
   (`repo:<org>/lgtmaybe:*`).
3. Attach the least-privilege policy below.
4. Confirm the models you want are enabled in the target region (model access
   request in the Bedrock console).
5. Note the **role ARN** (e.g. `arn:aws:iam::123456789012:role/lgtmaybe-bedrock`)
   — it becomes the `aws_role_arn` action input. No static key is ever stored.

The role needs only:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "arn:aws:bedrock:*::foundation-model/*"
}
```

Scope `Resource` to specific model ARNs for tighter least-privilege.

## Workflow example

The action assumes the role for you — no separate `configure-aws-credentials`
step needed. Store the role ARN in an `AWS_ROLE_ARN` secret.

```yaml
name: lgtmaybe

on:
  pull_request_target:
  issue_comment:
    types: [created]

permissions:
  id-token: write          # required for the OIDC token exchange (keyless)
  pull-requests: write     # required to post review comments
  contents: read

jobs:
  review:
    if: ${{ github.event_name == 'pull_request_target' || github.event.issue.pull_request }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: MattJColes/lgtmaybe@v0
        with:
          provider: bedrock
          model: anthropic.claude-sonnet-4-6
          aws_role_arn: ${{ secrets.AWS_ROLE_ARN }}
          aws_region: us-east-1
```

## Choosing a Bedrock model ID

| Model | Bedrock model ID |
|---|---|
| Claude Opus 4.8 | `anthropic.claude-opus-4-8` |
| Claude Sonnet 4.6 | `anthropic.claude-sonnet-4-6` |
| Claude Haiku 4.5 | `anthropic.claude-haiku-4-5` |

For tighter availability across regions, prefix with a cross-region inference
profile (e.g. `us.anthropic.claude-sonnet-4-6`) where one is enabled for your
account.

## Running locally with ambient AWS credentials

If your local shell has AWS credentials (via `~/.aws`, SSO, or an assumed role),
you can review your current branch's changes with Bedrock. Bedrock signing needs
`boto3`, so install the extra (the Action image already bundles it):

```bash
pip install 'lgtmaybe[bedrock]'

lgtmaybe review \
  --provider bedrock \
  --model anthropic.claude-haiku-4-5
```

lgtmaybe does not require or accept a static API key for Bedrock.

## Troubleshooting

**`ExpiredTokenException`** — the OIDC exchange failed or the role session
expired. Check that `id-token: write` permission is present in the workflow and
that the IAM trust policy references the correct GitHub repository.

**`AccessDeniedException`** — the role lacks `bedrock:InvokeModel` for the
selected model, or the model is not enabled in the Bedrock console for your
account and region.
