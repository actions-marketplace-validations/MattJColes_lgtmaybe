"""Token-aware patch fitting.

Splits changed files into batches that each fit within a token budget.
Provides a dynamic context-line calculator for the remaining budget.
"""

from __future__ import annotations

_MAX_CONTEXT_LINES = 20
_MIN_CONTEXT_LINES = 0
# Scale: remaining_tokens / _SCALE gives context lines, capped at _MAX_CONTEXT_LINES.
# At 100k budget with 500 tokens used → 99,500 / 5000 = 19 lines.
# At 100k budget with 90k tokens used → 10,000 / 5000 = 2 lines.
_SCALE = 5_000


def count_tokens(text: str) -> int:
    """Return the token count for *text* using tiktoken, with a len/4 fallback."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def batch_files(
    files: list[tuple[str, str]],
    max_tokens: int,
) -> list[list[tuple[str, str]]]:
    """Partition *files* into batches where each batch's combined patch fits under *max_tokens*.

    Args:
        files: List of (path, patch) pairs.
        max_tokens: Token budget per batch.

    Returns:
        A list of batches; each batch is a list of (path, patch) pairs.
    """
    if not files:
        return []

    batches: list[list[tuple[str, str]]] = []
    current_batch: list[tuple[str, str]] = []
    current_tokens = 0

    for path, patch in files:
        file_tokens = count_tokens(patch)

        # If a single file exceeds the budget on its own, give it its own batch.
        if file_tokens >= max_tokens:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            batches.append([(path, patch)])
            continue

        if current_tokens + file_tokens > max_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append((path, patch))
        current_tokens += file_tokens

    if current_batch:
        batches.append(current_batch)

    return batches


def context_lines_for_budget(remaining_tokens: int) -> int:
    """Return how many extra context lines to expand hunks by, given the remaining token budget.

    A larger remaining budget yields more context; a smaller one yields less.
    The result is capped between 0 and _MAX_CONTEXT_LINES.
    """
    if remaining_tokens <= 0:
        return _MIN_CONTEXT_LINES

    # Scale: every _TOKENS_PER_CONTEXT_LINE remaining tokens buys one context line,
    # up to _MAX_CONTEXT_LINES.
    lines = remaining_tokens // _SCALE
    return min(int(lines), _MAX_CONTEXT_LINES)
