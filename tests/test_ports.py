"""Boundary interfaces: importable and genuinely abstract."""

from __future__ import annotations

import abc

import pytest

from lgtmaybe.core.ports import GitHubGateway, ProviderClient, ReviewEngine

PORTS = [ProviderClient, GitHubGateway, ReviewEngine]


@pytest.mark.parametrize("port", PORTS, ids=lambda p: p.__name__)
def test_ports_are_abstract(port: type) -> None:
    assert issubclass(port, abc.ABC)
    with pytest.raises(TypeError):
        port()  # type: ignore[abstract]
