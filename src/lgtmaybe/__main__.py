"""Module entrypoint: ``python -m lgtmaybe`` and the Docker ENTRYPOINT.

Delegates to the Click CLI group, which handles argv and exit codes itself.
"""

from __future__ import annotations

from lgtmaybe.cli import main

if __name__ == "__main__":
    main()
