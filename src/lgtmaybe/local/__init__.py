"""Build a PRContext from the local git repo — the engine input for local mode.

This is the local counterpart to the GitHub REST gateway: instead of fetching a
PR's diff over the API, it shells out to ``git`` so a human can review their
current branch (or working tree) with no GitHub involvement at all.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from lgtmaybe.core.models import PRContext

_TIMEOUT = 30


def local_pr_context(
    *,
    base: str | None = None,
    working: bool = False,
    cwd: Path | None = None,
) -> PRContext:
    """Return a PRContext for the local repo.

    ``working`` reviews uncommitted changes (``git diff HEAD``). Otherwise the
    current branch is diffed against ``base`` (``git diff <base>...HEAD``);
    ``base`` defaults to the remote's default branch, falling back to ``main``.
    Raises ValueError when git is missing or this is not a git repository.
    """
    _ensure_repo(cwd)

    if working:
        base_ref = "HEAD"
        spec = "HEAD"
    else:
        base_ref = base or _default_base(cwd)
        spec = f"{base_ref}...HEAD"

    diff = _git(cwd, "diff", spec)
    name_output = _git(cwd, "diff", "--name-only", spec)
    changed_files = [line for line in name_output.splitlines() if line]

    # Commit names are the local stated intent — the CLI counterpart to a PR
    # title — feeding the intent lens. Uncommitted changes state no intent yet.
    commit_messages = [] if working else _commit_subjects(cwd, base_ref)

    return PRContext(
        diff=diff,
        changed_files=changed_files,
        base_sha=_git(cwd, "rev-parse", base_ref).strip(),
        head_sha=_git(cwd, "rev-parse", "HEAD").strip(),
        repo=_repo_name(cwd),
        pr_number=0,
        commit_messages=commit_messages,
    )


def _git(cwd: Path | None, *args: str) -> str:
    """Run a git command and return stdout; raise ValueError on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise ValueError("git is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"git {' '.join(args)} failed: {exc.stderr.strip()}") from exc
    return result.stdout


def _ensure_repo(cwd: Path | None) -> None:
    """Raise a clear ValueError unless cwd is inside a git work tree."""
    try:
        inside = _git(cwd, "rev-parse", "--is-inside-work-tree").strip()
    except ValueError as exc:
        raise ValueError("not a git repository (run lgtmaybe from inside one)") from exc
    if inside != "true":
        raise ValueError("not a git repository (run lgtmaybe from inside one)")


def _commit_subjects(cwd: Path | None, base_ref: str) -> list[str]:
    """Subject lines of the branch's commits (newest first), excluding *base_ref*."""
    log = _git(cwd, "log", "--format=%s", f"{base_ref}..HEAD")
    return [line for line in log.splitlines() if line.strip()]


def _default_base(cwd: Path | None) -> str:
    """The remote's default branch (e.g. origin/main), or 'main' if unknown."""
    try:
        return _git(cwd, "rev-parse", "--abbrev-ref", "origin/HEAD").strip()
    except ValueError:
        return "main"


def _repo_name(cwd: Path | None) -> str:
    """'owner/repo' from the origin remote, else the work-tree directory name."""
    try:
        url = _git(cwd, "remote", "get-url", "origin").strip()
    except ValueError:
        url = ""
    if url:
        parts = re.split(r"[:/]", url.removesuffix(".git"))
        return "/".join(parts[-2:])
    toplevel = _git(cwd, "rev-parse", "--show-toplevel").strip()
    return Path(toplevel).name
