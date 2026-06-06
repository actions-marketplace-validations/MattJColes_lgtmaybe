"""local_pr_context builds a PRContext from real git, no GitHub involved."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lgtmaybe.local import local_pr_context


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo on `main` with one base commit, plus a `feature` branch."""
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "app.py").write_text("def f():\n    return 1\n")
    _git(tmp_path, "add", "app.py")
    _git(tmp_path, "commit", "-m", "base")
    _git(tmp_path, "checkout", "-b", "feature")
    return tmp_path


def test_branch_vs_base_captures_committed_change(repo: Path) -> None:
    (repo / "app.py").write_text("def f():\n    return 2\n")
    _git(repo, "commit", "-am", "change")

    ctx = local_pr_context(base="main", working=False, cwd=repo)

    assert "+    return 2" in ctx.diff
    assert ctx.changed_files == ["app.py"]
    assert ctx.head_sha and ctx.base_sha
    assert ctx.pr_number == 0


def test_working_captures_uncommitted_change(repo: Path) -> None:
    (repo / "app.py").write_text("def f():\n    return 99\n")  # not committed

    ctx = local_pr_context(working=True, cwd=repo)

    assert "+    return 99" in ctx.diff
    assert ctx.changed_files == ["app.py"]


def test_branch_vs_base_ignores_uncommitted_when_not_working(repo: Path) -> None:
    (repo / "app.py").write_text("def f():\n    return 99\n")  # working tree only

    ctx = local_pr_context(base="main", working=False, cwd=repo)

    assert ctx.diff == ""
    assert ctx.changed_files == []


def test_repo_name_from_remote(repo: Path) -> None:
    _git(repo, "remote", "add", "origin", "git@github.com:owner/myrepo.git")
    (repo / "app.py").write_text("def f():\n    return 2\n")
    _git(repo, "commit", "-am", "change")

    ctx = local_pr_context(base="main", working=False, cwd=repo)

    assert ctx.repo == "owner/myrepo"


def test_not_a_git_repo_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="git"):
        local_pr_context(base="main", working=False, cwd=tmp_path)
