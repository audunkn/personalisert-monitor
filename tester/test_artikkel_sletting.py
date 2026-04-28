"""Enhetstester for automatisk opprydning når .md-filer slettes fra vault/artikler/.

Verifiserer fire kritiske egenskaper:
1. Artikkel med bilder: slett .md → bilder borte, ingen DB-rad.
2. Artikkel uten bilder (NULL bilder_json): slett .md → DB-rad borte, ingen feil.
3. .md-fil uten tilhørende DB-rad: ingen feil.
4. lagre_artikkel() med bilder: bilder_json er satt i DB.

Alle tester bruker midlertidige mapper og mock slik at de kjøres
raskt og uten nettverkskall eller ekstern infrastruktur.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from intelligence_monitor.innhenter import obsidian_vakt, vault_skriver

# Importer delte fixtures — pytest registrerer dem automatisk ved import
from tester.konfig.fixtures import db_sti, vault_rot  # noqa: F401

_KILDE_ID = 1


# ---------------------------------------------------------------------------
# Hjelpere
# ---------------------------------------------------------------------------


def _sett_inn_element(db_sti: Path, vault_sti: str, bilder_json: str | None = None) -> int:
    """Setter inn en testelement i elementer-tabellen og returnerer id."""
    with sqlite3.connect(db_sti) as con:
        rad = con.execute(
            """
            INSERT INTO elementer
                (kilde_id, guid, url, tittel, publisert, hentet, vault_sti, bilder_json)
            VALUES (1, ?, ?, 'Testittel', NULL, '2026-04-23T10:00:00+00:00', ?, ?)
            RETURNING id
            """,
            (f"test-guid-{vault_sti}", f"https://eksempel.no/{vault_sti}", vault_sti, bilder_json),
        ).fetchone()
    return int(rad[0])


# ---------------------------------------------------------------------------
# Tester
# ---------------------------------------------------------------------------


def test_slett_artikkel_fjerner_bilder(vault_rot: Path, db_sti: Path) -> None:
    """Artikkel med bilder: slett .md → bilder borte, ingen DB-rad."""
    bilde_mappe = vault_rot / "ressurser" / "bilder"
    bilde1 = bilde_mappe / "abc12345.jpg"
    bilde2 = bilde_mappe / "def67890.png"
    bilde1.write_bytes(b"fake-bilde-1")
    bilde2.write_bytes(b"fake-bilde-2")

    bilder_json = json.dumps(["abc12345.jpg", "def67890.png"])
    vault_sti = "artikler/abcd1234-test-artikkel.md"
    _sett_inn_element(db_sti, vault_sti, bilder_json)

    obsidian_vakt._rydd_etter_slettet_artikkel(db_sti, vault_rot, vault_sti)

    assert not bilde1.exists(), "Bilde 1 skal være slettet"
    assert not bilde2.exists(), "Bilde 2 skal være slettet"
    with sqlite3.connect(db_sti) as con:
        rad = con.execute(
            "SELECT id FROM elementer WHERE vault_sti = ?", (vault_sti,)
        ).fetchone()
    assert rad is None, "DB-rad skal være slettet"


def test_slett_artikkel_uten_bilder(vault_rot: Path, db_sti: Path) -> None:
    """Artikkel uten bilder (NULL bilder_json): slett .md → DB-rad borte, ingen feil."""
    vault_sti = "artikler/xyz99999-ingen-bilder.md"
    _sett_inn_element(db_sti, vault_sti, bilder_json=None)

    obsidian_vakt._rydd_etter_slettet_artikkel(db_sti, vault_rot, vault_sti)

    with sqlite3.connect(db_sti) as con:
        rad = con.execute(
            "SELECT id FROM elementer WHERE vault_sti = ?", (vault_sti,)
        ).fetchone()
    assert rad is None, "DB-rad skal være slettet selv uten bilder"


def test_slett_ukjent_fil_ignoreres(vault_rot: Path, db_sti: Path) -> None:
    """.md-fil uten tilhørende DB-rad: ingen feil."""
    vault_sti = "artikler/ukjent-fil-finnes-ikke-i-db.md"

    # Skal ikke kaste exception
    obsidian_vakt._rydd_etter_slettet_artikkel(db_sti, vault_rot, vault_sti)


def test_slett_artikkel_fjerner_sammendrag_og_triplets(vault_rot: Path, db_sti: Path) -> None:
    """Kaskadesletting: slett .md → sammendrag og evalueringstriplets borte, ingen feil."""
    vault_sti = "artikler/kaskade-test.md"
    element_id = _sett_inn_element(db_sti, vault_sti)

    with sqlite3.connect(db_sti) as con:
        sammendrag_id = con.execute(
            """
            INSERT INTO sammendrag (element_id, tekst, prompt_versjon, opprettet)
            VALUES (?, 'Testsammendrag', 'v1', '2026-04-28T10:00:00+00:00')
            RETURNING id
            """,
            (element_id,),
        ).fetchone()[0]
        con.execute(
            """
            INSERT INTO evalueringstriplets
                (element_id, resultat_id, komponent, tidsstempel)
            VALUES (?, ?, 'sammendrag', '2026-04-28T10:00:00+00:00')
            """,
            (element_id, sammendrag_id),
        )

    obsidian_vakt._rydd_etter_slettet_artikkel(db_sti, vault_rot, vault_sti)

    with sqlite3.connect(db_sti) as con:
        assert con.execute(
            "SELECT COUNT(*) FROM sammendrag WHERE element_id = ?", (element_id,)
        ).fetchone()[0] == 0, "Sammendrag skal være slettet"
        assert con.execute(
            "SELECT COUNT(*) FROM evalueringstriplets WHERE element_id = ?", (element_id,)
        ).fetchone()[0] == 0, "Evalueringstriplets skal være slettet"


def test_bilder_json_lagres_ved_opprettelse(vault_rot: Path, db_sti: Path, mocker) -> None:
    """lagre_artikkel() med bilder: bilder_json er satt korrekt i DB."""
    mocker.patch(
        "intelligence_monitor.innhenter.vault_skriver._last_ned_bilde",
        return_value="../ressurser/bilder/testbilde.jpg",
    )

    element_id = vault_skriver.lagre_artikkel(
        kilde_id=_KILDE_ID,
        url="https://eksempel.no/med-bilder",
        tittel="Artikkel med bilder",
        innhold="![bilde](https://eksempel.no/bilde.jpg)",
        publisert=None,
        kildetype="manuell",
        db_sti=db_sti,
        vault_rot=vault_rot,
    )

    with sqlite3.connect(db_sti) as con:
        rad = con.execute(
            "SELECT bilder_json FROM elementer WHERE guid = ?", (element_id,)
        ).fetchone()

    assert rad is not None, "Ingen rad funnet i elementer"
    bildefilnavn = json.loads(rad[0])
    assert bildefilnavn == ["testbilde.jpg"], (
        f"Forventet ['testbilde.jpg'], fikk: {bildefilnavn!r}"
    )
