"""Frozen data contracts.

These pydantic models are the wire format between every track. They are frozen
in the foundation step: change them only by consensus, never to suit one track.
`extra="forbid"` makes typos and drift fail loudly instead of silently.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Side of the diff a comment attaches to, matching the GitHub review API.
Side = Literal["LEFT", "RIGHT"]


class Severity(StrEnum):
    """Finding severity, ordered low → high for `min_severity` filtering."""

    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

    @property
    def rank(self) -> int:
        return _SEVERITY_ORDER.index(self)

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Severity):
            return self.rank >= other.rank
        return NotImplemented


_SEVERITY_ORDER: list[Severity] = [
    Severity.info,
    Severity.low,
    Severity.medium,
    Severity.high,
    Severity.critical,
]


class Provider(StrEnum):
    """The backend selected by the `--provider` flag."""

    openai = "openai"
    openrouter = "openrouter"
    anthropic = "anthropic"
    bedrock = "bedrock"
    vertex = "vertex"
    ollama = "ollama"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewFinding(_Strict):
    """A single inline review comment the model wants to post."""

    path: str
    line: int
    side: Side = "RIGHT"
    severity: Severity
    title: str
    body: str
    suggestion: str | None = None


class ProviderResult(_Strict):
    """The normalised return of one LLM completion, with usage + cost."""

    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class PRContext(_Strict):
    """Everything the engine needs about a PR — fetched via API, never checkout."""

    diff: str
    changed_files: list[str]
    base_sha: str
    head_sha: str
    repo: str
    pr_number: int


class ReviewConfig(_Strict):
    """How to run one review: provider/model, severity floor, filters, caps."""

    provider: Provider
    model: str
    api_base: str | None = None
    min_severity: Severity = Severity.info
    include_paths: list[str] = Field(default_factory=list)
    exclude_paths: list[str] = Field(default_factory=list)
    max_files: int = 50
    max_input_tokens: int = 100_000
    max_cost_usd: float = 1.0
