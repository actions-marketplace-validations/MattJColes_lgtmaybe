# Review with AWS Bedrock (keyless OIDC)

Use this guide to run lgtmaybe with **AWS Bedrock** using GitHub's OIDC token
— no static AWS credentials stored in secrets.

## How it works

GitHub Actions issues a short-lived OIDC token. AWS STS exchanges that token
for temporary IAM credentials scoped to a role you control. lgtmaybe picks up
those ambient credentials automatically — no `AWS_ACCESS_KEY_ID` or
`AWS_SECRET_ACCESS_KEY` in your secrets.

## Prerequisites

- An AWS account with Bedrock enabled in your target region
- An IAM role that trusts GitHub's OIDC provider and grants
  `bedrock:InvokeModel` on the models you want to use
- The role ARN (e.g. `arn:aws:iam::123456789012:role/lgtmaybe-bedrock`)

See `manual-steps.md` for the one-time AWS and GitHub setup that a human must
perform.

## Workflow example

```yaml
name: pr-review

on:
  pull_request_target:
    types: [opened, synchronize]

permissions:
  id-token: write          # required for OIDC token issuance
  pull-requests: write     # required to post review comments
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/lgtmaybe-bedrock
          aws-region: us-east-1

      - name: Run lgtmaybe
        uses: ghcr.io/lgtmaybe/lgtmaybe@latest
        with:
          pr-url: ${{ github.event.pull_request.html_url }}
          provider: bedrock
          model: us.anthropic.claude-3-5-sonnet-20241022-v2:0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Choosing a Bedrock model ID

Use the cross-region inference profile IDs to improve availability:

| Model | Bedrock model ID |
|---|---|
| Claude 3.5 Sonnet v2 | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` |
| Claude 3.5 Haiku | `us.anthropic.claude-3-5-haiku-20241022-v1:0` |
| Claude 3 Haiku | `us.anthropic.claude-3-haiku-20240307-v1:0` |

## Running locally with ambient AWS credentials

If your local shell has AWS credentials (via `~/.aws`, SSO, or an assumed role):

```bash
lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider bedrock \
  --model us.anthropic.claude-3-5-haiku-20241022-v1:0
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
