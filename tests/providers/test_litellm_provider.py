"""Tests for LiteLLMProvider — the litellm adapter.

All tests monkeypatch litellm.completion at the boundary so no real network
calls are made.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from lgtmaybe.core.models import ProviderResult
from lgtmaybe.providers.litellm_provider import LiteLLMProvider


def _fake_response(
    content: str = "hello",
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
) -> Any:
    """Build a minimal litellm ModelResponse lookalike."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
    )


class TestLiteLLMProvider:
    def test_complete_returns_provider_result_with_text(self) -> None:
        response = _fake_response(content="some text")
        with patch("litellm.completion", return_value=response):
            with patch("litellm.completion_cost", return_value=0.0042):
                provider = LiteLLMProvider()
                result = provider.complete([{"role": "user", "content": "hi"}], "openai/gpt-4o")

        assert result.text == "some text"

    def test_complete_maps_token_counts_from_usage(self) -> None:
        response = _fake_response(prompt_tokens=50, completion_tokens=100)
        with patch("litellm.completion", return_value=response):
            with patch("litellm.completion_cost", return_value=0.0):
                provider = LiteLLMProvider()
                result = provider.complete([{"role": "user", "content": "hi"}], "openai/gpt-4o")

        assert result.input_tokens == 50
        assert result.output_tokens == 100

    def test_complete_maps_cost_from_completion_cost(self) -> None:
        response = _fake_response()
        with patch("litellm.completion", return_value=response):
            with patch("litellm.completion_cost", return_value=0.0099):
                provider = LiteLLMProvider()
                result = provider.complete([{"role": "user", "content": "hi"}], "openai/gpt-4o")

        assert result.cost_usd == pytest.approx(0.0099)

    def test_complete_falls_back_to_zero_cost_on_completion_cost_error(self) -> None:
        response = _fake_response()
        with patch("litellm.completion", return_value=response):
            with patch("litellm.completion_cost", side_effect=Exception("unknown model")):
                provider = LiteLLMProvider()
                result = provider.complete([{"role": "user", "content": "hi"}], "openai/gpt-4o")

        assert result.cost_usd == 0.0

    def test_complete_passes_messages_and_model_to_litellm(self) -> None:
        response = _fake_response()
        messages = [{"role": "user", "content": "review this"}]
        with patch("litellm.completion", return_value=response) as mock_completion:
            with patch("litellm.completion_cost", return_value=0.0):
                provider = LiteLLMProvider()
                provider.complete(messages, "openai/gpt-4o")

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args
        assert (
            call_kwargs.kwargs["model"] == "openai/gpt-4o" or call_kwargs.args[0] == "openai/gpt-4o"
        )
        assert messages in call_kwargs.args or call_kwargs.kwargs.get("messages") == messages

    def test_complete_passes_extra_opts_to_litellm(self) -> None:
        response = _fake_response()
        with patch("litellm.completion", return_value=response) as mock_completion:
            with patch("litellm.completion_cost", return_value=0.0):
                provider = LiteLLMProvider()
                provider.complete(
                    [{"role": "user", "content": "hi"}],
                    "openai/gpt-4o",
                    api_key="sk-test",
                )

        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs.get("api_key") == "sk-test"

    def test_complete_sets_timeout_on_litellm_call(self) -> None:
        response = _fake_response()
        with patch("litellm.completion", return_value=response) as mock_completion:
            with patch("litellm.completion_cost", return_value=0.0):
                provider = LiteLLMProvider()
                provider.complete([{"role": "user", "content": "hi"}], "openai/gpt-4o")

        call_kwargs = mock_completion.call_args.kwargs
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] > 0

    def test_result_is_provider_result_instance(self) -> None:
        response = _fake_response()
        with patch("litellm.completion", return_value=response):
            with patch("litellm.completion_cost", return_value=0.0):
                provider = LiteLLMProvider()
                result = provider.complete([{"role": "user", "content": "hi"}], "openai/gpt-4o")

        assert isinstance(result, ProviderResult)
