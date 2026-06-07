"""Shared provider defaults."""

from __future__ import annotations

# Default ollama endpoint when none is supplied. Used by both the credential
# resolver (to fill AuthConfig.api_base) and the factory (to configure the
# litellm client) so the two never drift.
DEFAULT_OLLAMA_BASE = "http://localhost:11434"
