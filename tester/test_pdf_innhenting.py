"""Enhetstester for PDF-innhenting via vault innboks.

Verifiserer fire kritiske egenskaper:
1. Gyldig PDF med tekst lagres korrekt i vault og SQLite.
2. Tittel hentes fra PDF-metadata (/Title) hvis tilgjengelig.
3. Duplikat PDF (samme filnavn) hoppes over — ingen ny rad.
4. PDF uten tekst hoppes over med WARNING-logg.

Alle tester bruker tmp_path og pypdf.PdfWriter for å lage test-PDFer
programmatisk uten filer på disk utover det pytest håndterer.
"""

from __future__ import annotations

import io
import logging
import sqlite3
from pathlib import Path

import pypdf
import pytest

from intelligence_monitor.innhenter import obsidian_vakt

# Importer delte fixtures — pytest registrerer dem automatisk ved import
from tester.konfig.fixtures import db_sti, vault_rot  # noqa: F401


# ---------------------------------------------------------------------------
# Hjelpere
# ---------------------------------------------------------------------------


def _lag_pdf_bytes(tekst: str = "Testinnhold fra PDF.", tittel: str | None = None) -> bytes:
    """Lager en minimal PDF i minnet med valgfri /Title-metadata."""
    skriver = pypdf.PdfWriter()
    skriver.add_blank_page(width=595, height=842)

    # Legg tekst på første side via annotasjon (enkleste måte uten ekstra deps)
    # For testformål: bruk metadata for tittel og patch extract_text
    if tittel:
        skriver.add_metadata({"/Title": tittel})

    buf = io.BytesIO()
    skriver.write(buf)
    return buf.getvalue()


def _legg_pdf_kilde(db_sti: Path) -> int:
    """Setter inn manuell-pdf-kilde i testdatabasen og returnerer kilde_id."""
    with sqlite3.connect(db_sti) as con:
        rad = con.execute(
            "INSERT INTO kilder (navn, url, type) VALUES ('manuell-pdf', 'lokal', 'pdf') RETURNING id"
        ).fetchone()
    return int(rad[0])


def _hent_element_rad(db_sti: Path, url: str) -> tuple | None:
    """Returnerer (guid, tittel, url) fra elementer eller None."""
    with sqlite3.connect(db_sti) as con:
        return con.execute(
            "SELECT guid, tittel, url FROM elementer WHERE url = ?", (url,)
        ).fetchone()


# ---------------------------------------------------------------------------
# Tester
# ---------------------------------------------------------------------------


def test_pdf_lagres_korrekt(vault_rot: Path, db_sti: Path, mocker) -> None:
    """Gyldig PDF med tekst → rad i elementer, fil i behandlet/.

    Verifiserer:
    - En rad med korrekt url (pdf://{stem}) finnes i elementer-tabellen.
    - PDF-filen er flyttet til behandlet/.
    - .md-fil er skrevet til vault/artikler/.
    """
    _legg_pdf_kilde(db_sti)

    innboks = vault_rot / "innboks"
    pdf_fil = innboks / "testartikkel.pdf"
    pdf_fil.write_bytes(_lag_pdf_bytes())

    # patch extract_text for å returnere tekst (blank_page gir ingen faktisk tekst)
    mocker.patch(
        "pypdf.PageObject.extract_text",
        return_value="Testinnhold fra PDF.",
    )
    mocker.patch(
        "intelligence_monitor.innhenter.vault_skriver._behandle_bilder",
        side_effect=lambda innhold, vault_rot: (innhold, []),
    )

    handler = obsidian_vakt._InnboksHandler(db_sti=db_sti, vault_rot=vault_rot)
    handler._prosesser_pdf(pdf_fil)

    rad = _hent_element_rad(db_sti, "pdf://testartikkel")
    assert rad is not None, "Ingen rad funnet i elementer for PDF"
    assert rad[2] == "pdf://testartikkel"

    assert (vault_rot / "behandlet" / "testartikkel.pdf").exists(), "PDF skal være i behandlet/"
    filer = list((vault_rot / "artikler").glob("*.md"))
    assert len(filer) == 1, f"Forventet 1 .md-fil i artikler/, fant {len(filer)}"


def test_pdf_tittel_fra_metadata(vault_rot: Path, db_sti: Path, mocker) -> None:
    """PDF med /Title i metadata → tittel hentes fra metadata, ikke filnavn.

    Verifiserer at tittelfeltet i elementer-tabellen matcher metadata-tittelen.
    """
    _legg_pdf_kilde(db_sti)

    innboks = vault_rot / "innboks"
    pdf_fil = innboks / "rapport-2026.pdf"
    pdf_fil.write_bytes(_lag_pdf_bytes(tittel="Årsrapport 2026"))

    mocker.patch(
        "pypdf.PageObject.extract_text",
        return_value="Innhold i årsrapporten.",
    )
    mocker.patch(
        "intelligence_monitor.innhenter.vault_skriver._behandle_bilder",
        side_effect=lambda innhold, vault_rot: (innhold, []),
    )

    handler = obsidian_vakt._InnboksHandler(db_sti=db_sti, vault_rot=vault_rot)
    handler._prosesser_pdf(pdf_fil)

    rad = _hent_element_rad(db_sti, "pdf://rapport-2026")
    assert rad is not None, "Ingen rad funnet i elementer"
    assert rad[1] == "Årsrapport 2026", f"Forventet tittel fra metadata, fikk: {rad[1]!r}"


def test_pdf_duplikat_hoppes_over(vault_rot: Path, db_sti: Path, mocker) -> None:
    """Samme PDF lagt inn to ganger → kun én rad i elementer.

    Verifiserer at duplikater basert på filnavn-dedupnøkkel ikke lagres to ganger.
    """
    _legg_pdf_kilde(db_sti)

    innboks = vault_rot / "innboks"
    pdf_fil = innboks / "duplikat.pdf"
    pdf_fil.write_bytes(_lag_pdf_bytes())

    mocker.patch(
        "pypdf.PageObject.extract_text",
        return_value="Innhold.",
    )
    mocker.patch(
        "intelligence_monitor.innhenter.vault_skriver._behandle_bilder",
        side_effect=lambda innhold, vault_rot: (innhold, []),
    )

    handler = obsidian_vakt._InnboksHandler(db_sti=db_sti, vault_rot=vault_rot)
    handler._prosesser_pdf(pdf_fil)

    # Legg inn ny fil med samme navn for andre kjøring
    pdf_fil2 = innboks / "duplikat.pdf"
    pdf_fil2.write_bytes(_lag_pdf_bytes())
    handler._prosesser_pdf(pdf_fil2)

    with sqlite3.connect(db_sti) as con:
        antall = con.execute(
            "SELECT COUNT(*) FROM elementer WHERE url = 'pdf://duplikat'"
        ).fetchone()[0]
    assert antall == 1, f"Forventet 1 rad, fant {antall}"


def test_pdf_uten_tekst_hoppes_over(vault_rot: Path, db_sti: Path, mocker, caplog) -> None:
    """PDF med tom tekst → ingen rad i elementer, WARNING logges.

    Verifiserer at skannede PDFer uten digitalt tekstlag ikke lagres.
    """
    _legg_pdf_kilde(db_sti)

    innboks = vault_rot / "innboks"
    pdf_fil = innboks / "skannet.pdf"
    pdf_fil.write_bytes(_lag_pdf_bytes())

    mocker.patch(
        "pypdf.PageObject.extract_text",
        return_value="",
    )

    handler = obsidian_vakt._InnboksHandler(db_sti=db_sti, vault_rot=vault_rot)

    with caplog.at_level(logging.WARNING, logger="intelligence_monitor.innhenter.obsidian_vakt"):
        handler._prosesser_pdf(pdf_fil)

    rad = _hent_element_rad(db_sti, "pdf://skannet")
    assert rad is None, "Skannet PDF uten tekst skal ikke lagres"

    advarsler = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert advarsler, "Forventet minst én WARNING for PDF uten tekst"
