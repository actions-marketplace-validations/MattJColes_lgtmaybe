"""render_findings formats findings for the local CLI (human + json)."""

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
    out = render_findings([_FINDING], "1 finding · llama3 · ~$0.00", as_json=False)

    assert "src/app.py:42" in out
    assert "[HIGH]" in out
    assert "possible NPE" in out
    assert "`user` may be None here." in out
    assert "if user is not None:" in out
    assert "1 finding · llama3 · ~$0.00" in out


def test_human_output_with_no_findings_is_just_the_summary() -> None:
    out = render_findings([], "👍 LGTM! · llama3 · ~$0.00", as_json=False)

    assert "👍 LGTM!" in out


def test_json_output_round_trips_to_findings() -> None:
    out = render_findings([_FINDING], "summary", as_json=True)

    parsed = json.loads(out)
    assert parsed == [_FINDING.model_dump(mode="json")]
