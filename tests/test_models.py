"""Contracts: round-trip serialise/deserialise + committed schema snapshots."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from lgtmaybe.core.models import (
    PRContext,
    Provider,
    ProviderResult,
    ReviewConfig,
    ReviewFinding,
    Severity,
)

SNAP_DIR = Path(__file__).parent / "snapshots"

SAMPLES: list[BaseModel] = [
    ReviewFinding(
        path="src/app.py",
        line=42,
        side="RIGHT",
        severity=Severity.high,
        title="possible NPE",
        body="`user` may be None here.",
        suggestion="if user is not None:",
    ),
    ProviderResult(text="hi", input_tokens=12, output_tokens=8),
    PRContext(
        diff="@@ -1 +1 @@\n-a\n+b\n",
        changed_files=["src/app.py"],
        base_sha="abc",
        head_sha="def",
        repo="lgtmaybe/lgtmaybe",
        pr_number=7,
    ),
    ReviewConfig(provider=Provider.bedrock, model="anthropic.claude-3-5-sonnet"),
]


@pytest.mark.parametrize("obj", SAMPLES, ids=lambda o: type(o).__name__)
def test_roundtrip(obj: BaseModel) -> None:
    restored = type(obj).model_validate_json(obj.model_dump_json())
    assert restored == obj


CONTRACT_MODELS = [ReviewFinding, ProviderResult, PRContext, ReviewConfig]


@pytest.mark.parametrize("model", CONTRACT_MODELS, ids=lambda m: m.__name__)
def test_schema_snapshot(model: type[BaseModel]) -> None:
    snap = SNAP_DIR / f"{model.__name__}.json"
    actual = json.dumps(model.model_json_schema(), indent=2, sort_keys=True)
    assert snap.exists(), f"missing committed snapshot: {snap}"
    assert actual == snap.read_text().rstrip("\n"), (
        f"schema for {model.__name__} drifted from committed snapshot"
    )


def test_severity_is_ordered() -> None:
    assert Severity.critical >= Severity.info
    assert Severity.high >= Severity.medium
    assert not (Severity.low >= Severity.high)


def test_review_config_accepts_api_base() -> None:
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3", api_base="http://localhost:11434")
    assert cfg.api_base == "http://localhost:11434"
    restored = ReviewConfig.model_validate_json(cfg.model_dump_json())
    assert restored.api_base == "http://localhost:11434"


def test_review_config_api_base_defaults_to_none() -> None:
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3")
    assert cfg.api_base is None


def test_review_config_timeout_defaults_to_60() -> None:
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3")
    assert cfg.timeout == 60


def test_review_config_accepts_timeout() -> None:
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3", timeout=600)
    assert cfg.timeout == 600


def test_review_config_temperature_defaults_to_zero() -> None:
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3")
    assert cfg.temperature == 0.0


def test_review_config_accepts_temperature() -> None:
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3", temperature=0.7)
    assert cfg.temperature == 0.7


def test_review_config_reflect_defaults_to_true() -> None:
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3")
    assert cfg.reflect is True


def test_review_config_accepts_reflect_false() -> None:
    cfg = ReviewConfig(provider=Provider.ollama, model="llama3", reflect=False)
    assert cfg.reflect is False


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValueError):
        ProviderResult.model_validate(
            {
                "text": "x",
                "input_tokens": 1,
                "output_tokens": 1,
                "bogus": True,
            }
        )
