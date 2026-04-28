"""Innhentings-shell for Intelligence Monitor.

Koordinerer alle aktive innhentingskanaler. I A1 støttes kun RSS.
Øvrige kanaler (nett, YouTube, Substack) legges til i A4 og A6.

Bruk:
    python -m intelligence_monitor.innhenter.kjører
    make innhent
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from intelligence_monitor.innhenter import rss  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_PROSJEKTROT = Path(__file__).resolve().parents[3]


def _rydd_foreldreløse(db_sti: Path, vault_rot: Path) -> int:
    """Sletter SQLite-rader der vault-filen ikke lenger eksisterer.

    Henter alle elementer med vault_sti IS NOT NULL og sjekker om filen
    finnes. Manglende filer behandles likt som i obsidian_vakt:
    bilder slettes fra vault/ressurser/bilder/, deretter evalueringstriplets,
    sammendrag og elementer-raden.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        vault_rot: Rot-mappe for Obsidian-vault.

    Returns:
        Antall slettede elementer.
    """
    with sqlite3.connect(db_sti) as tilkobling:
        rader = tilkobling.execute(
            "SELECT id, vault_sti, bilder_json FROM elementer WHERE vault_sti IS NOT NULL"
        ).fetchall()

    antall_slettet = 0
    bilde_mappe = vault_rot / "ressurser" / "bilder"

    for element_id, vault_sti, bilder_json_tekst in rader:
        if (vault_rot / vault_sti).exists():
            continue

        bildefilnavn: list[str] = json.loads(bilder_json_tekst) if bilder_json_tekst else []
        for filnavn in bildefilnavn:
            bilde_fil = bilde_mappe / filnavn
            if bilde_fil.exists():
                bilde_fil.unlink()

        with sqlite3.connect(db_sti) as tilkobling:
            tilkobling.execute(
                "DELETE FROM evalueringstriplets WHERE element_id = ?", (element_id,)
            )
            tilkobling.execute(
                "DELETE FROM sammendrag WHERE element_id = ?", (element_id,)
            )
            tilkobling.execute("DELETE FROM elementer WHERE id = ?", (element_id,))

        antall_slettet += 1

    if antall_slettet:
        logger.info("Ryddet %d foreldreløse element(er) fra SQLite", antall_slettet)

    return antall_slettet


def oppdater() -> None:
    """Rydder foreldreløse SQLite-rader og kjører alle aktive innhentingskanaler."""
    logger.info("=== Innhenting starter ===")

    db_sti = Path(os.getenv("DATABASE_STI", str(_PROSJEKTROT / "data" / "monitor.db")))
    vault_rot = Path(os.getenv("VAULT_ROT", str(_PROSJEKTROT / "vault")))
    _rydd_foreldreløse(db_sti, vault_rot)

    nye_rss = rss.innhent_alle()
    # TODO A4: legg til nett.innhent_alle() og substack.innhent_alle()
    # TODO A6: legg til youtube.innhent_alle()

    totalt = nye_rss
    logger.info("=== Innhenting ferdig — %d nye artikler totalt ===", totalt)


if __name__ == "__main__":
    oppdater()
