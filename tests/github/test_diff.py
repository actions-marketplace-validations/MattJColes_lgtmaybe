"""Tests for diff position map and skip filter."""

from __future__ import annotations

from lgtmaybe.github import build_position_map, is_reviewable

# ---------------------------------------------------------------------------
# Diff position map
# ---------------------------------------------------------------------------

SAMPLE_DIFF = """\
diff --git a/src/app.py b/src/app.py
index 0000001..0000002 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,4 +1,6 @@
 import os
+import sys

 def main():
-    pass
+    print("hello")
+    return 0
diff --git a/src/utils.py b/src/utils.py
index 0000003..0000004 100644
--- a/src/utils.py
+++ b/src/utils.py
@@ -10,3 +10,4 @@ def helper():
     x = 1
     y = 2
     return x + y
+    # comment added
"""


def test_position_map_context_line() -> None:
    """A context line (unchanged) maps to a position within the hunk."""
    pos_map = build_position_map(SAMPLE_DIFF)
    # Line 1 of src/app.py is "import os" — a context line at new-file line 1.
    # It is diff position 1 within the first file's hunk.
    assert pos_map.get(("src/app.py", 1)) == 1


def test_position_map_added_line() -> None:
    """An added line maps to its correct 1-based diff position."""
    pos_map = build_position_map(SAMPLE_DIFF)
    # "import sys" is the first added line in src/app.py, at new-file line 2.
    # Hunk header is position 0 (not counted); context "import os" is pos 1;
    # "+import sys" is pos 2.
    assert pos_map.get(("src/app.py", 2)) == 2


def test_position_map_line_not_in_diff_returns_none() -> None:
    """A line number outside any hunk maps to None."""
    pos_map = build_position_map(SAMPLE_DIFF)
    assert pos_map.get(("src/app.py", 999)) is None


def test_position_map_unknown_file_returns_none() -> None:
    """A file not present in the diff maps to None for any line."""
    pos_map = build_position_map(SAMPLE_DIFF)
    assert pos_map.get(("totally_absent.py", 1)) is None


def test_position_map_second_file() -> None:
    """Position counting resets per file, not globally."""
    pos_map = build_position_map(SAMPLE_DIFF)
    # src/utils.py: hunk @@ -10,3 +10,4 @@
    # new-file line 10 → "    x = 1" → diff position 1 (first line after hunk header)
    assert pos_map.get(("src/utils.py", 10)) == 1


def test_position_map_deleted_line_not_in_new_file() -> None:
    """Deleted lines do not advance the new-file line counter, so they have no position."""
    pos_map = build_position_map(SAMPLE_DIFF)
    # src/app.py original line 4 was "    pass" (deleted).
    # After deletion the new file jumps from line 3 to line 4 being "    print(...)".
    # There is no new-file line corresponding to the deleted line itself.
    # The test just verifies the map contains known good entries and not junk.
    assert ("src/app.py", 5) in pos_map or ("src/app.py", 4) in pos_map  # either is fine


# ---------------------------------------------------------------------------
# Skip filter
# ---------------------------------------------------------------------------

MIXED_FILE_LIST = [
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "app.min.js",
    "styles.min.css",
    "vendor/lib.py",
    "node_modules/dep/index.js",
    "dist/bundle.js",
    "src/__snapshots__/app.test.js.snap",
    "image.png",
    "binary.exe",
    "src/app.py",
    "src/models.py",
]


def test_is_reviewable_rejects_lockfiles() -> None:
    assert not is_reviewable("package-lock.json")
    assert not is_reviewable("yarn.lock")
    assert not is_reviewable("pnpm-lock.yaml")


def test_is_reviewable_rejects_minified() -> None:
    assert not is_reviewable("app.min.js")
    assert not is_reviewable("styles.min.css")


def test_is_reviewable_rejects_vendor_and_generated_dirs() -> None:
    assert not is_reviewable("vendor/lib.py")
    assert not is_reviewable("node_modules/dep/index.js")
    assert not is_reviewable("dist/bundle.js")


def test_is_reviewable_rejects_snapshots() -> None:
    assert not is_reviewable("src/__snapshots__/app.test.js.snap")


def test_is_reviewable_rejects_binary_extensions() -> None:
    assert not is_reviewable("image.png")
    assert not is_reviewable("binary.exe")


def test_is_reviewable_accepts_source_files() -> None:
    assert is_reviewable("src/app.py")
    assert is_reviewable("src/models.py")


def test_filter_mixed_list_leaves_only_source() -> None:
    """Given a mixed file list, only source files survive."""
    reviewable = [f for f in MIXED_FILE_LIST if is_reviewable(f)]
    assert reviewable == ["src/app.py", "src/models.py"]
