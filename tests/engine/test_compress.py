"""Tests for compress.py — token-aware patch fitting."""

from __future__ import annotations

from lgtmaybe.engine.compress import batch_files, count_tokens

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
