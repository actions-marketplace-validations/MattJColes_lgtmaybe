"""Tests for prompt.py — system prompt builder."""

from __future__ import annotations

import pytest

from lgtmaybe.core.models import ReviewCategory
from lgtmaybe.engine.prompt import build_system_prompt

# A term that appears only in each category's own section, used to prove a
# focused prompt carries its section and excludes the others'.
_SIGNATURE = {
    ReviewCategory.security: "owasp",
    ReviewCategory.correctness: "off-by-one",
    ReviewCategory.deprecation: "end-of-life",
    ReviewCategory.tests: "accompanying test",
    ReviewCategory.documentation: "docstring",
    ReviewCategory.performance: "n+1",
    ReviewCategory.complexity: "cyclomatic",
}


def test_build_system_prompt_is_cached() -> None:
    """The per-category prompts are deterministic, so building one twice must
    return the identical cached object (the engine rebuilds them every batch)."""
    assert build_system_prompt(ReviewCategory.security) is build_system_prompt(
        ReviewCategory.security
    )
    assert build_system_prompt() is build_system_prompt()


def test_prompt_contains_all_severity_levels() -> None:
    prompt = build_system_prompt()
    for level in ("info", "low", "medium", "high", "critical"):
        assert level in prompt, f"severity level '{level}' missing from system prompt"


def test_prompt_contains_json_contract() -> None:
    prompt = build_system_prompt()
    # Must describe the JSON output fields
    for field in ("severity", "path", "line", "title", "body", "suggestion"):
        assert field in prompt, f"JSON field '{field}' missing from system prompt"


def test_prompt_asks_for_findings_envelope() -> None:
    """Structured output expects {"findings": [...]}, not a bare array."""
    prompt = build_system_prompt()
    assert "findings" in prompt
    assert '"findings"' in prompt
    assert '{"findings": []}' in prompt  # the empty-review shape


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


def test_prompt_asks_for_performance_review() -> None:
    """The reviewer should flag performance regressions, graded by impact."""
    prompt = build_system_prompt().lower()
    assert "performance" in prompt
    assert "n+1" in prompt  # N+1 queries / repeated calls in a loop
    assert "quadratic" in prompt


def test_prompt_asks_for_complexity_review() -> None:
    """The reviewer should flag needless complexity, restrained and low severity."""
    prompt = build_system_prompt().lower()
    assert "complexity" in prompt
    assert "cyclomatic" in prompt
    assert "nest" in prompt  # deep nesting
    assert "duplicat" in prompt  # duplicated logic to extract


# ---------------------------------------------------------------------------
# Per-category fan-out: each lens gets its own focused prompt
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", list(ReviewCategory), ids=lambda c: c.value)
def test_focused_prompt_carries_its_section_and_the_shared_contract(
    category: ReviewCategory,
) -> None:
    prompt = build_system_prompt(category).lower()
    # Its own section is present...
    assert _SIGNATURE[category] in prompt
    # ...and the shared output contract travels with every category.
    for field in ("severity", "path", "line", "title", "body", "suggestion"):
        assert field in prompt


@pytest.mark.parametrize("category", list(ReviewCategory), ids=lambda c: c.value)
def test_focused_prompt_excludes_other_categories(category: ReviewCategory) -> None:
    prompt = build_system_prompt(category).lower()
    for other, marker in _SIGNATURE.items():
        if other is not category:
            assert marker not in prompt, f"{category.value} prompt leaked {other.value} section"


def test_full_prompt_still_contains_every_category() -> None:
    """The no-arg call is the union of all sections (backward compatible)."""
    prompt = build_system_prompt().lower()
    for marker in _SIGNATURE.values():
        assert marker in prompt
