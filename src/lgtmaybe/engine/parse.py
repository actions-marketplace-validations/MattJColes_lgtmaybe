"""JSON parse + repair for LLM review output.

Tolerates:
- Markdown code fences (```json ... ```)
- Leading/trailing prose
- Trailing commas in objects/arrays
- A bare object instead of an array

Raises ParseError for unrecoverable input.
"""

from __future__ import annotations

import json
import re

from lgtmaybe.core.models import ReviewFinding


class ParseError(Exception):
    """Raised when the LLM response cannot be parsed into findings."""


# Regex to strip trailing commas before ] or }
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def _strip_fences(text: str) -> str:
    """Remove markdown code fences, keeping only the content."""
    text = re.sub(r"```(?:json)?\s*", "", text)
    return text.replace("```", "")


def _repair_trailing_commas(text: str) -> str:
    return _TRAILING_COMMA_RE.sub(r"\1", text)


def _extract_json_blob(text: str) -> str:
    """Extract the first JSON array or object from *text*."""
    # Try to find a JSON array first
    array_match = re.search(r"\[.*\]", text, re.DOTALL)
    if array_match:
        return array_match.group(0)
    # Fall back to a JSON object
    obj_match = re.search(r"\{.*\}", text, re.DOTALL)
    if obj_match:
        return obj_match.group(0)
    return text


def parse_findings(raw: str) -> list[ReviewFinding]:
    """Parse *raw* LLM text into a list of ReviewFinding objects.

    Raises:
        ParseError: if the text cannot be recovered into valid findings.
    """
    if not raw or not raw.strip():
        raise ParseError("Empty response from provider")

    text = raw.strip()
    text = _strip_fences(text)
    text = text.strip()
    text = _extract_json_blob(text)
    text = _repair_trailing_commas(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Cannot parse JSON: {exc}") from exc

    # Normalise a bare object to a single-element list
    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        raise ParseError(f"Expected JSON array, got {type(data).__name__}")

    try:
        return [ReviewFinding.model_validate(item) for item in data]
    except Exception as exc:
        raise ParseError(f"Finding validation failed: {exc}") from exc
