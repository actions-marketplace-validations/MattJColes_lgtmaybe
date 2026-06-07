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


# ---------------------------------------------------------------------------
# Security-review coverage (the reviewer should actually hunt for vulns)
# ---------------------------------------------------------------------------


def test_prompt_directs_a_security_review() -> None:
    prompt = build_system_prompt().lower()
    assert "security" in prompt
    assert "owasp" in prompt


def test_prompt_names_common_vulnerability_classes() -> None:
    """The prompt should cue the model on the major OWASP-style vuln classes."""
    prompt = build_system_prompt().lower()
    expected = [
        "injection",
        "xss",  # cross-site scripting
        "secret",
        "auth",  # authn/authz
        "traversal",
        "ssrf",
        "deserialization",
        "crypto",
    ]
    missing = [term for term in expected if term not in prompt]
    assert not missing, f"security cues missing from prompt: {missing}"


def test_prompt_reaffirms_diff_is_untrusted_data() -> None:
    """Defence-in-depth: the system prompt itself restates the injection guard."""
    prompt = build_system_prompt().lower()
    assert "data" in prompt and ("untrusted" in prompt or "never follow" in prompt)


def test_prompt_asks_for_deprecated_and_eol_review() -> None:
    """The reviewer should flag deprecated APIs and end-of-life dependencies."""
    prompt = build_system_prompt().lower()
    assert "deprecat" in prompt  # deprecated / deprecation
    assert "end-of-life" in prompt or "end of life" in prompt
    assert "dependenc" in prompt  # dependency / dependencies


def test_prompt_asks_for_logic_and_edge_case_review() -> None:
    """The reviewer should hunt correctness/logic bugs, not just security."""
    prompt = build_system_prompt().lower()
    assert "correctness" in prompt
    assert "off-by-one" in prompt
    assert "boundary" in prompt
    assert "dereference" in prompt  # null/None dereferences


def test_prompt_asks_for_test_coverage() -> None:
    """Changed code paths shipped without a test should be flagged."""
    prompt = build_system_prompt().lower()
    assert "coverage" in prompt
    assert "accompanying test" in prompt
    assert "suggestion" in prompt  # a runnable test goes in the suggestion field


def test_prompt_asks_for_documentation_review() -> None:
    """Public surfaces added without docs should be flagged, restrained to public APIs."""
    prompt = build_system_prompt().lower()
    assert "documentation" in prompt
    assert "docstring" in prompt
    assert "public" in prompt


def test_prompt_names_pii_and_secrets_in_logs() -> None:
    """Sensitive-data exposure should name concrete PII/secret leaks into logs."""
    prompt = build_system_prompt().lower()
    assert "log" in prompt
    assert "pii" in prompt
    assert "ssn" in prompt  # SSNs
    assert "password" in prompt
