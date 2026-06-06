"""FakeGitHub: serves a canned PRContext, records posted reviews."""

from __future__ import annotations

from lgtmaybe.core.models import PRContext, ReviewFinding
from lgtmaybe.core.ports import GitHubGateway

_DEFAULT_CTX = PRContext(
    diff="--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-old\n+new\n",
    changed_files=["a.py"],
    base_sha="basesha",
    head_sha="headsha",
    repo="lgtmaybe/lgtmaybe",
    pr_number=1,
)


class FakeGitHub(GitHubGateway):
    """A GitHubGateway backed by in-memory state."""

    def __init__(self, ctx: PRContext | None = None) -> None:
        self._ctx = _DEFAULT_CTX if ctx is None else ctx
        self.posted: list[tuple[list[ReviewFinding], str]] = []
        self.comments: list[str] = []

    def get_pr_context(self) -> PRContext:
        return self._ctx

    def post_review(self, findings: list[ReviewFinding], summary: str) -> None:
        self.posted.append((findings, summary))

    def post_issue_comment(self, body: str) -> None:
        """In-thread reply — beyond the frozen port, used by slash commands."""
        self.comments.append(body)
