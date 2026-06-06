# Review with AWS Bedrock (keyless OIDC)

Use this guide to run lgtmaybe with **AWS Bedrock** using GitHub's OIDC token
— no static AWS credentials stored in secrets.

## How it works

GitHub Actions issues a short-lived OIDC token. AWS STS exchanges that token
for temporary IAM credentials scoped to a role you control. The action performs
that exchange for you (pass `aws_role_arn`) and lgtmaybe picks up the ambient
credentials automatically — no `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`
in your secrets.

## Prerequisites

- An AWS account with Bedrock enabled in your target region
- An IAM role that trusts GitHub's OIDC provider and grants
  `bedrock:InvokeModel` on the models you want to use
- The role ARN (e.g. `arn:aws:iam::123456789012:role/lgtmaybe-bedrock`)

See `manual-steps.md` for the one-time AWS and GitHub setup that a human must
perform.

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
      - uses: actions/checkout@v4
      - uses: lgtmaybe/lgtmaybe@v1
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

If your local shell has AWS credentials (via `~/.aws`, SSO, or an assumed role):

```bash
lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider bedrock \
  --model anthropic.claude-haiku-4-5
```

lgtmaybe does not require or accept a static API key for Bedrock.

## Required IAM permissions

The IAM role needs:

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

## Troubleshooting

**`ExpiredTokenException`** — the OIDC exchange failed or the role session
expired. Check that `id-token: write` permission is present in the workflow and
that the IAM trust policy references the correct GitHub repository.

**`AccessDeniedException`** — the role lacks `bedrock:InvokeModel` for the
selected model, or the model is not enabled in the Bedrock console for your
account and region.
