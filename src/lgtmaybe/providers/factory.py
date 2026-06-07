"""Provider factory — maps (Provider, model) → configured LiteLLMProvider.

litellm model-string conventions:
  openai     → openai/<model>
  anthropic  → anthropic/<model>
  openrouter → openrouter/<model>
  bedrock    → bedrock/<model>
  vertex     → vertex_ai/<model>
  ollama     → ollama/<model>  (+ api_base)
"""

from __future__ import annotations

from typing import Any

from lgtmaybe.core.models import Provider
from lgtmaybe.providers.constants import DEFAULT_OLLAMA_BASE
from lgtmaybe.providers.litellm_provider import LiteLLMProvider

_PREFIXES: dict[Provider, str] = {
    Provider.openai: "openai",
    Provider.anthropic: "anthropic",
    Provider.openrouter: "openrouter",
    Provider.bedrock: "bedrock",
    Provider.vertex: "vertex_ai",
    Provider.ollama: "ollama",
}


def litellm_model_string(provider: Provider, model: str) -> str:
    """Return the litellm model string for the given provider and model name."""
    return f"{_PREFIXES[provider]}/{model}"


def build_provider(
    provider: Provider,
    model: str,
    *,
    api_key: str | None = None,
    api_base: str | None = None,
    fallback_model: str | None = None,
    **extra_opts: Any,
) -> LiteLLMProvider:
    """Build a configured LiteLLMProvider for the given provider and model."""
    resolved_model = litellm_model_string(provider, model)
    resolved_fallback = litellm_model_string(provider, fallback_model) if fallback_model else None
    opts: dict[str, Any] = dict(extra_opts)

    if api_key is not None:
        opts["api_key"] = api_key

    is_ollama = provider is Provider.ollama
    if is_ollama:
        opts["api_base"] = api_base or DEFAULT_OLLAMA_BASE

    return LiteLLMProvider(
        model=resolved_model,
        fallback_model=resolved_fallback,
        force_cost_zero=is_ollama,
        **opts,
    )
