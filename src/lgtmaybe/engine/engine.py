"""LLMReviewEngine: the full review pipeline.

Pipeline: redact → compress/batch → (for each batch) build messages → provider.complete
         → parse/repair → self-reflect/filter → filter by min_severity → return findings + summary.
"""

from __future__ import annotations

from lgtmaybe.core.diffparse import split_by_file
from lgtmaybe.core.models import PRContext, ReviewConfig, ReviewFinding
from lgtmaybe.core.ports import Message, ProviderClient, ReviewEngine
from lgtmaybe.github import is_reviewable

from .compress import batch_files, context_lines_for_budget, count_tokens, expand_hunks
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
        file_patches = split_by_file(clean_diff, ctx.changed_files)
        file_patches = [(path, patch) for path, patch in file_patches if is_reviewable(path)]

        # 3. File cap: review only the first N reviewable files, note the rest.
        total_files = len(file_patches)
        capped_files = total_files > cfg.max_files
        if capped_files:
            file_patches = file_patches[: cfg.max_files]

        # 4. Pad each hunk with surrounding lines so the model sees the function
        #    and definitions around a change. The amount is budget-scaled and
        #    capped by cfg.context_lines; content is the head file text the
        #    gateway fetched (redacted), and is for understanding only —
        #    inline-comment positions are always built from the real diff.
        used_tokens = count_tokens(clean_diff)
        remaining = max(0, cfg.max_input_tokens - used_tokens)
        ctx_lines = min(cfg.context_lines, context_lines_for_budget(remaining))
        if ctx_lines > 0 and ctx.file_contents:
            file_patches = [
                (path, expand_hunks(patch, redact(ctx.file_contents.get(path, "")), ctx_lines))
                for path, patch in file_patches
            ]

        batches = batch_files(file_patches, max_tokens=cfg.max_input_tokens)

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
        #    Skippable (--no-reflect) for weaker models that drop valid findings here.
        if cfg.reflect and all_findings:
            reviewed_diff = "\n".join(patch for _, patch in file_patches)
            clean_ctx = ctx.model_copy(update={"diff": reviewed_diff})
            all_findings = reflect_findings(all_findings, clean_ctx, cfg, self._provider)

        # 7. Filter by min_severity.
        filtered = [f for f in all_findings if f.severity >= cfg.min_severity]

        plural = "s" if len(filtered) != 1 else ""
        summary_line = f"{len(filtered)} finding{plural} · model {cfg.model}"
        if capped_files:
            notice = (
                f"⚠️ Reviewed the top {cfg.max_files} of {total_files} changed files "
                f"(file cap {cfg.max_files}). Raise max_files to review them all."
            )
            return filtered, f"{notice}\n\n{summary_line}"
        # A genuinely clean review (nothing flagged, every file reviewed) gets an
        # explicit thumbs-up rather than a bare "0 findings".
        if not filtered:
            return filtered, f"👍 LGTM!\n\n{summary_line}"
        return filtered, summary_line

    @staticmethod
    def _cost_cap_notice(total_cost: float, cfg: ReviewConfig) -> str:
        return (
            f"⚠️ Review aborted: approximate cost ${total_cost:.4f} exceeded the "
            f"cap of ${cfg.max_cost_usd:.4f} (model {cfg.model}). "
            "Raise max_cost_usd to review the full PR."
        )
