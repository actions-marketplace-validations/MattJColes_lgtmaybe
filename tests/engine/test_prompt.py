"""Tests for prompt.py — system prompt builder."""

from __future__ import annotations

from lgtmaybe.engine.prompt import build_system_prompt


def test_prompt_contains_all_severity_levels() -> None:
    prompt = build_system_prompt()
    for level in ("info", "low", "medium", "high", "critical"):
        assert level in prompt, f"severity level '{level}' missing from system prompt"


def test_prompt_contains_json_contract() -> None:
    prompt = build_system_prompt()
    # Must describe the JSON output fields
    for field in ("severity", "path", "line", "title", "body", "suggestion"):
        assert field in prompt, f"JSON field '{field}' missing from system prompt"


def test_prompt_instructs_changed_lines_only() -> None:
    prompt = build_system_prompt()
    # Must instruct model to comment only on changed lines
    assert "changed" in prompt.lower()


def test_prompt_is_nonempty_string() -> None:
    prompt = build_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 200
