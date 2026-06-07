"""JSON parse + repair for LLM review output.

Tolerates:
- The ``{"findings": [...]}`` structured-output envelope and a bare array alike
- ``<think>...</think>`` reasoning blocks (qwen-style models) before the JSON
- Markdown code fences (```json ... ```)
- Leading/trailing prose
- Trailing commas in objects/arrays
- A bare object instead of an array

Raises ParseError for unrecoverable input.
"""

from __future__ import annotations

import json
import re
from typing import Any

from lgtmaybe.core.models import ReviewFinding


class ParseError(Exception):
    """Raised when the LLM response cannot be parsed into findings."""


# Regex to strip trailing commas before ] or }
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")

# Reasoning blocks emitted by "thinking" models (qwen3.x etc.) — stripped before
# we look for JSON so their contents can't be mistaken for the answer.
_THINK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.DOTALL | re.IGNORECASE)


def strip_fences(text: str) -> str:
    """Remove markdown code fences, keeping only the content."""
    text = re.sub(r"```(?:json)?\s*", "", text)
    return text.replace("```", "")


def _strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> reasoning blocks."""
    return _THINK_RE.sub("", text)


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


def _loads_lenient(text: str) -> Any:
    """Parse JSON from *text*: try it whole, then the first embedded JSON blob."""
    for candidate in (text, _extract_json_blob(text)):
        try:
            return json.loads(_repair_trailing_commas(candidate))
        except json.JSONDecodeError:
            continue
    raise ParseError("Cannot parse JSON from response")


def _unwrap(data: Any) -> Any:
    """Turn the ``{"findings": [...]}`` envelope or a bare object into a list."""
    if isinstance(data, dict):
        findings = data.get("findings")
        if isinstance(findings, list):
            return findings
        return [data]  # a bare single finding object
    return data


def parse_findings(raw: str) -> list[ReviewFinding]:
    """Parse *raw* LLM text into a list of ReviewFinding objects.

    Accepts the ``{"findings": [...]}`` structured-output envelope or a bare
    array, with reasoning blocks, fences, prose, and trailing commas tolerated.

    Raises:
        ParseError: if the text cannot be recovered into valid findings.
    """
    if not raw or not raw.strip():
        raise ParseError("Empty response from provider")

    text = _strip_think_blocks(raw).strip()
    text = strip_fences(text).strip()

    data = _unwrap(_loads_lenient(text))

    if not isinstance(data, list):
        raise ParseError(f"Expected JSON array or {{'findings': [...]}}, got {type(data).__name__}")

    try:
        return [ReviewFinding.model_validate(item) for item in data]
    except Exception as exc:
        raise ParseError(f"Finding validation failed: {exc}") from exc
