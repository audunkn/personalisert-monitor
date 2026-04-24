"""Enhetstester for src/intelligence_monitor/sammendrag/lag_sammendrag.py.

Dekker fem kritiske grener:
1. XML-innramming er korrekt formatert.
2. Tekst over MAKS_ARTIKKEL_TOKENS kuttes riktig.
3. prompt_versjon lagres korrekt i SQLite.
4. regulatorisk-kontekst.md inkluderes i brukermelding til API.
5. Manglende vault-fil gir FileNotFoundError med meningsfull melding.

Alle tester bruker mock for OpenAI-kallet og midlertidig SQLite.
Ingen nettverkskall.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from intelligence_monitor.sammendrag.lag_sammendrag import (
    PROMPT_VERSJON,
    _bygg_brukermelding,
    _kutt_til_tokens,
    _les_artikkeltekst,
    _les_regulatorisk_kontekst,
    lag_alle_sammendrag,
)
from tester.konfig.fixtures import db_sti, vault_rot  # noqa: F401


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def prompts_mappe(tmp_path: Path) -> Path:
    """Midlertidig prompts-mappe med en minimal v1.txt."""
    mappe = tmp_path / "prompts"
    mappe.mkdir()
    (mappe / "v1.txt").write_text(
        "Du er en redaktør.\n\nArtikkel:\n[LIM INN ARTIKKEL]",
        encoding="utf-8",
    )
    return mappe


@pytest.fixture()
def specs_mappe(tmp_path: Path) -> Path:
    """Midlertidig specs-mappe med regulatorisk-kontekst.md."""
    mappe = tmp_path / "specs"
    mappe.mkdir()
    (mappe / "regulatorisk-kontekst.md").write_text(
        "## EU AI Act\nRisikobasert tilnærming.",
        encoding="utf-8",
    )
    return mappe


@pytest.fixture()
def db_med_element(db_sti: Path, vault_rot: Path) -> tuple[Path, int]:
    """Database med én kilde og ett element som mangler sammendrag.

    Returns:
        (db_sti, element_id) — sti til testdatabasen og elementets id.
    """
    artikkel_fil = vault_rot / "artikler" / "test-artikkel.md"
    artikkel_fil.write_text(
        "---\nelement_id: abc\nurl: https://example.com\nkildetype: rss\n---\n\n# Tittel\n\nInnhold her.",
        encoding="utf-8",
    )
    vault_sti = "artikler/test-artikkel.md"

    with sqlite3.connect(db_sti) as conn:
        conn.execute(
            "INSERT INTO elementer (kilde_id, guid, url, tittel, hentet, vault_sti) VALUES (1, 'guid-1', 'https://example.com', 'Tittel', '2026-04-24T00:00:00', ?)",
            (vault_sti,),
        )
        element_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    return db_sti, element_id


# ---------------------------------------------------------------------------
# Test 1: XML-innramming
# ---------------------------------------------------------------------------


def test_xml_innramming_korrekt_formatert():
    """<artikkel>-taggen omslutter artikkelteksten i brukermelding."""
    prompt = "Instruksjon.\n\nArtikkel:\n[LIM INN ARTIKKEL]"
    melding = _bygg_brukermelding(prompt, "Artikkelteksten her.", "")

    assert "<artikkel>" in melding
    assert "Artikkelteksten her." in melding
    assert "</artikkel>" in melding
    # Bekrefter at taggen omslutter innholdet (ikke bare finnes begge steder)
    start = melding.index("<artikkel>")
    slutt = melding.index("</artikkel>")
    assert "Artikkelteksten her." in melding[start:slutt]


# ---------------------------------------------------------------------------
# Test 2: Tekst over grensen kuttes
# ---------------------------------------------------------------------------


def test_kutt_til_tokens_kutter_lang_tekst():
    """Tekst over MAKS_ARTIKKEL_TOKENS kuttes til omtrent riktig lengde."""
    maks = 100  # 100 tokens ≈ 400 tegn
    lang_tekst = "A" * 500  # godt over grensen

    kuttet = _kutt_til_tokens(lang_tekst, maks)

    assert len(kuttet) <= maks * 4
    assert len(kuttet) > 0


def test_kutt_til_tokens_bevar_kort_tekst():
    """Tekst innenfor grensen returneres uendret."""
    kort_tekst = "Kort tekst."
    assert _kutt_til_tokens(kort_tekst, 100) == kort_tekst


# ---------------------------------------------------------------------------
# Test 3: prompt_versjon lagres korrekt
# ---------------------------------------------------------------------------


def test_prompt_versjon_lagres_korrekt(
    db_med_element: tuple[Path, int],
    prompts_mappe: Path,
    specs_mappe: Path,
    vault_rot: Path,
):
    """Sammendrag lagres i SQLite med korrekt prompt_versjon."""
    db_sti, _ = db_med_element

    mock_respons = MagicMock()
    mock_respons.choices[0].message.content = "Testsammendrag."

    with patch("intelligence_monitor.sammendrag.lag_sammendrag.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_respons
        lag_alle_sammendrag(
            db_sti=db_sti,
            vault_rot=vault_rot,
            prompts_mappe=prompts_mappe,
            specs_mappe=specs_mappe,
        )

    with sqlite3.connect(db_sti) as conn:
        rad = conn.execute("SELECT tekst, prompt_versjon FROM sammendrag").fetchone()

    assert rad is not None
    assert rad[0] == "Testsammendrag."
    assert rad[1] == PROMPT_VERSJON


# ---------------------------------------------------------------------------
# Test 4: regulatorisk-kontekst.md inkluderes i brukermelding
# ---------------------------------------------------------------------------


def test_regulatorisk_kontekst_inkluderes_i_brukermelding(specs_mappe: Path):
    """Innholdet fra regulatorisk-kontekst.md er med i brukermelding til API."""
    regulatorisk = _les_regulatorisk_kontekst(specs_mappe)
    prompt = "Instruksjon.\n\nArtikkel:\n[LIM INN ARTIKKEL]"
    melding = _bygg_brukermelding(prompt, "Artikkeltekst.", regulatorisk)

    assert "EU AI Act" in melding
    assert "<kontekst>" in melding
    assert "</kontekst>" in melding


# ---------------------------------------------------------------------------
# Test 5: Manglende vault-fil gir FileNotFoundError
# ---------------------------------------------------------------------------


def test_manglende_vault_fil_gir_feilmelding(vault_rot: Path):
    """FileNotFoundError kastes med meningsfull melding når vault-fil mangler."""
    with pytest.raises(FileNotFoundError, match="Vault-fil ikke funnet"):
        _les_artikkeltekst(vault_rot, "artikler/finnes-ikke.md")
