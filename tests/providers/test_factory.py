"""Tests for the provider factory — maps (Provider, model) -> litellm model string."""

from __future__ import annotations

from lgtmaybe.core.models import Provider
from lgtmaybe.providers.factory import build_provider, litellm_model_string


class TestLiteLLMModelString:
    def test_openai_prefix(self) -> None:
        assert litellm_model_string(Provider.openai, "gpt-4o") == "openai/gpt-4o"

    def test_anthropic_prefix(self) -> None:
        assert (
            litellm_model_string(Provider.anthropic, "claude-3-haiku-20240307")
            == "anthropic/claude-3-haiku-20240307"
        )

    def test_openrouter_prefix(self) -> None:
        assert (
            litellm_model_string(Provider.openrouter, "meta-llama/llama-3-70b-instruct")
            == "openrouter/meta-llama/llama-3-70b-instruct"
        )

    def test_bedrock_prefix(self) -> None:
        assert (
            litellm_model_string(Provider.bedrock, "anthropic.claude-3-haiku-20240307-v1:0")
            == "bedrock/anthropic.claude-3-haiku-20240307-v1:0"
        )

    def test_vertex_prefix(self) -> None:
        assert (
            litellm_model_string(Provider.vertex, "gemini-2.0-flash")
            == "vertex_ai/gemini-2.0-flash"
        )

    def test_ollama_prefix(self) -> None:
        assert litellm_model_string(Provider.ollama, "llama2") == "ollama/llama2"

    def test_azure_prefix(self) -> None:
        assert litellm_model_string(Provider.azure, "gpt-4o") == "azure/gpt-4o"


class TestBuildProvider:
    def test_build_provider_returns_litellm_provider(self) -> None:
        from lgtmaybe.providers.litellm_provider import LiteLLMProvider

        provider = build_provider(Provider.openai, "gpt-4o", api_key="sk-test")
        assert isinstance(provider, LiteLLMProvider)

    def test_build_provider_openai_carries_api_key(self) -> None:
        from lgtmaybe.providers.litellm_provider import LiteLLMProvider

        provider = build_provider(Provider.openai, "gpt-4o", api_key="sk-test")
        assert isinstance(provider, LiteLLMProvider)
        assert provider.default_opts.get("api_key") == "sk-test"

    def test_build_provider_ollama_carries_api_base(self) -> None:
        from lgtmaybe.providers.litellm_provider import LiteLLMProvider

        provider = build_provider(Provider.ollama, "llama2", api_base="http://localhost:11434")
        assert isinstance(provider, LiteLLMProvider)
        assert provider.default_opts.get("api_base") == "http://localhost:11434"

    def test_build_provider_azure_carries_api_key_and_base(self) -> None:
        from lgtmaybe.providers.litellm_provider import LiteLLMProvider

        provider = build_provider(
            Provider.azure,
            "gpt-4o",
            api_key="azure-secret",
            api_base="https://my-resource.openai.azure.com",
        )
        assert isinstance(provider, LiteLLMProvider)
        assert provider.default_opts.get("api_key") == "azure-secret"
        assert provider.default_opts.get("api_base") == "https://my-resource.openai.azure.com"
        assert provider.model == "azure/gpt-4o"

    def test_build_provider_azure_keyless_carries_ad_token(self) -> None:
        from lgtmaybe.providers.litellm_provider import LiteLLMProvider

        provider = build_provider(
            Provider.azure,
            "gpt-4o",
            api_base="https://my-resource.openai.azure.com",
            azure_ad_token="ad-token-xyz",
        )
        assert isinstance(provider, LiteLLMProvider)
        assert provider.default_opts.get("azure_ad_token") == "ad-token-xyz"
        assert provider.default_opts.get("api_base") == "https://my-resource.openai.azure.com"
        assert "api_key" not in provider.default_opts

    def test_build_provider_stores_resolved_model_string(self) -> None:
        provider = build_provider(Provider.bedrock, "anthropic.claude-3-haiku-20240307-v1:0")
        assert provider.model == "bedrock/anthropic.claude-3-haiku-20240307-v1:0"

    def test_build_provider_resolves_fallback_model(self) -> None:
        provider = build_provider(Provider.ollama, "qwen3:27b", fallback_model="llama2")
        assert provider.fallback_model == "ollama/llama2"

    def test_build_provider_threads_timeout_into_default_opts(self) -> None:
        provider = build_provider(Provider.ollama, "llama2", timeout=600)
        assert provider.default_opts.get("timeout") == 600

    def test_build_provider_threads_temperature_into_default_opts(self) -> None:
        provider = build_provider(Provider.ollama, "llama2", temperature=0.0)
        assert provider.default_opts.get("temperature") == 0.0

    def test_factory_provider_calls_litellm_with_resolved_model(self) -> None:
        """The engine passes the raw cfg.model; the call must still use the
        factory-resolved model string (regression for 'LLM Provider NOT provided')."""
        from types import SimpleNamespace
        from unittest.mock import patch

        provider = build_provider(Provider.ollama, "qwen3:27b", api_base="http://localhost:11434")
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="[]"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )

        with patch("litellm.completion", return_value=response) as mock_completion:
            with patch("litellm.completion_cost", return_value=0.0):
                provider.complete([{"role": "user", "content": "hi"}], model="qwen3:27b")

        assert mock_completion.call_args.kwargs["model"] == "ollama/qwen3:27b"
