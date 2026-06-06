"""Tests for compress.py — token-aware patch fitting."""

from __future__ import annotations

from lgtmaybe.engine.compress import batch_files, count_tokens, expand_hunks

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_SMALL_DIFF = "@@ -1,3 +1,4 @@\n context\n+added line\n context\n"
_FILE_BLOCK = "diff --git a/{name} b/{name}\n{diff}"


def _make_diff(n_files: int, lines_per_file: int = 5) -> list[tuple[str, str]]:
    """Return list of (path, patch) pairs."""
    result = []
    for i in range(n_files):
        lines = "\n".join(f"+line {j}" for j in range(lines_per_file))
        patch = f"@@ -0,0 +1,{lines_per_file} @@\n{lines}\n"
        result.append((f"file_{i}.py", patch))
    return result


# ---------------------------------------------------------------------------
# count_tokens
# ---------------------------------------------------------------------------


def test_count_tokens_returns_int() -> None:
    assert isinstance(count_tokens("hello world"), int)


def test_count_tokens_scales_with_length() -> None:
    short = count_tokens("x")
    long = count_tokens("x " * 1000)
    assert long > short


# ---------------------------------------------------------------------------
# batch_files: single-call path
# ---------------------------------------------------------------------------


def test_small_pr_fits_one_batch() -> None:
    files = _make_diff(3)
    batches = batch_files(files, max_tokens=10_000)
    assert len(batches) == 1


def test_large_pr_stays_under_token_budget_per_batch() -> None:
    # 50 files × 200 lines each — well over a 2 000-token budget per batch
    files = _make_diff(50, lines_per_file=200)
    budget = 2_000
    batches = batch_files(files, max_tokens=budget)
    assert len(batches) > 1
    for batch in batches:
        combined = "\n".join(patch for _, patch in batch)
        assert count_tokens(combined) <= budget


def test_oversize_pr_is_bounded() -> None:
    files = _make_diff(100, lines_per_file=200)
    budget = 3_000
    batches = batch_files(files, max_tokens=budget)
    # number of batches must be bounded (≤ number of files in worst case)
    assert len(batches) <= len(files)


# ---------------------------------------------------------------------------
# dynamic context: small PR gets more context lines than a big PR
# ---------------------------------------------------------------------------


def test_dynamic_context_more_for_small_pr() -> None:
    from lgtmaybe.engine.compress import context_lines_for_budget

    small_pr_tokens_used = 500
    large_pr_tokens_used = 90_000
    budget = 100_000

    ctx_small = context_lines_for_budget(budget - small_pr_tokens_used)
    ctx_large = context_lines_for_budget(budget - large_pr_tokens_used)

    assert ctx_small > ctx_large
    assert ctx_small >= 0
    assert ctx_large >= 0


# ---------------------------------------------------------------------------
# expand_hunks: pad hunks with surrounding lines from head file content
# ---------------------------------------------------------------------------

_CONTENT = "\n".join("abcdefghij")  # lines 1..10: a, b, c, ... j


def test_expand_hunks_adds_surrounding_lines() -> None:
    # Hunk covers new-file lines 5..6 (e, E2); ask for 2 lines either side.
    patch = "diff --git a/f.py b/f.py\n@@ -5,2 +5,2 @@\n e\n+E2\n"

    expanded = expand_hunks(patch, _CONTENT, 2)

    # Two leading lines (c, d) and two trailing lines (g, h) are added as context.
    assert "\n c\n d\n" in expanded
    assert "\n g\n h\n" in expanded
    # Header line/length counts are widened by the added context on both sides.
    assert "@@ -3,6 +3,6 @@" in expanded


def test_expand_hunks_noop_when_n_zero() -> None:
    patch = "diff --git a/f.py b/f.py\n@@ -5,2 +5,2 @@\n e\n+E2\n"
    assert expand_hunks(patch, _CONTENT, 0) == patch


def test_expand_hunks_noop_when_no_content() -> None:
    patch = "diff --git a/f.py b/f.py\n@@ -5,2 +5,2 @@\n e\n+E2\n"
    assert expand_hunks(patch, None, 5) == patch


def test_expand_hunks_clamps_at_file_edges() -> None:
    # Hunk at the very top of the file: no leading context possible, and a huge
    # n must not read past either end.
    patch = "diff --git a/f.py b/f.py\n@@ -1,1 +1,1 @@\n a\n"
    expanded = expand_hunks(patch, _CONTENT, 100)

    # No phantom lines before line 1.
    assert "@@ -1," in expanded
    # Trailing context is clamped to the last real line (j) — no over-read.
    assert expanded.rstrip().endswith(" j")
