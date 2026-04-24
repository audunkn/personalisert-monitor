"""Sammendragsmodul — genererer norskspråklige sammendrag via OpenAI API.

Henter artikler fra SQLite som mangler sammendrag, leser artikkeltekst fra
Obsidian-vault, kombinerer med regulatorisk kontekst og versjonert prompt,
kaller OpenAI API og lagrer resultatet i sammendrag-tabellen.

Kjøres via: make sammendrag
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Konfigurasjon fra .env
# ---------------------------------------------------------------------------

_OPENAI_MODELL = os.getenv("OPENAI_MODELL", "gpt-4.1")
_MAKS_SAMMENDRAG_TOKENS = int(os.getenv("MAKS_SAMMENDRAG_TOKENS", "1024"))
_TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
_MAKS_ARTIKKEL_TOKENS = int(os.getenv("MAKS_ARTIKKEL_TOKENS", "4000"))
_DATABASE_STI = Path(os.getenv("DATABASE_STI", "data/monitor.db"))
_VAULT_ROT = Path(os.getenv("VAULT_ROT", ""))

PROMPT_VERSJON = "v1"

# ---------------------------------------------------------------------------
# Opik-konfigurasjon (fail_silently — feil i sporing stopper ikke kjøring)
# ---------------------------------------------------------------------------

try:
    import opik

    opik.configure(
        api_key=os.getenv("OPIK_API_NØKKEL"),
        workspace=os.getenv("OPIK_ARBEIDSROM"),
        project_name=os.getenv("OPIK_PROSJEKTNAVN", "intelligence-monitor"),
        force=True,
        automatic_approvals=True,
    )
    _OPIK_TILGJENGELIG = True
except Exception as _opik_feil:
    logger.warning("Opik ikke tilgjengelig — sporing deaktivert: %s", _opik_feil)
    _OPIK_TILGJENGELIG = False


# ---------------------------------------------------------------------------
# Interne hjelpefunksjoner
# ---------------------------------------------------------------------------


def _les_prompt(prompts_mappe: Path) -> str:
    """Leser aktiv prompt fra fil.

    Args:
        prompts_mappe: Mappe med prompt-tekstfiler (f.eks. v1.txt).

    Returns:
        Prompt-tekst som streng.

    Raises:
        FileNotFoundError: Hvis prompt-filen ikke finnes.
    """
    prompt_fil = prompts_mappe / f"{PROMPT_VERSJON}.txt"
    if not prompt_fil.exists():
        raise FileNotFoundError(f"Prompt ikke funnet: {prompt_fil}")
    return prompt_fil.read_text(encoding="utf-8")


def _les_regulatorisk_kontekst(specs_mappe: Path) -> str:
    """Leser regulatorisk-kontekst.md som oppslagsverk for summarizeren.

    Args:
        specs_mappe: Sti til specs/-mappen.

    Returns:
        Innhold som streng, eller tom streng hvis filen ikke finnes.
    """
    kontekst_fil = specs_mappe / "regulatorisk-kontekst.md"
    if not kontekst_fil.exists():
        logger.warning("regulatorisk-kontekst.md ikke funnet: %s", kontekst_fil)
        return ""
    return kontekst_fil.read_text(encoding="utf-8")


def _les_artikkeltekst(vault_rot: Path, vault_sti: str) -> str:
    """Leser artikkeltekst fra vault-fil og fjerner YAML-frontmatter.

    Args:
        vault_rot: Rot-mappe for Obsidian-vault.
        vault_sti: Relativ sti fra vault_rot til artikkelens .md-fil.

    Returns:
        Artikkeltekst uten frontmatter, som streng.

    Raises:
        FileNotFoundError: Hvis vault-filen ikke finnes.
    """
    # vault_sti kan inneholde Windows-skråstreker — normaliser til Path
    fil = vault_rot / Path(vault_sti)
    if not fil.exists():
        raise FileNotFoundError(f"Vault-fil ikke funnet: {fil}")
    innhold = fil.read_text(encoding="utf-8")

    # Fjern YAML-frontmatter (--- ... ---)
    if innhold.startswith("---"):
        slutt = innhold.find("\n---", 3)
        if slutt != -1:
            innhold = innhold[slutt + 4:].strip()

    return innhold


def _kutt_til_tokens(tekst: str, maks_tokens: int) -> str:
    """Kutter tekst til omtrent maks_tokens tokens (1 token ≈ 4 tegn).

    Kutter ved siste linjeskift for å unngå å kutte midt i en setning.

    Args:
        tekst: Artikkeltekst.
        maks_tokens: Øvre grense for antall tokens.

    Returns:
        Tekst innenfor grensen.
    """
    maks_tegn = maks_tokens * 4
    if len(tekst) <= maks_tegn:
        return tekst

    kuttet = tekst[:maks_tegn]
    siste_linjeskift = kuttet.rfind("\n")
    if siste_linjeskift > int(maks_tegn * 0.8):
        kuttet = kuttet[:siste_linjeskift]

    logger.info(
        "Artikkeltekst kuttet fra %d til ~%d tokens",
        len(tekst) // 4,
        maks_tokens,
    )
    return kuttet


def _bygg_brukermelding(
    prompt: str,
    artikkeltekst: str,
    regulatorisk_kontekst: str,
) -> str:
    """Bygger komplett brukermelding med regulatorisk kontekst og XML-innrammet artikkel.

    Erstatter plassholderteksten [LIM INN ARTIKKEL] i prompten med regulatorisk
    kontekst og artikkeltekst pakket i XML-tagger.

    Args:
        prompt: Basis-prompt med [LIM INN ARTIKKEL]-plassholder.
        artikkeltekst: Artikkeltekst (allerede kuttet til maks tokens).
        regulatorisk_kontekst: Innhold fra regulatorisk-kontekst.md.

    Returns:
        Komplett brukermelding klar for API-kall.
    """
    kontekst_blokk = ""
    if regulatorisk_kontekst:
        kontekst_blokk = (
            f"\nRegulatorisk kontekst (AI Act, NIS2, ISO 42001):\n"
            f"<kontekst>\n{regulatorisk_kontekst}\n</kontekst>\n\n"
        )

    artikkel_blokk = f"<artikkel>\n{artikkeltekst}\n</artikkel>"
    return prompt.replace("[LIM INN ARTIKKEL]", f"{kontekst_blokk}{artikkel_blokk}")


def _kall_openai(brukermelding: str, klient: OpenAI) -> str:
    """Kaller OpenAI API og returnerer sammendraget.

    Spores av Opik hvis tilgjengelig. Selve kallet er innpakket slik at
    sporingssvikt ikke stopper kjøringen.

    Args:
        brukermelding: Komplett melding med prompt, kontekst og artikkel.
        klient: Initialisert OpenAI-klient.

    Returns:
        Sammendragstekst fra modellen.
    """
    def _kall() -> str:
        respons = klient.chat.completions.create(
            model=_OPENAI_MODELL,
            messages=[{"role": "user", "content": brukermelding}],
            max_tokens=_MAKS_SAMMENDRAG_TOKENS,
            temperature=_TEMPERATURE,
        )
        return respons.choices[0].message.content or ""

    if _OPIK_TILGJENGELIG:
        try:
            return opik.track(name="lag_sammendrag")(_kall)()
        except Exception as feil:
            logger.warning("Opik-sporing feilet — kjører uten sporing: %s", feil)

    return _kall()


def _lagre_sammendrag(db_sti: Path, element_id: int, tekst: str) -> None:
    """Lagrer sammendrag i sammendrag-tabellen.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        element_id: Primærnøkkel fra elementer-tabellen.
        tekst: Generert sammendragstekst.
    """
    opprettet = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute("PRAGMA foreign_keys = ON")
        tilkobling.execute(
            "INSERT INTO sammendrag (element_id, tekst, prompt_versjon, opprettet) VALUES (?, ?, ?, ?)",
            (element_id, tekst, PROMPT_VERSJON, opprettet),
        )


# ---------------------------------------------------------------------------
# Offentlig API
# ---------------------------------------------------------------------------


def lag_alle_sammendrag(
    db_sti: Path,
    vault_rot: Path,
    prompts_mappe: Path,
    specs_mappe: Path,
) -> None:
    """Genererer sammendrag for alle artikler som mangler det i SQLite.

    Henter elementer uten sammendrag, behandler dem sekvensielt og lagrer
    resultatet. Feil på enkeltartikler logges og kjøringen fortsetter.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        vault_rot: Rot-mappe for Obsidian-vault.
        prompts_mappe: Mappe med prompt-tekstfiler.
        specs_mappe: Sti til specs/-mappen (for regulatorisk-kontekst.md).
    """
    prompt = _les_prompt(prompts_mappe)
    regulatorisk_kontekst = _les_regulatorisk_kontekst(specs_mappe)
    klient = OpenAI(api_key=os.getenv("OPENAI_API_NØKKEL"))

    with sqlite3.connect(db_sti) as tilkobling:
        rader = tilkobling.execute(
            """
            SELECT e.id, e.tittel, e.vault_sti
            FROM elementer e
            LEFT JOIN sammendrag s ON s.element_id = e.id
            WHERE s.id IS NULL
              AND e.dead_letter = 0
              AND e.vault_sti IS NOT NULL
            """
        ).fetchall()

    if not rader:
        logger.info("Ingen artikler å behandle.")
        return

    logger.info("Behandler %d artikler.", len(rader))
    for element_id, tittel, vault_sti in rader:
        try:
            artikkeltekst = _les_artikkeltekst(vault_rot, vault_sti)
            artikkeltekst = _kutt_til_tokens(artikkeltekst, _MAKS_ARTIKKEL_TOKENS)
            brukermelding = _bygg_brukermelding(prompt, artikkeltekst, regulatorisk_kontekst)
            sammendrag = _kall_openai(brukermelding, klient)
            _lagre_sammendrag(db_sti, element_id, sammendrag)
            logger.info("Sammendrag lagret for element %d: %s", element_id, tittel)
        except FileNotFoundError as feil:
            logger.error(
                "Vault-fil ikke funnet for element %d (%s): %s", element_id, tittel, feil
            )
        except Exception as feil:
            logger.error(
                "Feil ved behandling av element %d (%s): %s", element_id, tittel, feil
            )


# ---------------------------------------------------------------------------
# Inngangspunkt for make sammendrag
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # Repo-rot er tre nivåer over src/intelligence_monitor/sammendrag/
    rotmappe = Path(__file__).parents[3]

    lag_alle_sammendrag(
        db_sti=_DATABASE_STI,
        vault_rot=_VAULT_ROT,
        prompts_mappe=Path(__file__).parent / "prompts",
        specs_mappe=rotmappe / "specs",
    )
