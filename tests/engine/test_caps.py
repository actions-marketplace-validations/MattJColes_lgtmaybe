"""Guards in the engine: cost cap, file cap, and generated-file skipping."""

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
from lgtmaybe.core.ports import Message
from lgtmaybe.engine import LLMReviewEngine
from tests.fakes import FakeProvider


def _diff_for(paths: list[str]) -> str:
    """Build a minimal multi-file unified diff adding one line to each path."""
    chunks = []
    for p in paths:
        chunks.append(
            f"diff --git a/{p} b/{p}\n"
            f"index 0000001..0000002 100644\n"
            f"--- a/{p}\n"
            f"+++ b/{p}\n"
            f"@@ -1,1 +1,2 @@\n"
            f" first\n"
            f"+added line in {p}\n"
        )
    return "".join(chunks)


def _ctx(paths: list[str]) -> PRContext:
    return PRContext(
        diff=_diff_for(paths),
        changed_files=paths,
        base_sha="abc",
        head_sha="def",
        repo="org/repo",
        pr_number=1,
    )


class _Provider(FakeProvider):
    """Returns the given findings (as JSON) on call 1, keep-all reflection after."""

    def __init__(self, findings: list[ReviewFinding], cost: float) -> None:
        super().__init__()
        self._payload = json.dumps([f.model_dump(mode="json") for f in findings])
        self._cost = cost
        self._verdict = json.dumps({i: True for i in range(len(findings))})
        self._n = 0

    def complete(self, messages: list[Message], model: str, **opts: object) -> ProviderResult:
        self.calls.append({"messages": messages, "model": model, "opts": opts})
        self._n += 1
        if self._n == 1:
            return ProviderResult(
                text=self._payload, input_tokens=10, output_tokens=20, cost_usd=self._cost
            )
        return ProviderResult(text=self._verdict, input_tokens=5, output_tokens=5, cost_usd=0.0)


_A_FINDING = ReviewFinding(path="a.py", line=1, severity=Severity.high, title="bug", body="broken")


def test_cost_cap_aborts_with_notice_and_no_findings() -> None:
    provider = _Provider([_A_FINDING], cost=0.0123)
    engine = LLMReviewEngine(provider)
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3", max_cost_usd=0.005)

    findings, summary = engine.review(_ctx(["a.py"]), cfg)

    assert findings == []
    assert "cost" in summary.lower()
    assert "0.005" in summary  # the cap
    assert "abort" in summary.lower() or "exceed" in summary.lower()


def test_under_cost_cap_returns_findings_normally() -> None:
    provider = _Provider([_A_FINDING], cost=0.0001)
    engine = LLMReviewEngine(provider)
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3", max_cost_usd=1.0)

    findings, summary = engine.review(_ctx(["a.py"]), cfg)

    assert len(findings) == 1
    assert "abort" not in summary.lower()


def test_file_cap_reviews_top_n_with_notice() -> None:
    provider = _Provider([_A_FINDING], cost=0.0001)
    engine = LLMReviewEngine(provider)
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3", max_files=2)

    findings, summary = engine.review(_ctx(["f1.py", "f2.py", "f3.py"]), cfg)

    assert "2" in summary and "3" in summary
    assert "file" in summary.lower()
    # Only the first two files' patches reached the provider.
    sent = " ".join(msg.get("content", "") for call in provider.calls for msg in call["messages"])
    assert "added line in f1.py" in sent
    assert "added line in f2.py" in sent
    assert "added line in f3.py" not in sent


def test_generated_and_lockfiles_are_skipped() -> None:
    provider = _Provider([_A_FINDING], cost=0.0001)
    engine = LLMReviewEngine(provider)
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3")

    engine.review(_ctx(["package-lock.json", "src/app.py"]), cfg)

    sent = " ".join(msg.get("content", "") for call in provider.calls for msg in call["messages"])
    assert "added line in src/app.py" in sent
    assert "added line in package-lock.json" not in sent
