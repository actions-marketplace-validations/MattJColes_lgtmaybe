"""Deterministic code-quality guards.

These are *factual*, not stylistic — they fail only on things that are
objectively outdated, never on opinion:

- importing any lgtmaybe module must not trigger a DeprecationWarning (i.e. we
  are not calling deprecated stdlib / dependency APIs on an import path);
- the deprecation gate in pyproject must stay wired, so nobody can silently
  drop it.

Newer-version availability and CVE scanning are intentionally *not* here — they
depend on the outside world at time-of-check and so can't be deterministic. They
live in scheduled background tooling (Dependabot + the audit workflow).
"""

from __future__ import annotations

import importlib
import pkgutil
import tomllib
import warnings
from pathlib import Path

import pytest

import lgtmaybe

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _all_module_names() -> list[str]:
    """Every importable lgtmaybe submodule, minus the executable entrypoint."""
    names = [lgtmaybe.__name__]
    for info in pkgutil.walk_packages(lgtmaybe.__path__, prefix="lgtmaybe."):
        if info.name.endswith(".__main__"):
            continue  # entrypoint module — nothing to assert, avoid argv side effects
        names.append(info.name)
    return names


@pytest.mark.parametrize("module_name", _all_module_names())
def test_module_imports_without_deprecation_warnings(module_name: str) -> None:
    """No lgtmaybe module may use a deprecated API on its import path."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        warnings.simplefilter("error", PendingDeprecationWarning)
        importlib.import_module(module_name)


def test_deprecation_gate_is_configured() -> None:
    """The pyproject deprecation gate must stay in place (don't silently drop it)."""
    cfg = tomllib.loads(_PYPROJECT.read_text())
    filters = cfg["tool"]["pytest"]["ini_options"]["filterwarnings"]
    assert "error::DeprecationWarning" in filters
    assert "error::PendingDeprecationWarning" in filters
