"""Tests for parse.py — JSON parse + repair."""

from __future__ import annotations

import pytest

from lgtmaybe.core.models import ReviewFinding, Severity
from lgtmaybe.engine.parse import ParseError, parse_findings

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_VALID_FINDING = {
    "path": "src/app.py",
    "line": 10,
    "side": "RIGHT",
    "severity": "high",
    "title": "null deref",
    "body": "may be None",
    "suggestion": None,
}


def _json_findings(findings: list[dict]) -> str:  # type: ignore[type-arg]
    import json

    return json.dumps(findings)


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------


def test_plain_json_array_parses() -> None:
    raw = _json_findings([_VALID_FINDING])
    result = parse_findings(raw)
    assert len(result) == 1
    assert isinstance(result[0], ReviewFinding)
    assert result[0].severity == Severity.high


def test_markdown_fence_stripped() -> None:
    raw = "```json\n" + _json_findings([_VALID_FINDING]) + "\n```"
    result = parse_findings(raw)
    assert len(result) == 1


def test_prose_wrapped_json_extracted() -> None:
    raw = "Here are my findings:\n\n" + _json_findings([_VALID_FINDING]) + "\n\nHope that helps!"
    result = parse_findings(raw)
    assert len(result) == 1


def test_trailing_comma_tolerated() -> None:
    raw = '[{"path":"a.py","line":1,"severity":"low","title":"t","body":"b","suggestion":null,}]'
    result = parse_findings(raw)
    assert len(result) == 1


def test_multiple_findings_parse() -> None:
    finding2 = dict(_VALID_FINDING, line=20, severity="medium", title="other")
    raw = _json_findings([_VALID_FINDING, finding2])
    result = parse_findings(raw)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# malformed-but-recoverable
# ---------------------------------------------------------------------------


def test_single_object_wrapped_in_list() -> None:
    """Model returns a bare object instead of an array."""
    import json

    raw = json.dumps(_VALID_FINDING)
    result = parse_findings(raw)
    assert len(result) == 1


def test_extra_whitespace_and_newlines() -> None:
    raw = "\n\n  " + _json_findings([_VALID_FINDING]) + "  \n\n"
    result = parse_findings(raw)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# unrecoverable
# ---------------------------------------------------------------------------


def test_pure_garbage_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        parse_findings("this is not json at all, just prose, no brackets")


def test_empty_string_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        parse_findings("")


def test_whitespace_only_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        parse_findings("   \n\t  ")


# ---------------------------------------------------------------------------
# schema enforcement — the model output is untrusted; reject drift loudly
# ---------------------------------------------------------------------------


def test_empty_array_yields_no_findings() -> None:
    """A clean review (empty array) is valid and parses to zero findings."""
    assert parse_findings("[]") == []


def test_unknown_field_is_rejected() -> None:
    """`extra=forbid` on the model means injected/extra keys fail, not slip through."""
    bad = dict(_VALID_FINDING, exploit="rm -rf /")
    with pytest.raises(ParseError):
        parse_findings(_json_findings([bad]))


def test_invalid_severity_is_rejected() -> None:
    bad = dict(_VALID_FINDING, severity="catastrophic")
    with pytest.raises(ParseError):
        parse_findings(_json_findings([bad]))


def test_missing_required_field_is_rejected() -> None:
    bad = {k: v for k, v in _VALID_FINDING.items() if k != "body"}
    with pytest.raises(ParseError):
        parse_findings(_json_findings([bad]))


def test_non_integer_line_is_rejected() -> None:
    bad = dict(_VALID_FINDING, line="not-a-number")
    with pytest.raises(ParseError):
        parse_findings(_json_findings([bad]))


def test_json_null_literal_raises_parse_error() -> None:
    """A literal `null` is neither an array nor an object of findings."""
    with pytest.raises(ParseError):
        parse_findings("null")
