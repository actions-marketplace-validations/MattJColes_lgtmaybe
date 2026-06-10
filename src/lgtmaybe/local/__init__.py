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
    """Return a PRContext for the local repo, compared against the remote primary branch.

    Both modes resolve the same base — the remote's default branch
    (``origin/HEAD``, else the first of ``origin/main``/``origin/master``/
    ``main``/``master`` that exists), overridable with ``base``:

    - default: the branch's committed changes (``git diff <base>...HEAD``).
    - ``working``: the whole worktree — branch commits **plus** uncommitted
      edits — diffed against the merge-base with ``base``, so commits that only
      exist on the remote don't show up as reversed changes.

    Commit subjects between the base and HEAD are collected in both modes (the
    stated intent for the intent lens). Raises ValueError when git is missing or
    this is not a git repository.
    """
    _ensure_repo(cwd)

    base_ref = base or _default_base(cwd)

    if working:
        merge_base = _git(cwd, "merge-base", base_ref, "HEAD").strip()
        spec = merge_base
        base_sha = merge_base
    else:
        spec = f"{base_ref}...HEAD"
        base_sha = _git(cwd, "rev-parse", base_ref).strip()

    diff = _git(cwd, "diff", spec)
    name_output = _git(cwd, "diff", "--name-only", spec)
    changed_files = [line for line in name_output.splitlines() if line]

    return PRContext(
        diff=diff,
        changed_files=changed_files,
        base_sha=base_sha,
        head_sha=_git(cwd, "rev-parse", "HEAD").strip(),
        repo=_repo_name(cwd),
        pr_number=0,
        # Commit names are the local stated intent — the CLI counterpart to a PR
        # title — feeding the intent lens. Empty when HEAD sits on the base.
        commit_messages=_commit_subjects(cwd, base_ref),
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
    """The remote primary branch, falling back through local names.

    ``origin/HEAD`` is only set by a normal clone of a non-empty repo; after
    ``git remote add`` (or cloning an empty repo) it is missing, and a bare
    ``main`` fallback would silently compare against a possibly stale LOCAL
    main. So prefer the remote-tracking refs before any local branch, and end
    at HEAD (an empty comparison) rather than failing.
    """
    try:
        return _git(cwd, "rev-parse", "--abbrev-ref", "origin/HEAD").strip()
    except ValueError:
        pass
    for candidate in ("origin/main", "origin/master", "main", "master"):
        if _ref_exists(cwd, candidate):
            return candidate
    return "HEAD"


def _ref_exists(cwd: Path | None, ref: str) -> bool:
    try:
        _git(cwd, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    except ValueError:
        return False
    return True


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
