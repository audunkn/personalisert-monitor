"""Initialisering av Intelligence Monitor-databasen.

Oppretter alle fase A-tabeller (idempotent) og synkroniserer kildelisten
fra konfig/kilder.yaml til kilder-tabellen i SQLite.

Bruk:
    python -m intelligence_monitor.db.init
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

from intelligence_monitor.opik_konfig import konfigurer_opik


# Prosjektrot er tre nivåer opp fra denne filen (src/intelligence_monitor/db/)
_PROSJEKTROT = Path(__file__).resolve().parents[3]
_SKJEMA_STI = Path(__file__).parent / "skjema.sql"
_YAML_STI = _PROSJEKTROT / "konfig" / "kilder.yaml"


def initialiser(db_sti: str | Path) -> None:
    """Oppretter databasen og synkroniserer kildelisten fra YAML.

    Args:
        db_sti: Sti til SQLite-databasefilen. Opprettes hvis den ikke finnes.
    """
    konfigurer_opik()           # Opik konfigureres før databasetilkobling
    db_sti = Path(db_sti)
    db_sti.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute("PRAGMA foreign_keys = ON")
        _opprett_tabeller(tilkobling)
        _synkroniser_kilder(tilkobling)


def _opprett_tabeller(tilkobling: sqlite3.Connection) -> None:
    """Kjører skjema.sql mot databasen og legger til nye kolonner idempotent.

    CREATE TABLE IF NOT EXISTS er allerede idempotent. Nye kolonner som ble
    lagt til etter at databasen først ble opprettet, håndteres eksplisitt med
    ALTER TABLE — feil fordi kolonnen allerede finnes ignoreres stille.
    """
    skjema = _SKJEMA_STI.read_text(encoding="utf-8")
    tilkobling.executescript(skjema)

    # A1: feilfelt på kilder — idempotent (ignorerer feil hvis kolonnen finnes)
    for kolonne_sql in [
        "ALTER TABLE kilder ADD COLUMN sist_feil_tidsstempel TEXT",
        "ALTER TABLE kilder ADD COLUMN sist_feil_melding TEXT",
    ]:
        try:
            tilkobling.execute(kolonne_sql)
        except Exception:
            pass  # Kolonnen finnes allerede — trygt å ignorere


def _synkroniser_kilder(tilkobling: sqlite3.Connection) -> None:
    """Synkroniserer konfig/kilder.yaml til kilder-tabellen.

    Ny kilde     → INSERT
    Eksisterende → UPDATE url, type, hent_fra, hent_til, aktiv = 1
    Fjernet kilde → sett aktiv = 0 (soft delete, bevarer historikk)
    """
    yaml_data = yaml.safe_load(_YAML_STI.read_text(encoding="utf-8"))
    yaml_kilder = {k["navn"]: k for k in yaml_data["kilder"]}

    # Hent alle eksisterende kildenavn fra databasen
    eksisterende = {
        rad[0] for rad in tilkobling.execute("SELECT navn FROM kilder").fetchall()
    }

    for navn, kilde in yaml_kilder.items():
        if navn in eksisterende:
            # Oppdater feltene — aktiv settes tilbake til 1 hvis den var deaktivert
            tilkobling.execute(
                """
                UPDATE kilder
                SET url = ?, type = ?, hent_fra = ?, hent_til = ?, aktiv = 1
                WHERE navn = ?
                """,
                (kilde["url"], kilde["type"], kilde.get("hent_fra"), kilde.get("hent_til"), navn),
            )
        else:
            tilkobling.execute(
                """
                INSERT INTO kilder (navn, url, type, aktiv, hent_fra, hent_til)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (navn, kilde["url"], kilde["type"], kilde.get("hent_fra"), kilde.get("hent_til")),
            )

    # Deaktiver kilder som er fjernet fra YAML
    for navn in eksisterende - yaml_kilder.keys():
        tilkobling.execute("UPDATE kilder SET aktiv = 0 WHERE navn = ?", (navn,))


if __name__ == "__main__":
    db_sti = os.getenv("DATABASE_STI", "data/monitor.db")
    print(f"Initialiserer database: {db_sti}")
    initialiser(db_sti)
    print("Ferdig.")
