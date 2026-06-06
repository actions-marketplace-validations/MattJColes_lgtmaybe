"""Secret redaction: scrub obvious secrets from patches before they reach the provider."""

from __future__ import annotations

import re

REDACTED_PLACEHOLDER = "[REDACTED]"

# Simple patterns — replaced wholesale.
_SIMPLE_PATTERNS: list[re.Pattern[str]] = [
    # AWS access key IDs (AKIA... 20 chars)
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # OpenAI keys: sk- followed by at least 20 word chars
    re.compile(r"sk-[A-Za-z0-9\-_]{20,}"),
    # GitHub tokens: ghp_, gho_, ghs_, ghr_ followed by at least 20 word chars
    re.compile(r"gh[poshrt]_[A-Za-z0-9]{20,}"),
]

# Capturing-group patterns — only the captured value is replaced, not the key name.
_VALUE_PATTERNS: list[re.Pattern[str]] = [
    # Generic high-entropy assignments: api_key = "..." or token = "..." (value ≥ 16 chars)
    re.compile(
        r"(?i)(api[_\-]?key|api[_\-]?secret|access[_\-]?token|secret[_\-]?key|token)"
        r'\s*[=:]\s*["\']?([A-Za-z0-9\-_/+=]{16,})["\']?'
    ),
]


def _replace_value(m: re.Match[str]) -> str:
    """Replace only the secret value group (group 2), preserving the key name (group 1)."""
    full = m.group(0)
    value = m.group(2)
    return full.replace(value, REDACTED_PLACEHOLDER, 1)


def redact(text: str) -> str:
    """Return *text* with known secret patterns replaced by REDACTED_PLACEHOLDER."""
    for pattern in _SIMPLE_PATTERNS:
        text = pattern.sub(REDACTED_PLACEHOLDER, text)
    for pattern in _VALUE_PATTERNS:
        text = pattern.sub(_replace_value, text)
    return text
