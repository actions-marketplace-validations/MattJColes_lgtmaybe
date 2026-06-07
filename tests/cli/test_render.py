"""render_findings formats findings for the local CLI (human, json, agent)."""

from __future__ import annotations

import json

from lgtmaybe.cli import render_findings
from lgtmaybe.core.models import ReviewFinding, Severity

_FINDING = ReviewFinding(
    path="src/app.py",
    line=42,
    severity=Severity.high,
    title="possible NPE",
    body="`user` may be None here.",
    suggestion="if user is not None:",
)


def test_human_output_shows_location_severity_and_body() -> None:
    out = render_findings([_FINDING], "1 finding · llama3 · ~$0.00", fmt="human")

    assert "src/app.py:42" in out
    assert "[HIGH]" in out
    assert "possible NPE" in out
    assert "`user` may be None here." in out
    assert "if user is not None:" in out
    assert "1 finding · llama3 · ~$0.00" in out


def test_human_output_with_no_findings_is_just_the_summary() -> None:
    out = render_findings([], "👍 LGTM! · llama3 · ~$0.00", fmt="human")

    assert "👍 LGTM!" in out


def test_json_output_round_trips_to_findings() -> None:
    out = render_findings([_FINDING], "summary", fmt="json")

    parsed = json.loads(out)
    assert parsed == [_FINDING.model_dump(mode="json")]


def test_agent_output_is_directive_and_carries_the_fix() -> None:
    out = render_findings([_FINDING], "1 finding · llama3", fmt="agent")

    assert "apply" in out.lower()  # tells the AI to act, not just observe
    assert "src/app.py:42" in out
    assert "possible NPE" in out
    assert "`user` may be None here." in out
    assert "if user is not None:" in out


def test_agent_output_with_no_findings_says_nothing_to_correct() -> None:
    out = render_findings([], "👍 LGTM! · llama3", fmt="agent")

    assert "nothing to correct" in out.lower()
