"""Integrasjonstest: obsidian_vakt prosesserer pre-eksisterende innboks-filer ved oppstart.

Verifiserer at start() sin oppstartsskanning plukker opp filer som allerede
lå i innboks/ da vakten ble startet — ikke bare filer som opprettes etterpå.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from intelligence_monitor.innhenter import obsidian_vakt
import intelligence_monitor.innhenter.vault_skriver as vault_skriver_modul

# Importer delte fixtures — pytest registrerer dem automatisk ved import
from tester.konfig.fixtures import db_sti, vault_rot  # noqa: F401


# ---------------------------------------------------------------------------
# Hjelpere
# ---------------------------------------------------------------------------


def _hent_element_url(db_sti: Path, url: str) -> tuple | None:
    """Returnerer (guid, tittel, url) fra elementer eller None."""
    with sqlite3.connect(db_sti) as con:
        return con.execute(
            "SELECT guid, tittel, url FROM elementer WHERE url = ?", (url,)
        ).fetchone()


def _lag_md_fil(innboks: Path, filnavn: str, url: str, tittel: str = "Testtittel") -> Path:
    """Lager en minimal Obsidian-klippet .md-fil i innboks/."""
    innhold = f"""---
title: {tittel}
url: {url}
---

# {tittel}

Testinnhold for oppstartstest.
"""
    fil = innboks / filnavn
    fil.write_text(innhold, encoding="utf-8")
    return fil


# ---------------------------------------------------------------------------
# Tester
# ---------------------------------------------------------------------------


def test_oppstart_prosesserer_eksisterende_md(vault_rot: Path, db_sti: Path, monkeypatch) -> None:
    """Pre-eksisterende .md-fil i innboks/ prosesseres ved oppstartsskanning.

    Verifiserer:
    - Filen lå i innboks/ FØR oppstartsskanningen kjøres.
    - Etter skanning finnes en rad i elementer-tabellen.
    - Filen er flyttet til behandlet/.
    """
    monkeypatch.setattr(
        vault_skriver_modul,
        "_behandle_bilder",
        lambda innhold, vault_rot: (innhold, []),
    )

    innboks = vault_rot / "innboks"
    url = "https://eksempel.no/artikkel-oppstart"
    _lag_md_fil(innboks, "artikkel-oppstart.md", url)

    # Kall oppstartsskanningen direkte — samme logikk som i start()
    handler = obsidian_vakt._InnboksHandler(db_sti=db_sti, vault_rot=vault_rot)
    for fil in sorted(innboks.iterdir()):
        if fil.suffix == ".md":
            handler._prosesser(fil)
        elif fil.suffix == ".pdf":
            handler._prosesser_pdf(fil)

    rad = _hent_element_url(db_sti, url)
    assert rad is not None, f"Forventet rad i elementer for url={url!r}"
    assert (vault_rot / "behandlet" / "artikkel-oppstart.md").exists(), (
        "Filen skal være flyttet til behandlet/"
    )


def test_oppstart_dedup_hopper_over_kjent_url(vault_rot: Path, db_sti: Path, monkeypatch) -> None:
    """Fil med allerede kjent URL hoppes over ved oppstartsskanning — ingen duplikat.

    Verifiserer at dedupliseringslogikken i _prosesser() fungerer ved oppstart,
    slik at vakten er trygg å restarte uten å lage dobbeltoppføringer.
    """
    monkeypatch.setattr(
        vault_skriver_modul,
        "_behandle_bilder",
        lambda innhold, vault_rot: (innhold, []),
    )

    innboks = vault_rot / "innboks"
    url = "https://eksempel.no/duplikat-oppstart"
    _lag_md_fil(innboks, "duplikat-oppstart.md", url)

    handler = obsidian_vakt._InnboksHandler(db_sti=db_sti, vault_rot=vault_rot)

    # Første skann — lagrer filen
    for fil in sorted(innboks.iterdir()):
        if fil.suffix == ".md":
            handler._prosesser(fil)

    # Legg inn ny fil med samme URL (simulerer restart med fil tilbake i innboks)
    _lag_md_fil(innboks, "duplikat-oppstart.md", url)

    # Andre skann — skal hoppe over
    for fil in sorted(innboks.iterdir()):
        if fil.suffix == ".md":
            handler._prosesser(fil)

    with sqlite3.connect(db_sti) as con:
        antall = con.execute(
            "SELECT COUNT(*) FROM elementer WHERE url = ?", (url,)
        ).fetchone()[0]
    assert antall == 1, f"Forventet 1 rad etter duplikat-skann, fant {antall}"
