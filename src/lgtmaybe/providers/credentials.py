"""Credential resolver — chain of responsibility pattern.

Given a Provider and optional explicit credentials, resolves the auth config
or raises a clear, actionable error naming the exact remediation.

The ambient_probe parameter makes the cloud-creds check injectable so tests
never touch real AWS/GCP.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lgtmaybe.core.models import Provider

_DEFAULT_OLLAMA_BASE = "http://localhost:11434"


@dataclass(frozen=True)
class AuthConfig:
    api_key: str | None = None
    api_base: str | None = None


def _default_aws_probe() -> bool:
    """Detect ambient AWS credentials via environment variables."""
    import os

    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID")
        or os.environ.get("AWS_PROFILE")
        or os.environ.get("AWS_ROLE_ARN")
        or os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE")
    )


def _default_gcp_probe() -> bool:
    """Detect ambient GCP credentials via environment variables."""
    import os

    return bool(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
    )


def resolve_credentials(
    provider: Provider,
    *,
    api_key: str | None = None,
    api_base: str | None = None,
    ambient_probe: Callable[[], bool] | None = None,
) -> AuthConfig:
    """Resolve auth for the given provider.

    Raises ValueError with a clear remediation message when no valid auth
    can be found.
    """
    if provider is Provider.bedrock:
        probe = ambient_probe if ambient_probe is not None else _default_aws_probe
        if not probe():
            raise ValueError(
                "bedrock requires ambient AWS credentials. "
                "Configure an OIDC role (AWS_ROLE_ARN + AWS_WEB_IDENTITY_TOKEN_FILE), "
                "a named profile (AWS_PROFILE), or set AWS_ACCESS_KEY_ID / "
                "AWS_SECRET_ACCESS_KEY in the environment."
            )
        return AuthConfig()

    if provider is Provider.vertex:
        probe = ambient_probe if ambient_probe is not None else _default_gcp_probe
        if not probe():
            raise ValueError(
                "vertex requires ambient GCP credentials. "
                "Configure Workload Identity Federation, set GOOGLE_APPLICATION_CREDENTIALS "
                "to a service-account key file, or run 'gcloud auth application-default login'."
            )
        return AuthConfig()

    if provider is Provider.azure:
        import os

        key = api_key or os.environ.get("AZURE_API_KEY")
        base = api_base or os.environ.get("AZURE_API_BASE")
        if not key:
            raise ValueError(
                "azure requires an API key. Set the AZURE_API_KEY environment "
                "variable or pass --api-key."
            )
        if not base:
            raise ValueError(
                "azure requires the resource endpoint. Set the AZURE_API_BASE "
                "environment variable (e.g. https://<resource>.openai.azure.com) "
                "or pass --api-base."
            )
        return AuthConfig(api_key=key, api_base=base)

    if provider is Provider.ollama:
        return AuthConfig(api_base=api_base or _DEFAULT_OLLAMA_BASE)

    # API-key providers: openai, anthropic, openrouter
    _ENV_VAR: dict[Provider, str] = {
        Provider.openai: "OPENAI_API_KEY",
        Provider.anthropic: "ANTHROPIC_API_KEY",
        Provider.openrouter: "OPENROUTER_API_KEY",
    }
    env_var = _ENV_VAR[provider]

    if api_key:
        return AuthConfig(api_key=api_key)

    import os

    key_from_env = os.environ.get(env_var)
    if key_from_env:
        return AuthConfig(api_key=key_from_env)

    raise ValueError(
        f"{provider} requires an API key. Set the {env_var} environment variable or pass --api-key."
    )
