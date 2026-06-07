"""Tests for reflect.py — self-reflection / false-positive filter."""

from __future__ import annotations

import json

from lgtmaybe.core.models import (
    PRContext,
    Provider,
    ProviderResult,
    ReviewConfig,
    ReviewFinding,
    Severity,
)
from lgtmaybe.engine.reflect import reflect_findings
from tests.fakes import FakeProvider

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

_CTX = PRContext(
    diff="@@ -1,3 +1,4 @@\n context\n+new line\n context\n",
    changed_files=["a.py"],
    base_sha="abc",
    head_sha="def",
    repo="org/repo",
    pr_number=1,
)

_CFG = ReviewConfig(provider=Provider.ollama, model="llama3")

_HIGH = ReviewFinding(
    path="a.py", line=1, severity=Severity.high, title="real bug", body="definitely broken"
)
_LOW_CONF = ReviewFinding(
    path="a.py", line=2, severity=Severity.low, title="dubious", body="probably fine"
)


def _reflection_result(verdicts: dict[int, bool]) -> str:
    """Build the JSON the reflection pass returns: {index: keep_bool}."""
    return json.dumps(verdicts)


def _fake_with_verdict(verdicts: dict[int, bool]) -> FakeProvider:
    text = _reflection_result(verdicts)
    return FakeProvider(result=ProviderResult(text=text, input_tokens=5, output_tokens=5))


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_low_confidence_finding_dropped() -> None:
    # Reflection pass says: keep finding 0 (high), drop finding 1 (low-conf)
    provider = _fake_with_verdict({0: True, 1: False})

    survivors = reflect_findings([_HIGH, _LOW_CONF], _CTX, _CFG, provider)

    assert _HIGH in survivors
    assert _LOW_CONF not in survivors


def test_high_confidence_finding_survives() -> None:
    provider = _fake_with_verdict({0: True})

    survivors = reflect_findings([_HIGH], _CTX, _CFG, provider)

    assert _HIGH in survivors


def test_empty_findings_returns_empty() -> None:
    provider = FakeProvider(result=ProviderResult(text="{}", input_tokens=1, output_tokens=1))
    survivors = reflect_findings([], _CTX, _CFG, provider)
    assert survivors == []


def test_reflect_calls_provider_once() -> None:
    provider = _fake_with_verdict({0: True, 1: False})

    reflect_findings([_HIGH, _LOW_CONF], _CTX, _CFG, provider)

    assert len(provider.calls) == 1
