"""Tests for the credential resolver (chain of responsibility)."""

from __future__ import annotations

import pytest

from lgtmaybe.core.models import Provider
from lgtmaybe.providers.credentials import resolve_credentials

# ---- probe stubs ----


def _ambient_present() -> bool:
    return True


def _ambient_absent() -> bool:
    return False


class TestBedrock:
    def test_bedrock_with_ambient_creds_resolves_keyless(self) -> None:
        config = resolve_credentials(
            Provider.bedrock,
            ambient_probe=_ambient_present,
        )
        assert config.api_key is None

    def test_bedrock_without_ambient_creds_raises_helpful_error(self) -> None:
        with pytest.raises(ValueError, match="bedrock") as exc_info:
            resolve_credentials(
                Provider.bedrock,
                ambient_probe=_ambient_absent,
            )
        # Error must name a concrete remediation
        assert (
            "AWS" in str(exc_info.value)
            or "OIDC" in str(exc_info.value)
            or "aws" in str(exc_info.value).lower()
        )

    def test_bedrock_error_message_names_the_provider(self) -> None:
        with pytest.raises(ValueError, match="bedrock"):
            resolve_credentials(Provider.bedrock, ambient_probe=_ambient_absent)


class TestVertex:
    def test_vertex_with_ambient_creds_resolves_keyless(self) -> None:
        config = resolve_credentials(
            Provider.vertex,
            ambient_probe=_ambient_present,
        )
        assert config.api_key is None

    def test_vertex_without_ambient_creds_raises_helpful_error(self) -> None:
        with pytest.raises(ValueError, match="vertex") as exc_info:
            resolve_credentials(
                Provider.vertex,
                ambient_probe=_ambient_absent,
            )
        assert (
            "GCP" in str(exc_info.value)
            or "GOOGLE" in str(exc_info.value)
            or "gcp" in str(exc_info.value).lower()
            or "google" in str(exc_info.value).lower()
        )


class TestOpenAI:
    def test_openai_with_api_key_resolves(self) -> None:
        config = resolve_credentials(Provider.openai, api_key="sk-abc")
        assert config.api_key == "sk-abc"

    def test_openai_without_key_raises_helpful_error(self) -> None:
        with pytest.raises(ValueError, match="openai") as exc_info:
            resolve_credentials(Provider.openai)
        msg = str(exc_info.value).lower()
        # Must tell user how to fix it
        assert "api" in msg or "key" in msg or "OPENAI_API_KEY" in str(exc_info.value)

    def test_openai_error_names_the_env_var(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            resolve_credentials(Provider.openai)
        assert "OPENAI_API_KEY" in str(exc_info.value)


class TestAnthropic:
    def test_anthropic_with_api_key_resolves(self) -> None:
        config = resolve_credentials(Provider.anthropic, api_key="sk-ant-xyz")
        assert config.api_key == "sk-ant-xyz"

    def test_anthropic_without_key_raises_helpful_error(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            resolve_credentials(Provider.anthropic)
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)


class TestOpenRouter:
    def test_openrouter_with_api_key_resolves(self) -> None:
        config = resolve_credentials(Provider.openrouter, api_key="sk-or-test")
        assert config.api_key == "sk-or-test"

    def test_openrouter_without_key_raises_helpful_error(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            resolve_credentials(Provider.openrouter)
        assert "OPENROUTER_API_KEY" in str(exc_info.value)


class TestAzure:
    def test_azure_with_api_key_and_base_resolves(self) -> None:
        config = resolve_credentials(
            Provider.azure,
            api_key="azure-secret",
            api_base="https://my-resource.openai.azure.com",
        )
        assert config.api_key == "azure-secret"
        assert config.api_base == "https://my-resource.openai.azure.com"
        assert config.azure_ad_token is None

    def test_azure_reads_key_and_base_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AZURE_API_KEY", "env-secret")
        monkeypatch.setenv("AZURE_API_BASE", "https://env-resource.openai.azure.com")
        config = resolve_credentials(Provider.azure)
        assert config.api_key == "env-secret"
        assert config.api_base == "https://env-resource.openai.azure.com"

    def test_azure_without_base_raises_helpful_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AZURE_API_BASE", raising=False)
        with pytest.raises(ValueError, match="azure") as exc_info:
            resolve_credentials(Provider.azure, api_key="azure-secret")
        assert "AZURE_API_BASE" in str(exc_info.value)

    def test_azure_keyless_resolves_with_ambient_ad_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No key, but ambient Azure AD creds yield a token — the keyless path."""
        monkeypatch.delenv("AZURE_API_KEY", raising=False)
        config = resolve_credentials(
            Provider.azure,
            api_base="https://my-resource.openai.azure.com",
            azure_token_provider=lambda: "ad-token-xyz",
        )
        assert config.api_key is None
        assert config.azure_ad_token == "ad-token-xyz"
        assert config.api_base == "https://my-resource.openai.azure.com"

    def test_azure_key_mode_preferred_over_keyless(self) -> None:
        """When a key is present the AD token provider is never consulted."""

        def _must_not_run() -> str | None:
            raise AssertionError("token provider should not be called in key mode")

        config = resolve_credentials(
            Provider.azure,
            api_key="azure-secret",
            api_base="https://my-resource.openai.azure.com",
            azure_token_provider=_must_not_run,
        )
        assert config.api_key == "azure-secret"
        assert config.azure_ad_token is None

    def test_azure_no_key_and_no_ambient_creds_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AZURE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="azure") as exc_info:
            resolve_credentials(
                Provider.azure,
                api_base="https://my-resource.openai.azure.com",
                azure_token_provider=lambda: None,
            )
        msg = str(exc_info.value)
        assert "AZURE_API_KEY" in msg
        assert "OIDC" in msg or "keyless" in msg.lower()


class TestOllama:
    def test_ollama_resolves_with_no_key_or_creds(self) -> None:
        config = resolve_credentials(Provider.ollama)
        assert config.api_key is None

    def test_ollama_resolves_with_custom_api_base(self) -> None:
        config = resolve_credentials(Provider.ollama, api_base="http://host.docker.internal:11434")
        assert config.api_base == "http://host.docker.internal:11434"

    def test_ollama_default_api_base_is_localhost(self) -> None:
        config = resolve_credentials(Provider.ollama)
        assert "localhost" in (config.api_base or "")
