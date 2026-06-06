"""Boundary interfaces (ports).

Hexagonal architecture: these abstract base classes are the seams between the
core and the outside world. Adapters (litellm, github) implement them; the
engine depends only on these types. Frozen in the foundation step so the
parallel tracks can build against stable signatures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import PRContext, ProviderResult, ReviewConfig, ReviewFinding

# A chat message in the provider-neutral shape litellm expects.
Message = dict[str, str]


class ProviderClient(ABC):
    """Port: an LLM backend that returns a normalised completion."""

    @abstractmethod
    def complete(self, messages: list[Message], model: str, **opts: Any) -> ProviderResult:
        """Run one completion and return text + usage + cost."""
        raise NotImplementedError


class GitHubGateway(ABC):
    """Port: read a PR's context and post a review back."""

    @abstractmethod
    def get_pr_context(self) -> PRContext:
        """Fetch the PR diff and metadata via API (never check out PR code)."""
        raise NotImplementedError

    @abstractmethod
    def post_review(self, findings: list[ReviewFinding], summary: str) -> None:
        """Post batched inline comments + one summary, idempotently."""
        raise NotImplementedError


class ReviewEngine(ABC):
    """Port: turn a PR context + config into findings and a summary."""

    @abstractmethod
    def review(self, ctx: PRContext, cfg: ReviewConfig) -> tuple[list[ReviewFinding], str]:
        """Produce (findings, summary) for the given PR and config."""
        raise NotImplementedError
