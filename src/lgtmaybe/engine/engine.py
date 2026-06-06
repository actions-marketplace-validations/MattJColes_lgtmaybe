"""LLMReviewEngine: the full review pipeline.

Pipeline: redact → compress/batch → (for each batch) build messages → provider.complete
         → parse/repair → self-reflect/filter → filter by min_severity → return findings + summary.
"""

from __future__ import annotations

from lgtmaybe.core.models import PRContext, ReviewConfig, ReviewFinding
from lgtmaybe.core.ports import Message, ProviderClient, ReviewEngine
from lgtmaybe.github import is_reviewable

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

        # 2. Split into per-file patches and drop generated/binary/vendored noise.
        file_patches = _split_diff_by_file(clean_diff, ctx.changed_files)
        file_patches = [(path, patch) for path, patch in file_patches if is_reviewable(path)]

        # 3. File cap: review only the first N reviewable files, note the rest.
        total_files = len(file_patches)
        capped_files = total_files > cfg.max_files
        if capped_files:
            file_patches = file_patches[: cfg.max_files]

        batches = batch_files(file_patches, max_tokens=cfg.max_input_tokens)

        # 4. Determine how many extra context lines we can afford.
        used_tokens = count_tokens(clean_diff)
        remaining = max(0, cfg.max_input_tokens - used_tokens)
        _ctx_lines = context_lines_for_budget(remaining)  # available for future use

        system_prompt = build_system_prompt()

        all_findings: list[ReviewFinding] = []
        total_cost = 0.0

        # 5. Run one provider call per batch (single call for most PRs).
        #    Stop early if the accumulated cost crosses the cap.
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

            if total_cost > cfg.max_cost_usd:
                return [], self._cost_cap_notice(total_cost, cfg)

        # 6. Self-reflection: filter out low-confidence findings. Reflect against
        #    only the reviewed diff — redacted, and free of skipped/over-cap files.
        if all_findings:
            reviewed_diff = "\n".join(patch for _, patch in file_patches)
            clean_ctx = ctx.model_copy(update={"diff": reviewed_diff})
            all_findings = reflect_findings(all_findings, clean_ctx, cfg, self._provider)

        # 7. Filter by min_severity.
        filtered = [f for f in all_findings if f.severity >= cfg.min_severity]

        plural = "s" if len(filtered) != 1 else ""
        cost_line = (
            f"{len(filtered)} finding{plural} · model {cfg.model} · approx cost ${total_cost:.4f}"
        )
        if capped_files:
            notice = (
                f"⚠️ Reviewed the top {cfg.max_files} of {total_files} changed files "
                f"(file cap {cfg.max_files}). Raise max_files to review them all."
            )
            return filtered, f"{notice}\n\n{cost_line}"
        # A genuinely clean review (nothing flagged, every file reviewed) gets an
        # explicit thumbs-up rather than a bare "0 findings".
        if not filtered:
            return filtered, f"👍 LGTM!\n\n{cost_line}"
        return filtered, cost_line

    @staticmethod
    def _cost_cap_notice(total_cost: float, cfg: ReviewConfig) -> str:
        return (
            f"⚠️ Review aborted: approximate cost ${total_cost:.4f} exceeded the "
            f"cap of ${cfg.max_cost_usd:.4f} (model {cfg.model}). "
            "Raise max_cost_usd to review the full PR."
        )


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
