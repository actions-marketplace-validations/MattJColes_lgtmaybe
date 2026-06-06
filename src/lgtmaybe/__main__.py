"""Module entrypoint placeholder.

The real CLI is wired in the CLI track. For now this keeps `python -m lgtmaybe`
(and the Docker ENTRYPOINT) runnable on the skeleton.
"""

from __future__ import annotations

import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    print(f"lgtmaybe {__version__} — CLI not wired yet (see CLAUDE.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
