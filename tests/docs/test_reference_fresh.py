"""Verify that docs/reference/config.md matches the committed generated output.

If this test fails, run `uv run python docs/generate_reference.py` and commit
the updated file.
"""

import sys
from pathlib import Path

# Allow importing the generator without it being a package.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "docs"))

from generate_reference import generate  # noqa: E402

COMMITTED_PATH = Path(__file__).parent.parent.parent / "docs" / "reference" / "config.md"


def test_reference_matches_committed_file() -> None:
    committed = COMMITTED_PATH.read_text(encoding="utf-8")
    regenerated = generate()
    assert regenerated == committed, (
        "docs/reference/config.md is stale. "
        "Run `uv run python docs/generate_reference.py` and commit the result."
    )
