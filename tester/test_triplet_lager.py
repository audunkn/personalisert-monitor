"""Enhetstester for src/intelligence_monitor/evaluering/triplet_lager.py.

Dekker fire kritiske grener:
1. Triplet skrives korrekt og kan hentes tilbake.
2. Godkjenningsrate og antall avviste beregnes korrekt ved kjente data.
3. Filtrering på komponent returnerer kun riktig komponent.
4. er_duplikat() returnerer True etter første innsending.

Alle tester bruker midlertidig SQLite. Ingen nettverkskall.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from intelligence_monitor.evaluering.triplet_lager import (
    beregn_statistikk,
    er_duplikat,
    filtrer_pa_komponent,
    lagre_triplet,
)
from tester.konfig.fixtures import db_sti  # noqa: F401


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_med_sammendrag(db_sti: Path) -> tuple[Path, int, int]:
    """Database med én kilde, ett element og ett sammendrag.

    Returns:
        (db_sti, element_id, sammendrag_id) — klart til triplet-skriving.
    """
    with sqlite3.connect(db_sti) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            "INSERT INTO elementer (kilde_id, guid, url, tittel, hentet) "
            "VALUES (1, 'guid-triplet-1', 'https://example.com/art1', 'Testart', '2026-04-24T10:00:00')"
        )
        element_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO sammendrag (element_id, tekst, prompt_versjon, opprettet) "
            "VALUES (?, 'Testsammendrag.', 'v1', '2026-04-24T10:01:00')",
            (element_id,),
        )
        sammendrag_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    return db_sti, element_id, sammendrag_id


# ---------------------------------------------------------------------------
# Test 1: Triplet skrives og leses korrekt
# ---------------------------------------------------------------------------


def test_skriv_og_les(db_med_sammendrag: tuple[Path, int, int]):
    """Triplet skrives korrekt og kan hentes tilbake via filtrer_pa_komponent."""
    db_sti, element_id, sammendrag_id = db_med_sammendrag

    ny_id = lagre_triplet(
        db_sti=db_sti,
        element_id=element_id,
        resultat_id=sammendrag_id,
        godkjent=True,
        kommentar="Ser bra ut.",
        komponent="sammendrag",
    )

    assert ny_id is not None and ny_id > 0

    triplets = filtrer_pa_komponent(db_sti, "sammendrag")
    assert len(triplets) == 1

    t = triplets[0]
    assert t["element_id"] == element_id
    assert t["resultat_id"] == sammendrag_id
    assert t["godkjent"] == 1
    assert t["kommentar"] == "Ser bra ut."
    assert t["komponent"] == "sammendrag"


# ---------------------------------------------------------------------------
# Test 2: Godkjenningsrate og antall avviste beregnes korrekt
# ---------------------------------------------------------------------------


def test_godkjenningsrate_og_avviste(db_med_sammendrag: tuple[Path, int, int]):
    """Statistikk er korrekt ved 2 godkjente og 1 avvist triplet."""
    db_sti, element_id, sammendrag_id = db_med_sammendrag

    # Legg til to ekstra elementer med sammendrag
    with sqlite3.connect(db_sti) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for i in range(2):
            conn.execute(
                "INSERT INTO elementer (kilde_id, guid, url, tittel, hentet) "
                f"VALUES (1, 'guid-stat-{i}', 'https://example.com/stat{i}', 'Art{i}', '2026-04-24T10:00:00')"
            )
            eid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO sammendrag (element_id, tekst, prompt_versjon, opprettet) "
                "VALUES (?, 'Tekst.', 'v1', '2026-04-24T10:01:00')",
                (eid,),
            )
            sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            # Lagre element_id og sammendrag_id midlertidig
            if i == 0:
                extra_eid_0, extra_sid_0 = eid, sid
            else:
                extra_eid_1, extra_sid_1 = eid, sid

    # 2 godkjente, 1 avvist
    lagre_triplet(db_sti, element_id, sammendrag_id, godkjent=True, kommentar=None)
    lagre_triplet(db_sti, extra_eid_0, extra_sid_0, godkjent=True, kommentar=None)
    lagre_triplet(db_sti, extra_eid_1, extra_sid_1, godkjent=False, kommentar="Mangelfull")

    stats = beregn_statistikk(db_sti, "sammendrag")

    assert stats["totalt"] == 3
    assert stats["antall_avviste"] == 1
    assert abs(stats["godkjenningsrate"] - 2 / 3) < 0.001


# ---------------------------------------------------------------------------
# Test 3: Filtrering på komponent
# ---------------------------------------------------------------------------


def test_filtrering_pa_komponent(db_med_sammendrag: tuple[Path, int, int]):
    """filtrer_pa_komponent returnerer kun triplets for riktig komponent."""
    db_sti, element_id, sammendrag_id = db_med_sammendrag

    # Lagre én "sammendrag"- og én "dommer_validering"-triplet
    lagre_triplet(db_sti, element_id, sammendrag_id, godkjent=True, kommentar=None, komponent="sammendrag")
    lagre_triplet(db_sti, element_id, sammendrag_id, godkjent=False, kommentar=None, komponent="dommer_validering")

    sammendrag_triplets = filtrer_pa_komponent(db_sti, "sammendrag")
    dommer_triplets = filtrer_pa_komponent(db_sti, "dommer_validering")

    assert len(sammendrag_triplets) == 1
    assert sammendrag_triplets[0]["komponent"] == "sammendrag"

    assert len(dommer_triplets) == 1
    assert dommer_triplets[0]["komponent"] == "dommer_validering"


# ---------------------------------------------------------------------------
# Test 4: Duplikat håndteres korrekt
# ---------------------------------------------------------------------------


def test_duplikat_handteres(db_med_sammendrag: tuple[Path, int, int]):
    """er_duplikat() returnerer True etter første innsending, False før."""
    db_sti, element_id, sammendrag_id = db_med_sammendrag

    assert er_duplikat(db_sti, element_id, "sammendrag") is False

    lagre_triplet(db_sti, element_id, sammendrag_id, godkjent=True, kommentar=None)

    assert er_duplikat(db_sti, element_id, "sammendrag") is True
