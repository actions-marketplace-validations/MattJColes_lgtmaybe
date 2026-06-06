"""LLMReviewEngine: the full review pipeline.

Pipeline: redact → compress/batch → (for each batch) build messages → provider.complete
         → parse/repair → self-reflect/filter → filter by min_severity → return findings + summary.
"""

from __future__ import annotations

from lgtmaybe.core.models import PRContext, ReviewConfig, ReviewFinding
from lgtmaybe.core.ports import Message, ProviderClient, ReviewEngine

from .compress import batch_files, context_lines_for_budget, count_tokens
from .injection import wrap_diff
from .parse import ParseError, parse_findings
from .prompt import build_system_prompt
from .redact import redact
from .reflect import reflect_findings


class LLMReviewEngine(ReviewEngine):
    """Review engine that runs the full pipeline against an injected ProviderClient."""

    def __init__(self, provider: ProviderClient) -> None:
        self._provider = provider

    def review(self, ctx: PRContext, cfg: ReviewConfig) -> tuple[list[ReviewFinding], str]:
        """Run the review pipeline and return (findings, summary)."""
        # 1. Redact secrets from the diff before it leaves this process.
        clean_diff = redact(ctx.diff)

        # 2. Split the diff into per-file batches that each fit under the token budget.
        #    We parse changed_files paired with their hunks from the diff.
        file_patches = _split_diff_by_file(clean_diff, ctx.changed_files)
        batches = batch_files(file_patches, max_tokens=cfg.max_input_tokens)

        # 3. Determine how many extra context lines we can afford.
        used_tokens = count_tokens(clean_diff)
        remaining = max(0, cfg.max_input_tokens - used_tokens)
        _ctx_lines = context_lines_for_budget(remaining)  # available for future use

        system_prompt = build_system_prompt()

        all_findings: list[ReviewFinding] = []
        total_cost = 0.0

        # 4. Run one provider call per batch (single call for most PRs).
        for batch in batches:
            batch_diff = "\n".join(patch for _, patch in batch)
            wrapped = wrap_diff(batch_diff)
            messages: list[Message] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": wrapped},
            ]
            result = self._provider.complete(messages, model=cfg.model)
            total_cost += result.cost_usd

            try:
                findings = parse_findings(result.text)
            except ParseError:
                findings = []

            all_findings.extend(findings)

        # 5. Self-reflection: filter out low-confidence findings.
        #    Pass a redacted context so secrets don't leak in the reflection prompt.
        if all_findings:
            clean_ctx = ctx.model_copy(update={"diff": clean_diff})
            all_findings = reflect_findings(all_findings, clean_ctx, cfg, self._provider)

        # 6. Filter by min_severity.
        filtered = [f for f in all_findings if f.severity >= cfg.min_severity]

        plural = "s" if len(filtered) != 1 else ""
        summary = f"{len(filtered)} finding{plural} · cost ${total_cost:.4f}"
        return filtered, summary


def _split_diff_by_file(
    diff: str,
    changed_files: list[str],
) -> list[tuple[str, str]]:
    """Split a unified diff string into per-file (path, patch) pairs.

    Falls back to treating the whole diff as one file if parsing fails.
    """
    import re

    # Match 'diff --git a/... b/...' headers
    pattern = re.compile(r"^diff --git a/.+ b/(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(diff))

    if not matches:
        # No git diff headers — treat as a single chunk associated with the first changed file
        path = changed_files[0] if changed_files else "unknown"
        return [(path, diff)]

    result: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        path = match.group(1)
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(diff)
        result.append((path, diff[start:end]))

    return result
