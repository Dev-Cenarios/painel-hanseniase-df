"""Sem a fonte de dados, os testes que precisam dela pulam, não falham."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import dados  # noqa: E402


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "dado: precisa da fonte de dados; pulado sem ela")


def pytest_collection_modifyitems(items) -> None:
    if dados.disponivel():
        return
    pular = pytest.mark.skip(reason="fonte de dados ausente — ver README")
    for item in items:
        if item.get_closest_marker("dado"):
            item.add_marker(pular)


def pytest_report_header() -> str:
    return f"fonte de dados: {'presente' if dados.disponivel() else 'AUSENTE (rode os scripts/)'}"
