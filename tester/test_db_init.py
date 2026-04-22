"""Enhetstester for src/intelligence_monitor/db/init.py.

Verifiserer to kritiske egenskaper:
1. Idempotens — gjentatt kjøring av initialiser() ødelegger ikke eksisterende data.
2. YAML→SQLite-synk — kildelisten i YAML reflekteres alltid korrekt i databasen.

Opik-kallet i initialiser() er mocket for å isolere databaselogikken fra
ekstern infrastruktur (ingen ekte API-nøkkel nødvendig i CI).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_sti(tmp_path: Path) -> Path:
    """Returnerer sti til en midlertidig SQLite-testdatabase."""
    return tmp_path / "test.db"


@pytest.fixture()
def yaml_sti(tmp_path: Path) -> Path:
    """Oppretter en midlertidig YAML-fil med to startkilder."""
    sti = tmp_path / "kilder.yaml"
    _skriv_yaml(sti, [
        {"navn": "kilde-a", "type": "rss", "url": "https://a.example.com/feed", "hent_fra": "2024-01-01", "hent_til": None},
        {"navn": "kilde-b", "type": "substack", "url": "https://b.example.com", "hent_fra": "2024-06-01", "hent_til": None},
    ])
    return sti


# ---------------------------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------------------------

def _skriv_yaml(sti: Path, kilder: list[dict]) -> None:
    """Skriver kildelisten til YAML-filen på angitt sti."""
    sti.write_text(
        yaml.dump({"kilder": kilder}, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def _hent_tabeller(db_sti: Path) -> set[str]:
    """Returnerer settet av tabellnavn i databasen."""
    with sqlite3.connect(db_sti) as con:
        rader = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    return {rad[0] for rad in rader}


def _hent_kilder(db_sti: Path) -> list[dict]:
    """Returnerer alle rader fra kilder-tabellen som dict-liste."""
    with sqlite3.connect(db_sti) as con:
        con.row_factory = sqlite3.Row
        rader = con.execute("SELECT * FROM kilder").fetchall()
    return [dict(rad) for rad in rader]


# ---------------------------------------------------------------------------
# Tester
# ---------------------------------------------------------------------------

def test_idempotens(db_sti: Path, yaml_sti: Path, mocker) -> None:
    """Kjøre initialiser() to ganger skal ikke doble data eller slette tabeller.

    Verifiserer:
    - Alle fire fase A-tabeller eksisterer etter begge kjøringer.
    - Antall rader i kilder-tabellen er 2 (ikke 4) etter andre kjøring.
    """
    from intelligence_monitor.db import init as db_init

    mocker.patch("intelligence_monitor.db.init.konfigurer_opik")
    mocker.patch.object(db_init, "_YAML_STI", yaml_sti)

    # Første kjøring
    db_init.initialiser(db_sti)
    # Andre kjøring — skal ikke feile eller doble data
    db_init.initialiser(db_sti)

    forventede_tabeller = {"kilder", "elementer", "sammendrag", "evalueringstriplets"}
    assert forventede_tabeller.issubset(_hent_tabeller(db_sti)), (
        "Ikke alle fire fase A-tabeller ble funnet etter to kjøringer av initialiser()"
    )

    kilder = _hent_kilder(db_sti)
    assert len(kilder) == 2, (
        f"Forventet 2 rader i kilder etter idempotent kjøring, fikk {len(kilder)}"
    )


def test_yaml_synk(db_sti: Path, yaml_sti: Path, mocker) -> None:
    """YAML→SQLite-synkronisering: ny kilde inn, fjernet kilde settes aktiv=0.

    Scenario:
    1. Initialiser med to startkilder.
    2. Legg til 'ny-kilde' i YAML → kjør initialiser() → verifiser at ny-kilde
       finnes med korrekt hent_fra og aktiv = 1.
    3. Fjern 'ny-kilde' fra YAML → kjør initialiser() → verifiser aktiv = 0.
    """
    from intelligence_monitor.db import init as db_init

    mocker.patch("intelligence_monitor.db.init.konfigurer_opik")
    mocker.patch.object(db_init, "_YAML_STI", yaml_sti)

    # Steg 1: initialiser med startkilder
    db_init.initialiser(db_sti)

    # Steg 2: legg til ny kilde
    ny_kilde = {
        "navn": "ny-kilde",
        "type": "rss",
        "url": "https://ny.example.com/feed",
        "hent_fra": "2025-01-01",
        "hent_til": None,
    }
    startkilder = [
        {"navn": "kilde-a", "type": "rss", "url": "https://a.example.com/feed", "hent_fra": "2024-01-01", "hent_til": None},
        {"navn": "kilde-b", "type": "substack", "url": "https://b.example.com", "hent_fra": "2024-06-01", "hent_til": None},
    ]
    _skriv_yaml(yaml_sti, startkilder + [ny_kilde])
    db_init.initialiser(db_sti)

    kilder = {k["navn"]: k for k in _hent_kilder(db_sti)}
    assert "ny-kilde" in kilder, "ny-kilde ble ikke lagt til i kilder-tabellen"
    assert kilder["ny-kilde"]["hent_fra"] == "2025-01-01", (
        f"Feil hent_fra for ny-kilde: {kilder['ny-kilde']['hent_fra']!r}"
    )
    assert kilder["ny-kilde"]["aktiv"] == 1, (
        f"ny-kilde skal ha aktiv=1 etter innsetting, fikk {kilder['ny-kilde']['aktiv']}"
    )

    # Steg 3: fjern ny-kilde fra YAML
    _skriv_yaml(yaml_sti, startkilder)
    db_init.initialiser(db_sti)

    kilder = {k["navn"]: k for k in _hent_kilder(db_sti)}
    assert "ny-kilde" in kilder, "ny-kilde skal fortsatt finnes (soft delete)"
    assert kilder["ny-kilde"]["aktiv"] == 0, (
        f"ny-kilde skal ha aktiv=0 etter fjerning fra YAML, fikk {kilder['ny-kilde']['aktiv']}"
    )
