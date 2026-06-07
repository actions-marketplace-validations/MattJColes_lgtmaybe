"""Runner wiring test — fixture load → engine → score, with a fake provider."""

from __future__ import annotations

import json

import pytest

from evals import run as run_mod
from lgtmaybe.core.models import ProviderResult, ReviewFinding, Severity
from tests.fakes import FakeProvider


class _ShellInjectionProvider(FakeProvider):
    """Returns the badcode shell-injection finding for every review call."""

    def complete(self, messages, model, **opts):  # type: ignore[override]
        self.calls.append({"messages": messages, "model": model, "opts": opts})
        finding = ReviewFinding(
            path="badcode.py",
            line=30,
            severity=Severity.high,
            title="Command injection via shell=True",
            body="report_name is concatenated into a shell command.",
        )
        return ProviderResult(
            text=json.dumps({"findings": [finding.model_dump(mode="json")]}),
            input_tokens=1,
            output_tokens=1,
        )


def test_runner_loads_fixtures_and_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_mod, "build_provider", lambda *a, **k: _ShellInjectionProvider())
    # The provider catches 1 of the 5 planted issues — passes a low bar, fails a high one.
    assert run_mod.main(["--provider", "ollama", "--model", "x", "--min-recall", "0.0"]) == 0
    assert run_mod.main(["--provider", "ollama", "--model", "x", "--min-recall", "0.9"]) == 1


def test_runner_fails_when_review_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Unparseable(FakeProvider):
        def complete(self, messages, model, **opts):  # type: ignore[override]
            self.calls.append({"messages": messages, "model": model, "opts": opts})
            return ProviderResult(text="I cannot help with that.", input_tokens=1, output_tokens=1)

    monkeypatch.setattr(run_mod, "build_provider", lambda *a, **k: _Unparseable())
    assert run_mod.main(["--provider", "ollama", "--model", "x", "--min-recall", "0.0"]) == 1
