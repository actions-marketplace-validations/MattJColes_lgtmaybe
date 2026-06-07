"""RestGitHubGateway: talks to the GitHub REST API.

Implements GitHubGateway with:
- get_pr_context(): fetches diff + paginated file list + base/head SHAs.
- post_review(): batches inline comments + summary; idempotent via a marker comment.

The httpx.Client is injected so tests can use respx without monkey-patching.
All network calls carry an explicit timeout.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from lgtmaybe.core.models import PRContext, ReviewFinding
from lgtmaybe.core.ports import GitHubGateway

from .diff import PositionMap, build_position_map, is_reviewable

_TIMEOUT = httpx.Timeout(30.0)
_MARKER = "<!-- lgtmaybe -->"

# Link header rel="next" parser
_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


class RestGitHubGateway(GitHubGateway):
    """GitHub REST adapter.

    Args:
        repo:      Full repo name, e.g. "owner/repo".
        pr_number: Pull-request number.
        token:     GitHub personal access token or GITHUB_TOKEN.
        client:    Injected httpx.Client; a default is created if omitted.
    """

    def __init__(
        self,
        repo: str,
        pr_number: int,
        token: str,
        client: httpx.Client | None = None,
        marker_key: str | None = None,
    ) -> None:
        self._repo = repo
        self._pr_number = pr_number
        self._headers = {
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._client = client if client is not None else httpx.Client(timeout=_TIMEOUT)
        # Scope the idempotency marker to a provider/model so concurrent reviews
        # from different backends on one PR update their own comment instead of
        # clobbering each other. Unkeyed gateways keep the legacy marker.
        self._marker = f"<!-- lgtmaybe:{marker_key} -->" if marker_key else _MARKER

    # ------------------------------------------------------------------
    # GitHubGateway implementation
    # ------------------------------------------------------------------

    def get_pr_context(self) -> PRContext:
        """Fetch PR metadata, unified diff, and the full paginated files list."""
        pr_url = f"https://api.github.com/repos/{self._repo}/pulls/{self._pr_number}"

        # Fetch metadata (base/head SHAs)
        meta = self._get_json(pr_url)
        base_sha: str = meta["base"]["sha"]
        head_sha: str = meta["head"]["sha"]

        # Fetch unified diff
        diff_headers = {**self._headers, "Accept": "application/vnd.github.v3.diff"}
        resp = self._client.get(pr_url, headers=diff_headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        diff: str = resp.text

        # Fetch paginated files list
        files_url = (
            f"https://api.github.com/repos/{self._repo}/pulls/{self._pr_number}/files?per_page=100"
        )
        changed_files = self._fetch_all_files(files_url)

        # Fetch head-revision text of reviewable files so the engine can pad hunks
        # with surrounding context. Read-only API fetch — never a checkout — and
        # the engine redacts it before it leaves the process.
        file_contents: dict[str, str] = {}
        for path in changed_files:
            if not is_reviewable(path):
                continue
            content = self._get_file_content(path, head_sha)
            if content is not None:
                file_contents[path] = content

        return PRContext(
            diff=diff,
            changed_files=changed_files,
            base_sha=base_sha,
            head_sha=head_sha,
            repo=self._repo,
            pr_number=self._pr_number,
            file_contents=file_contents,
        )

    def post_review(
        self,
        findings: list[ReviewFinding],
        summary: str,
        diff: str | None = None,
    ) -> None:
        """Post (or update) a single review with batched inline comments.

        If a previous review from this tool exists (identified by ``_MARKER`` in
        the body), it is updated in-place rather than creating a duplicate.

        The ``diff`` parameter is optional; when omitted the method fetches the
        PR diff to build the position map.
        """
        if diff is None:
            ctx = self.get_pr_context()
            diff = ctx.diff

        pos_map: PositionMap = build_position_map(diff)
        comments = self._build_comments(findings, pos_map)

        body = f"{summary}\n\n{self._marker}"
        existing_id = self._find_existing_review()

        reviews_url = f"https://api.github.com/repos/{self._repo}/pulls/{self._pr_number}/reviews"

        if existing_id is not None:
            # Update the existing review body (inline comments cannot be changed
            # through this endpoint, but the summary is updated).
            update_url = f"{reviews_url}/{existing_id}"
            resp = self._client.put(
                update_url,
                headers={**self._headers, "Accept": "application/vnd.github+json"},
                json={"body": body},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
        else:
            payload: dict[str, Any] = {
                "body": body,
                "event": "COMMENT",
                "comments": comments,
            }
            resp = self._client.post(
                reviews_url,
                headers={**self._headers, "Accept": "application/vnd.github+json"},
                json=payload,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()

    def post_issue_comment(self, body: str) -> None:
        """Post a standalone comment to the PR conversation (in-thread reply).

        Used by slash commands (/ask, /describe). Beyond the frozen GitHubGateway
        port, which only models reviews.
        """
        url = f"https://api.github.com/repos/{self._repo}/issues/{self._pr_number}/comments"
        resp = self._client.post(
            url,
            headers={**self._headers, "Accept": "application/vnd.github+json"},
            json={"body": body},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_json(self, url: str) -> Any:
        resp = self._client.get(
            url,
            headers={**self._headers, "Accept": "application/vnd.github+json"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _get_file_content(self, path: str, ref: str) -> str | None:
        """Return the raw text of *path* at *ref*, or None if it can't be fetched.

        Deleted/renamed-away files (404) and any other fetch error degrade to
        None so the engine simply reviews the bare diff for that file.
        """
        url = f"https://api.github.com/repos/{self._repo}/contents/{path}?ref={ref}"
        try:
            resp = self._client.get(
                url,
                headers={**self._headers, "Accept": "application/vnd.github.v3.raw"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            return None
        return resp.text

    def _fetch_all_files(self, first_url: str) -> list[str]:
        """Follow Link rel=next pagination and collect all filenames."""
        files: list[str] = []
        url: str | None = first_url
        while url is not None:
            resp = self._client.get(
                url,
                headers={**self._headers, "Accept": "application/vnd.github+json"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            for item in resp.json():
                files.append(item["filename"])
            url = self._next_link(resp)
        return files

    @staticmethod
    def _next_link(resp: httpx.Response) -> str | None:
        link = resp.headers.get("Link", "")
        m = _LINK_NEXT.search(link)
        return m.group(1) if m else None

    def _find_existing_review(self) -> int | None:
        """Return the ID of the first review whose body contains the marker, or None."""
        reviews_url = f"https://api.github.com/repos/{self._repo}/pulls/{self._pr_number}/reviews"
        reviews = self._get_json(reviews_url)
        for review in reviews:
            body: str = review.get("body", "") or ""
            if self._marker in body:
                review_id: int = review["id"]
                return review_id
        return None

    @staticmethod
    def _build_comments(
        findings: list[ReviewFinding],
        pos_map: PositionMap,
    ) -> list[dict[str, Any]]:
        """Map findings to GitHub review comment dicts, skipping unmapped lines."""
        comments: list[dict[str, Any]] = []
        for f in findings:
            position = pos_map.get((f.path, f.line))
            if position is None:
                continue
            comment: dict[str, Any] = {
                "path": f.path,
                "position": position,
                "body": f"**[{f.severity.upper()}] {f.title}**\n\n{f.body}",
            }
            if f.suggestion is not None:
                comment["body"] += f"\n\n```suggestion\n{f.suggestion}\n```"
            comments.append(comment)
        return comments
