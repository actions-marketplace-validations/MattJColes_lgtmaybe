# Review with Google Vertex AI (keyless WIF)

Use this guide to run lgtmaybe with **Google Vertex AI** using Workload Identity
Federation — no service-account JSON or static keys in secrets.

## How it works

GitHub Actions issues an OIDC token. GCP's Workload Identity Federation
exchanges that token for a short-lived GCP access token, impersonating a service
account that has only the Vertex AI permissions it needs. lgtmaybe uses
Application Default Credentials (ADC) to pick up those tokens automatically.

## Prerequisites

- A GCP project with the Vertex AI API enabled
- A Workload Identity Pool and Provider configured for GitHub Actions
- A GCP service account that lgtmaybe will impersonate, with
  `roles/aiplatform.user` on the project
- The Workload Identity Provider resource name and the service account email

See `manual-steps.md` for the one-time GCP and GitHub setup that a human must
perform.

## Workflow example

```yaml
name: pr-review

on:
  pull_request_target:
    types: [opened, synchronize]

permissions:
  id-token: write          # required for WIF token exchange
  pull-requests: write     # required to post review comments
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Authenticate to GCP (WIF)
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: >-
            projects/123456789/locations/global/workloadIdentityPools/github/providers/github
          service_account: lgtmaybe@my-project.iam.gserviceaccount.com

      - name: Run lgtmaybe
        uses: ghcr.io/lgtmaybe/lgtmaybe@latest
        with:
          pr-url: ${{ github.event.pull_request.html_url }}
          provider: vertex
          model: gemini-2.0-flash-001
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          VERTEXAI_PROJECT: my-project
          VERTEXAI_LOCATION: us-central1
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `VERTEXAI_PROJECT` | Yes | GCP project ID |
| `VERTEXAI_LOCATION` | No | Region (default: `us-central1`) |

## Available Vertex AI models

| Model | Vertex model ID |
|---|---|
| Gemini 2.0 Flash | `gemini-2.0-flash-001` |
| Gemini 2.0 Pro | `gemini-2.0-pro-exp-02-05` |
| Gemini 1.5 Flash | `gemini-1.5-flash-002` |
| Gemini 1.5 Pro | `gemini-1.5-pro-002` |

## Running locally with ADC

If your local shell has application default credentials (`gcloud auth
application-default login`):

```bash
export VERTEXAI_PROJECT=my-project
export VERTEXAI_LOCATION=us-central1

lgtmaybe review \
  --pr-url https://github.com/owner/repo/pull/42 \
  --provider vertex \
  --model gemini-2.0-flash-001
```

lgtmaybe does not accept a static API key for Vertex.

## Required IAM role

The service account needs `roles/aiplatform.user` on the GCP project, which
grants `aiplatform.endpoints.predict`. Do not assign broader project-level roles.

## Troubleshooting

**`UNAUTHENTICATED`** — ADC credentials are missing or expired. Run
`gcloud auth application-default login` locally, or verify the WIF provider and
service account impersonation binding in CI.

**`PERMISSION_DENIED`** — the service account lacks `roles/aiplatform.user`, or
the Vertex AI API is not enabled in the project. Enable it with:

```bash
gcloud services enable aiplatform.googleapis.com --project=my-project
```

**`Model not found`** — the model ID may not be available in your selected
region. Check the [Vertex AI model garden](https://console.cloud.google.com/vertex-ai/model-garden).
