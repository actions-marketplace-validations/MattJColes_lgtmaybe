"""Self-reflection pass: ask the provider to judge confidence in each finding.

Drops findings the model marks as low-confidence (keep=False).
"""

from __future__ import annotations

import json

from lgtmaybe.core.models import PRContext, ReviewConfig, ReviewFinding
from lgtmaybe.core.ports import ProviderClient

from .parse import strip_fences

_REFLECT_SYSTEM = """\
You are a senior code reviewer auditing another reviewer's findings for false positives.

Given a list of findings (as JSON) and the diff that generated them, return a JSON object \
mapping each finding's index (as a string key) to a boolean: true to keep it, false to drop it.

Keep a finding only if you are confident it is a real issue in the actual changed code.
Drop it if it is speculative, out of scope, or referring to unchanged lines.

Return ONLY the JSON object, nothing else. Example:
{"0": true, "1": false, "2": true}
"""


def reflect_findings(
    findings: list[ReviewFinding],
    ctx: PRContext,
    cfg: ReviewConfig,
    provider: ProviderClient,
) -> list[ReviewFinding]:
    """Filter *findings* by asking the provider to score confidence.

    Returns only findings the provider marks as keep=True.
    """
    if not findings:
        return []

    findings_json = json.dumps([f.model_dump(mode="json") for f in findings], indent=2)
    user_content = (
        f"Diff:\n{ctx.diff}\n\n"
        f"Findings (indexed from 0):\n{findings_json}\n\n"
        "Return the confidence verdict JSON object."
    )

    result = provider.complete(
        messages=[
            {"role": "system", "content": _REFLECT_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        model=cfg.model,
    )

    try:
        # Strip markdown fences if present, then parse the verdict object.
        raw = strip_fences(result.text.strip()).strip()
        verdicts: dict[str, bool] = json.loads(raw)
    except Exception:
        # If reflection fails to parse, keep all findings (safe default)
        return findings

    kept = []
    for i, finding in enumerate(findings):
        # Accept both int and string keys
        keep = verdicts.get(str(i), verdicts.get(i, True))  # type: ignore[call-overload]
        if keep:
            kept.append(finding)

    return kept
