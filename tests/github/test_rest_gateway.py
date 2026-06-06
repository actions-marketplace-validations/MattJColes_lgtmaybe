"""Tests for RestGitHubGateway.get_pr_context — respx-mocked GitHub REST API."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from lgtmaybe.github import RestGitHubGateway

FIXTURES = Path(__file__).parent / "fixtures"

REPO = "owner/repo"
PR_NUMBER = 42
TOKEN = "ghp_test"

BASE_URL = "https://api.github.com"
PR_URL = f"{BASE_URL}/repos/{REPO}/pulls/{PR_NUMBER}"
FILES_URL = f"{BASE_URL}/repos/{REPO}/pulls/{PR_NUMBER}/files"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


def _load_json(name: str) -> object:
    return json.loads(_load(name))


@respx.mock
def test_get_pr_context_returns_expected_shas_and_diff() -> None:
    """get_pr_context fetches the PR diff and extracts base/head SHAs."""
    # Route matching is first-match; register the more-specific diff route first.
    respx.route(
        method="GET",
        url=PR_URL,
        headers={"Accept": "application/vnd.github.v3.diff"},
    ).mock(return_value=httpx.Response(200, content=_load("pr_diff.patch").encode()))
    respx.route(
        method="GET",
        url=PR_URL,
    ).mock(return_value=httpx.Response(200, json=_load_json("pr_detail.json")))
    respx.route(
        method="GET",
        url__startswith=FILES_URL,
    ).mock(return_value=httpx.Response(200, json=_load_json("pr_files_page1.json")))

    client = httpx.Client()
    gw = RestGitHubGateway(repo=REPO, pr_number=PR_NUMBER, token=TOKEN, client=client)
    ctx = gw.get_pr_context()

    assert ctx.base_sha == "abc1234base"
    assert ctx.head_sha == "def5678head"
    assert ctx.repo == REPO
    assert ctx.pr_number == PR_NUMBER
    assert "src/app.py" in ctx.diff


@respx.mock
def test_get_pr_context_paginates_files_list() -> None:
    """get_pr_context follows Link rel=next to retrieve all files across pages."""
    page1_url = f"{FILES_URL}?per_page=100"
    page2_url = f"{FILES_URL}?per_page=100&page=2"

    link_header = f'<{page2_url}>; rel="next", <{page2_url}>; rel="last"'

    respx.route(
        method="GET",
        url=PR_URL,
        headers={"Accept": "application/vnd.github.v3.diff"},
    ).mock(return_value=httpx.Response(200, content=_load("pr_diff.patch").encode()))
    respx.route(
        method="GET",
        url=PR_URL,
    ).mock(return_value=httpx.Response(200, json=_load_json("pr_detail.json")))
    respx.route(method="GET", url=page1_url).mock(
        return_value=httpx.Response(
            200,
            json=_load_json("pr_files_page1.json"),
            headers={"Link": link_header},
        )
    )
    respx.route(method="GET", url=page2_url).mock(
        return_value=httpx.Response(200, json=_load_json("pr_files_page2.json"))
    )

    client = httpx.Client()
    gw = RestGitHubGateway(repo=REPO, pr_number=PR_NUMBER, token=TOKEN, client=client)
    ctx = gw.get_pr_context()

    # Page 1 files
    assert "src/app.py" in ctx.changed_files
    assert "package-lock.json" in ctx.changed_files
    # Page 2 files
    assert "src/models.py" in ctx.changed_files
    assert "yarn.lock" in ctx.changed_files
