"""Diff utilities: position map and skip filter.

Position map: GitHub review comments need a 1-based `position` that counts
lines in the patch (hunk headers count as 0, context/add/remove lines count
sequentially). We build a mapping of (filename, new_file_line) → position so
the gateway can anchor findings to the right spot.

Skip filter: lockfiles, minified bundles, vendored/generated paths and binary
files are dropped before review to save tokens and avoid noise.
"""

from __future__ import annotations

from fnmatch import fnmatch

from lgtmaybe.core.diffparse import FILE_HEADER_RE, parse_hunk_header

# ---------------------------------------------------------------------------
# Position map
# ---------------------------------------------------------------------------

# Maps (filename, new_file_line_number) → 1-based diff position within that file's hunks.
PositionMap = dict[tuple[str, int], int]


def build_position_map(diff: str) -> PositionMap:
    """Parse a unified diff and build a (file, new_line) → diff_position mapping.

    `diff_position` is the 1-based offset of that line within the file's patch
    block (hunk headers do not count as a position themselves; the first content
    line after the first hunk header is position 1).

    Deleted lines ("-") advance the diff position counter but do not produce a
    new-file line entry. Context lines (no prefix or " " prefix) and added lines
    ("+") both advance the new-file line counter.
    """
    pos_map: PositionMap = {}

    current_file: str | None = None
    diff_pos = 0  # 1-based position within this file's hunks
    new_line = 0  # current new-file line number
    in_hunk = False

    for raw_line in diff.splitlines():
        file_match = FILE_HEADER_RE.match(raw_line)
        if file_match:
            current_file = file_match.group(1)
            diff_pos = 0
            new_line = 0
            in_hunk = False
            continue

        if current_file is None:
            continue

        hunk = parse_hunk_header(raw_line)
        if hunk is not None:
            # Hunk header resets the new-file line counter; diff_pos keeps counting
            # across hunks within a file. The hunk header line does NOT occupy a
            # position itself — the first content line after it is position 1 (or
            # position N+1 if prior hunks exist). GitHub's position is a 1-based
            # count of content lines only.
            new_line = hunk.new_start
            in_hunk = True
            continue

        if not in_hunk:
            continue

        if raw_line.startswith("-"):
            # Deleted line: advances diff_pos but NOT new_line.
            diff_pos += 1
        elif raw_line.startswith("+"):
            # Added line: advances both.
            diff_pos += 1
            pos_map[(current_file, new_line)] = diff_pos
            new_line += 1
        else:
            # Context line (leading " " or empty).
            diff_pos += 1
            pos_map[(current_file, new_line)] = diff_pos
            new_line += 1

    return pos_map


# ---------------------------------------------------------------------------
# Skip filter
# ---------------------------------------------------------------------------

_SKIP_FILENAMES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "npm-shrinkwrap.json",
        "Cargo.lock",
        "Gemfile.lock",
        "poetry.lock",
        "Pipfile.lock",
        "composer.lock",
        "go.sum",
    }
)

_SKIP_DIR_PREFIXES = (
    "vendor/",
    "node_modules/",
    "dist/",
    "build/",
    ".git/",
    "third_party/",
    "third-party/",
)

# Glob patterns matched against the full path.
_SKIP_GLOB_PATTERNS = (
    "*.min.js",
    "*.min.css",
    "*.snap",
    "*.pb.go",
    "*.pb.py",
    "*.generated.*",
    "__generated__/*",
    "*.d.ts",
)

_SKIP_EXTENSIONS = frozenset(
    {
        # Images
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".svg",
        ".webp",
        ".tiff",
        # Compiled / binary
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".a",
        ".o",
        ".obj",
        ".pyc",
        ".pyo",
        # Archives
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        # Media
        ".mp3",
        ".mp4",
        ".wav",
        ".ogg",
        ".avi",
        ".mov",
        ".mkv",
        # Docs / data blobs
        ".pdf",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        # Java/JVM
        ".class",
        ".jar",
        ".war",
    }
)


def is_reviewable(path: str) -> bool:
    """Return True if the file at *path* should be reviewed.

    Rejects lockfiles, minified files, vendored/generated directories, snapshot
    files, and binary extensions. Everything else passes through.
    """
    filename = path.rsplit("/", 1)[-1]

    if filename in _SKIP_FILENAMES:
        return False

    # Extension check
    dot = filename.rfind(".")
    if dot != -1:
        ext = filename[dot:].lower()
        if ext in _SKIP_EXTENSIONS:
            return False

    # Directory prefix check (path must start with one of the blocked dirs)
    for prefix in _SKIP_DIR_PREFIXES:
        if path.startswith(prefix) or ("/" + prefix) in path:
            return False

    # Glob pattern check on the full path
    for pattern in _SKIP_GLOB_PATTERNS:
        if fnmatch(path, pattern) or fnmatch(filename, pattern):
            return False

    return True
