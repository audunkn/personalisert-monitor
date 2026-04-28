"""Enhetstester for src/intelligence_monitor/innhenter/vault_skriver.py.

Verifiserer fire kritiske egenskaper:
1. Korrekt filnavn (UUID8-prefix + slug) og YAML-frontmatter.
2. UUID i frontmatter matcher element_id i SQLite.
3. Ugyldig bilde-URL gir WARNING uten krasj.
4. Rollback — filen slettes hvis SQLite-skriving feiler.

Alle tester bruker midlertidige mapper og mock slik at de kjøres
raskt og uten nettverkskall eller ekstern infrastruktur.
"""

from __future__ import annotations

import logging
import sqlite3

import pytest

from intelligence_monitor.innhenter import vault_skriver

# Importer delte fixtures — pytest registrerer dem automatisk ved import
from tester.konfig.fixtures import db_sti, vault_rot  # noqa: F401

# kilde_id = 1 er alltid manuell-klipp i testdatabasen (første INSERT)
_KILDE_ID = 1


# ---------------------------------------------------------------------------
# Tester
# ---------------------------------------------------------------------------


def test_filnavn_og_frontmatter(vault_rot, db_sti, mocker) -> None:
    """lagre_artikkel() produserer korrekt filnavn og YAML-frontmatter.

    Verifiserer:
    - Filnavnet starter med 8 hex-tegn (uuid_kort) etterfulgt av bindestreker og slug.
    - Frontmatter inneholder element_id, url, kildetype og klippet_dato.
    """
    # Hopp over bildehåndtering — ikke relevant for denne testen
    mocker.patch(
        "intelligence_monitor.innhenter.vault_skriver._behandle_bilder",
        side_effect=lambda innhold, vault_rot, base_url="": (innhold, []),
    )

    element_id = vault_skriver.lagre_artikkel(
        kilde_id=_KILDE_ID,
        url="https://eksempel.no/test-artikkel",
        tittel="Test Artikkel Årets Beste",
        innhold="Innholdstekst.",
        publisert="2026-04-22",
        kildetype="manuell",
        db_sti=db_sti,
        vault_rot=vault_rot,
        klippet_dato="2026-04-22",
    )

    filer = list((vault_rot / "artikler").glob("*.md"))
    assert len(filer) == 1, f"Forventet 1 fil i artikler/, fant {len(filer)}"

    filnavn = filer[0].name
    prefix = filnavn.split("-")[0]
    assert len(prefix) == 8 and all(
        c in "0123456789abcdef" for c in prefix
    ), f"Filnavnet skal starte med 8 hex-tegn, fikk: {prefix!r}"

    innhold = filer[0].read_text(encoding="utf-8")
    assert f"element_id: {element_id}" in innhold
    assert "url: https://eksempel.no/test-artikkel" in innhold
    assert "kildetype: manuell" in innhold
    assert "klippet_dato: 2026-04-22" in innhold


def test_element_id_konsistens(vault_rot, db_sti, mocker) -> None:
    """UUID i frontmatter skal matche guid i SQLite-raden.

    Verifiserer at element_id returnert fra lagre_artikkel(),
    skrevet i frontmatter og lagret i elementer.guid er identiske.
    """
    mocker.patch(
        "intelligence_monitor.innhenter.vault_skriver._behandle_bilder",
        side_effect=lambda innhold, vault_rot, base_url="": (innhold, []),
    )

    element_id = vault_skriver.lagre_artikkel(
        kilde_id=_KILDE_ID,
        url="https://eksempel.no/konsistens",
        tittel="Konsistenstest",
        innhold="",
        publisert=None,
        kildetype="manuell",
        db_sti=db_sti,
        vault_rot=vault_rot,
        klippet_dato="2026-04-22",
    )

    # Verifiser SQLite
    with sqlite3.connect(db_sti) as con:
        rad = con.execute(
            "SELECT guid FROM elementer WHERE guid = ?", (element_id,)
        ).fetchone()
    assert rad is not None, "Ingen rad funnet i SQLite for returnert element_id"
    assert rad[0] == element_id, f"SQLite guid {rad[0]!r} != element_id {element_id!r}"

    # Verifiser frontmatter
    fil = next((vault_rot / "artikler").glob("*.md"))
    assert f"element_id: {element_id}" in fil.read_text(encoding="utf-8")


def test_ugyldig_bilde_url(vault_rot, db_sti, caplog) -> None:
    """Ugyldig bilde-URL (ikke http/https) gir WARNING og krasjer ikke.

    Verifiserer at:
    - lagre_artikkel() returnerer uten unntak.
    - Minst én WARNING er logget av vault_skriver-modulen.
    """
    with caplog.at_level(
        logging.WARNING, logger="intelligence_monitor.innhenter.vault_skriver"
    ):
        element_id = vault_skriver.lagre_artikkel(
            kilde_id=_KILDE_ID,
            url="https://eksempel.no/bilde-test",
            tittel="Bildetest",
            innhold="![bilde](ftp://ugyldig-protokoll/bilde.png)",
            publisert=None,
            kildetype="manuell",
            db_sti=db_sti,
            vault_rot=vault_rot,
        )

    assert element_id is not None, "lagre_artikkel() skal returnere element_id ved ugyldig bilde-URL"
    advarsler = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert advarsler, "Forventet minst én WARNING for ugyldig bilde-URL"


def test_rollback(vault_rot, db_sti, mocker) -> None:
    """Feil i SQLite-skriving skal slette .md-filen fra vault (rollback).

    Verifiserer at artikler/-mappen er tom etter en simulert SQLite-feil.
    """
    mocker.patch(
        "intelligence_monitor.innhenter.vault_skriver._behandle_bilder",
        side_effect=lambda innhold, vault_rot, base_url="": (innhold, []),
    )
    mocker.patch(
        "intelligence_monitor.innhenter.vault_skriver._skriv_til_db",
        side_effect=sqlite3.OperationalError("simulert SQLite-feil"),
    )

    with pytest.raises(sqlite3.OperationalError):
        vault_skriver.lagre_artikkel(
            kilde_id=_KILDE_ID,
            url="https://eksempel.no/rollback",
            tittel="Rollback Test",
            innhold="",
            publisert=None,
            kildetype="manuell",
            db_sti=db_sti,
            vault_rot=vault_rot,
        )

    filer = list((vault_rot / "artikler").glob("*.md"))
    assert len(filer) == 0, (
        f"Filen skal være slettet ved rollback, fant {len(filer)} fil(er)"
    )
