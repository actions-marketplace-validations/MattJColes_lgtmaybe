"""LiteLLMProvider: the litellm adapter implementing ProviderClient.

Wraps litellm.completion with retry (tenacity), an explicit timeout, and
optional fallback model. Cost comes from litellm.completion_cost; falls back
to 0.0 when the model is unknown to litellm's cost map.
"""

from __future__ import annotations

from typing import Any

import litellm
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from lgtmaybe.core.models import ProviderResult
from lgtmaybe.core.ports import Message, ProviderClient

_DEFAULT_TIMEOUT = 60  # seconds
_MAX_ATTEMPTS = 4


class LiteLLMProvider(ProviderClient):
    """ProviderClient backed by litellm with retry and optional fallback."""

    def __init__(
        self,
        *,
        model: str = "",
        fallback_model: str | None = None,
        force_cost_zero: bool = False,
        **default_opts: Any,
    ) -> None:
        self.model = model
        self.fallback_model = fallback_model
        self.force_cost_zero = force_cost_zero
        self.default_opts: dict[str, Any] = default_opts

    def complete(self, messages: list[Message], model: str, **opts: Any) -> ProviderResult:
        merged = {**self.default_opts, **opts}
        merged.setdefault("timeout", _DEFAULT_TIMEOUT)
        # A factory-built provider carries the resolved litellm model string
        # (e.g. "ollama/qwen3:27b"); prefer it over the caller's raw cfg.model.
        effective_model = self.model or model
        try:
            return self._complete_with_retry(messages, effective_model, **merged)
        except Exception:
            if self.fallback_model is None:
                raise
            return self._complete_with_retry(messages, self.fallback_model, **merged)

    def _complete_with_retry(
        self, messages: list[Message], model: str, **kwargs: Any
    ) -> ProviderResult:
        @retry(
            stop=stop_after_attempt(_MAX_ATTEMPTS),
            wait=wait_exponential_jitter(initial=0.1, max=5),
            reraise=True,
        )
        def _call() -> ProviderResult:
            response = litellm.completion(model=model, messages=messages, **kwargs)
            return self._map_response(response, model)

        return _call()

    def _map_response(self, response: Any, model: str) -> ProviderResult:
        text: str = response.choices[0].message.content
        input_tokens: int = response.usage.prompt_tokens
        output_tokens: int = response.usage.completion_tokens

        if self.force_cost_zero:
            cost: float = 0.0
        else:
            try:
                cost = float(litellm.completion_cost(completion_response=response))
            except Exception:
                cost = 0.0

        return ProviderResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
