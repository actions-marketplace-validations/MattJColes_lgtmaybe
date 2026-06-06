"""Tests for RestGitHubGateway.post_review — idempotency and batching."""

from __future__ import annotations

import json

import httpx
import respx

from lgtmaybe.core.models import ReviewFinding, Severity
from lgtmaybe.github import RestGitHubGateway

REPO = "owner/repo"
PR_NUMBER = 42
TOKEN = "ghp_test"

BASE_URL = "https://api.github.com"
PR_URL = f"{BASE_URL}/repos/{REPO}/pulls/{PR_NUMBER}"
REVIEWS_URL = f"{BASE_URL}/repos/{REPO}/pulls/{PR_NUMBER}/reviews"
COMMENTS_URL = f"{BASE_URL}/repos/{REPO}/issues/{PR_NUMBER}/comments"

MARKER = "<!-- lgtmaybe -->"

# A minimal diff that puts src/app.py line 2 at diff position 2.
SAMPLE_DIFF = """\
diff --git a/src/app.py b/src/app.py
index 0000001..0000002 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,4 +1,6 @@
 import os
+import sys

 def main():
-    pass
+    print("hello")
+    return 0
"""

FINDINGS = [
    ReviewFinding(
        path="src/app.py",
        line=2,
        side="RIGHT",
        severity=Severity.medium,
        title="Import order",
        body="sys should be before os",
        suggestion=None,
    )
]


def _pr_detail() -> dict[object, object]:
    return {"number": PR_NUMBER, "base": {"sha": "abc"}, "head": {"sha": "def"}}


@respx.mock
def test_post_review_creates_review_with_marker_and_batched_comments() -> None:
    """First post_review call creates one review containing the marker."""
    # No existing reviews
    respx.route(method="GET", url=REVIEWS_URL).mock(return_value=httpx.Response(200, json=[]))
    created_bodies: list[dict[object, object]] = []

    def capture_create(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        created_bodies.append(body)
        return httpx.Response(201, json={"id": 1, "body": body.get("body", "")})

    respx.route(method="POST", url=REVIEWS_URL).mock(side_effect=capture_create)

    client = httpx.Client()
    gw = RestGitHubGateway(repo=REPO, pr_number=PR_NUMBER, token=TOKEN, client=client)
    gw.post_review(FINDINGS, "Summary text", diff=SAMPLE_DIFF)

    assert len(created_bodies) == 1
    review_body = created_bodies[0]
    assert MARKER in str(review_body.get("body", ""))
    assert review_body.get("event") == "COMMENT"
    comments = review_body.get("comments", [])
    assert len(comments) == 1
    assert comments[0]["path"] == "src/app.py"
    assert comments[0]["position"] == 2


@respx.mock
def test_post_review_updates_existing_review_on_second_call() -> None:
    """Second post_review call updates the existing review rather than creating another."""
    existing_review_id = 99
    existing_reviews = [{"id": existing_review_id, "body": f"Old summary {MARKER}"}]
    respx.route(method="GET", url=REVIEWS_URL).mock(
        return_value=httpx.Response(200, json=existing_reviews)
    )

    update_url = f"{REVIEWS_URL}/{existing_review_id}"
    updated_bodies: list[dict[object, object]] = []

    def capture_update(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        updated_bodies.append(body)
        return httpx.Response(200, json={"id": existing_review_id, "body": body.get("body", "")})

    create_calls: list[httpx.Request] = []

    def capture_create(request: httpx.Request) -> httpx.Response:
        create_calls.append(request)
        return httpx.Response(201, json={"id": 100})

    respx.route(method="PUT", url=update_url).mock(side_effect=capture_update)
    respx.route(method="POST", url=REVIEWS_URL).mock(side_effect=capture_create)

    client = httpx.Client()
    gw = RestGitHubGateway(repo=REPO, pr_number=PR_NUMBER, token=TOKEN, client=client)
    gw.post_review(FINDINGS, "New summary", diff=SAMPLE_DIFF)

    # Must have updated, not created
    assert len(create_calls) == 0, "Should not POST a new review when one already exists"
    assert len(updated_bodies) == 1
    assert MARKER in str(updated_bodies[0].get("body", ""))


@respx.mock
def test_post_review_skips_findings_outside_diff() -> None:
    """Findings whose line has no diff position are omitted from the review comments."""
    respx.route(method="GET", url=REVIEWS_URL).mock(return_value=httpx.Response(200, json=[]))

    out_of_diff_findings = [
        ReviewFinding(
            path="src/app.py",
            line=999,  # not in the diff
            side="RIGHT",
            severity=Severity.high,
            title="Not in diff",
            body="This line is not in the diff",
            suggestion=None,
        )
    ]

    created_bodies: list[dict[object, object]] = []

    def capture_create(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        created_bodies.append(body)
        return httpx.Response(201, json={"id": 1})

    respx.route(method="POST", url=REVIEWS_URL).mock(side_effect=capture_create)

    client = httpx.Client()
    gw = RestGitHubGateway(repo=REPO, pr_number=PR_NUMBER, token=TOKEN, client=client)
    gw.post_review(out_of_diff_findings, "Summary", diff=SAMPLE_DIFF)

    assert len(created_bodies) == 1
    assert created_bodies[0].get("comments", []) == []
