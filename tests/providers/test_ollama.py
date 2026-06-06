"""Tests for the ollama path: api_base config and zero cost."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from lgtmaybe.core.models import Provider
from lgtmaybe.providers.factory import build_provider


def _fake_response(content: str = "ok") -> Any:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=10),
    )


class TestOllamaPath:
    def test_ollama_routes_to_configured_api_base(self) -> None:
        api_base = "http://host.docker.internal:11434"
        provider = build_provider(Provider.ollama, "llama2", api_base=api_base)
        assert provider.default_opts.get("api_base") == api_base

    def test_ollama_model_string_has_ollama_prefix(self) -> None:
        provider = build_provider(Provider.ollama, "llama2")
        assert provider.model == "ollama/llama2"

    def test_ollama_cost_is_always_zero(self) -> None:
        """Ollama completions must report 0.0 cost regardless of litellm."""
        api_base = "http://localhost:11434"
        provider = build_provider(Provider.ollama, "llama2", api_base=api_base)

        response = _fake_response("hello from ollama")
        # Even if completion_cost would return something, ollama overrides it
        with patch("litellm.completion", return_value=response):
            with patch("litellm.completion_cost", return_value=99.99):
                result = provider.complete([{"role": "user", "content": "hi"}], provider.model)

        assert result.cost_usd == 0.0

    def test_ollama_default_api_base_is_localhost(self) -> None:
        provider = build_provider(Provider.ollama, "llama2")
        assert "localhost" in (provider.default_opts.get("api_base") or "")

    def test_ollama_tailscale_host_api_base(self) -> None:
        tailscale_base = "http://100.64.0.1:11434"
        provider = build_provider(Provider.ollama, "llama2", api_base=tailscale_base)
        assert provider.default_opts.get("api_base") == tailscale_base
