"""Delte pytest-fixtures for Intelligence Monitor-tester.

Fixtures her importeres eksplisitt i testfiler som trenger dem.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

# Peker til skjema.sql fra prosjektroten
_SKJEMA_STI = Path(__file__).resolve().parents[2] / "src" / "intelligence_monitor" / "db" / "skjema.sql"


@pytest.fixture()
def vault_rot(tmp_path: Path) -> Path:
    """Midlertidig vault-mappe med alle nødvendige undermapper.

    Args:
        tmp_path: pytest sin midlertidige mappe (unikt per test).

    Returns:
        Sti til vault-roten.
    """
    for mappe in ["artikler", "ressurser/bilder", "innboks", "behandlet"]:
        (tmp_path / mappe).mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def db_sti(tmp_path: Path) -> Path:
    """Midlertidig SQLite-database med fase A-skjema og manuell-klipp-kilde.

    Args:
        tmp_path: pytest sin midlertidige mappe (unikt per test).

    Returns:
        Sti til testdatabasen.
    """
    sti = tmp_path / "test.db"
    skjema = _SKJEMA_STI.read_text(encoding="utf-8")
    with sqlite3.connect(sti) as tilkobling:
        tilkobling.execute("PRAGMA foreign_keys = ON")
        tilkobling.executescript(skjema)
        # Sett inn manuell-klipp-kilde slik at kilde_id = 1 er tilgjengelig
        tilkobling.execute(
            "INSERT INTO kilder (navn, url, type) VALUES ('manuell-klipp', 'lokal', 'manuell')"
        )
    return sti
