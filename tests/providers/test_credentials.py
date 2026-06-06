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
