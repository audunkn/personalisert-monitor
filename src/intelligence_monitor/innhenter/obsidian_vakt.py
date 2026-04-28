"""Watchdog-basert vakt på vault/innboks/.

Overvåker mappen for nye .md-filer fra Obsidian Web Clipper og prosesserer
dem via vault_skriver.lagre_artikkel(). Feil i én fil stopper ikke behandling
av neste. Manuelt klippede artikler lagres alltid — ingen datointervall-sjekk.

Bruk:
    python -m intelligence_monitor.innhenter.obsidian_vakt
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
import time
from pathlib import Path

import pypdf
import yaml
from urllib.parse import urlparse
from dotenv import load_dotenv
from watchdog.events import FileCreatedEvent, FileDeletedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from intelligence_monitor.innhenter import vault_skriver

load_dotenv()

logger = logging.getLogger(__name__)

_H1_MONSTER = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# Navn på manuell-kilde i kilder-tabellen
_MANUELL_KILDENAVN = "manuell-klipp"
_PDF_KILDENAVN = "manuell-pdf"


class _InnboksHandler(FileSystemEventHandler):
    """Håndterer fil-opprettelse-hendelser i vault/innboks/.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        vault_rot: Rot-mappe for Obsidian-vault.
    """

    def __init__(self, db_sti: Path, vault_rot: Path) -> None:
        self._db_sti = db_sti
        self._vault_rot = vault_rot

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        """Kalles av watchdog når en ny fil opprettes i innboks/.

        Ignorerer mapper og ukjente filtyper. Feil isoleres per fil.
        """
        if event.is_directory:
            return
        src = str(event.src_path)
        if src.endswith(".md"):
            fil_sti = Path(src)
            try:
                self._prosesser(fil_sti)
            except Exception as feil:
                logger.error("Ubehandlet feil ved prosessering av %s: %s", fil_sti.name, feil, exc_info=True)
            return
        if src.endswith(".pdf"):
            fil_sti = Path(src)
            try:
                self._prosesser_pdf(fil_sti)
            except Exception as feil:
                logger.error("Ubehandlet feil ved prosessering av %s: %s", fil_sti.name, feil, exc_info=True)
            return

    def _prosesser(self, fil_sti: Path) -> None:
        """Prosesserer én .md-fil fra innboks/.

        Rekkefølge:
        1. Vent kort slik at filen rekker å bli ferdigskrevet.
        2. Les frontmatter og kropp.
        3. Sjekk URL mot elementer-tabellen (dedup).
        4. Dedup → slett fil og logg INFO.
        5. Ny URL → lagre via vault_skriver, flytt til behandlet/.

        Args:
            fil_sti: Sti til den nye .md-filen i innboks/.
        """
        # Kort pause — watchdog kan fyre før filen er ferdigskrevet
        time.sleep(0.3)

        if not fil_sti.exists():
            logger.warning("Fil forsvant før prosessering: %s", fil_sti.name)
            return

        frontmatter, kropp = _les_frontmatter_og_kropp(fil_sti)
        url = (frontmatter.get("url") or frontmatter.get("source") or "").strip()

        if not url:
            logger.warning("Ingen URL i frontmatter — hopper over %s", fil_sti.name)
            return

        # Dedup-sjekk
        if _url_finnes(self._db_sti, url):
            logger.info(
                "Duplikat URL funnet — sletter innboks-fil: %s (%s)",
                fil_sti.name,
                url,
            )
            fil_sti.unlink(missing_ok=True)
            return

        # Hent kilde_id for manuell-klipp
        kilde_id = _hent_kilde_id(self._db_sti, _MANUELL_KILDENAVN)
        if kilde_id is None:
            logger.error(
                "Kilde '%s' ikke funnet i databasen — kjør db.init først",
                _MANUELL_KILDENAVN,
            )
            return

        tittel, kropp_uten_tittel = _trekk_ut_tittel(frontmatter, kropp, fil_sti.stem)
        klippet_dato = str(frontmatter.get("klippet_dato", "")) or None
        kildetype = str(frontmatter.get("kildetype", "manuell"))

        vault_skriver.lagre_artikkel(
            kilde_id=kilde_id,
            url=url,
            tittel=tittel,
            innhold=kropp_uten_tittel,
            publisert=None,
            kildetype=kildetype,
            db_sti=self._db_sti,
            vault_rot=self._vault_rot,
            klippet_dato=klippet_dato,
            kilde_mappe=_domene_fra_url(url),
        )

        # Flytt til behandlet/
        behandlet_mappe = self._vault_rot / "behandlet"
        behandlet_mappe.mkdir(parents=True, exist_ok=True)
        shutil.move(str(fil_sti), str(behandlet_mappe / fil_sti.name))
        logger.info("Lagret og flyttet til behandlet/: %s", fil_sti.name)

    def _prosesser_pdf(self, fil_sti: Path) -> None:
        """Prosesserer én .pdf-fil fra innboks/.

        Rekkefølge:
        1. Vent kort slik at filen rekker å bli ferdigskrevet.
        2. Sjekk URL-dedupnøkkel mot elementer-tabellen.
        3. Dedup → slett fil og logg INFO.
        4. Ny → ekstrakt tekst, lagre via vault_skriver, flytt til behandlet/.

        Args:
            fil_sti: Sti til den nye .pdf-filen i innboks/.
        """
        time.sleep(0.3)

        if not fil_sti.exists():
            logger.warning("Fil forsvant før prosessering: %s", fil_sti.name)
            return

        url = f"pdf://{fil_sti.stem}"

        if _url_finnes(self._db_sti, url):
            logger.info("Duplikat PDF — sletter: %s (%s)", fil_sti.name, url)
            fil_sti.unlink(missing_ok=True)
            return

        kilde_id = _hent_kilde_id(self._db_sti, _PDF_KILDENAVN)
        if kilde_id is None:
            logger.error(
                "Kilde '%s' ikke funnet i databasen — kjør db.init først",
                _PDF_KILDENAVN,
            )
            return

        tittel, innhold = _trekk_ut_pdf_innhold(fil_sti)

        if not innhold.strip():
            logger.warning("Ingen tekst å hente fra %s — hopper over", fil_sti.name)
            return

        vault_skriver.lagre_artikkel(
            kilde_id=kilde_id,
            url=url,
            tittel=tittel,
            innhold=innhold,
            publisert=None,
            kildetype="pdf",
            db_sti=self._db_sti,
            vault_rot=self._vault_rot,
            klippet_dato=None,
            kilde_mappe=_PDF_KILDENAVN,
        )

        behandlet_mappe = self._vault_rot / "behandlet"
        behandlet_mappe.mkdir(parents=True, exist_ok=True)
        shutil.move(str(fil_sti), str(behandlet_mappe / fil_sti.name))
        logger.info("Lagret og flyttet til behandlet/: %s", fil_sti.name)


class _ArtikkelHandler(FileSystemEventHandler):
    """Håndterer sletting av .md-filer i vault/artikler/.

    Når en .md-fil slettes fra artikler/, ryddes tilhørende bilder og
    DB-raden automatisk opp.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        vault_rot: Rot-mappe for Obsidian-vault.
    """

    def __init__(self, db_sti: Path, vault_rot: Path) -> None:
        self._db_sti = db_sti
        self._vault_rot = vault_rot

    def on_deleted(self, event: FileDeletedEvent) -> None:  # type: ignore[override]
        """Kalles av watchdog når en fil slettes fra artikler/.

        Ignorerer mapper og ikke-.md-filer. Feil isoleres per fil.
        """
        if event.is_directory or not str(event.src_path).endswith(".md"):
            return
        fil_sti = Path(str(event.src_path))
        vault_sti = fil_sti.relative_to(self._vault_rot).as_posix()
        try:
            _rydd_etter_slettet_artikkel(self._db_sti, self._vault_rot, vault_sti)
        except Exception as feil:
            logger.error(
                "Ubehandlet feil ved rydding etter slettet %s: %s",
                fil_sti.name,
                feil,
                exc_info=True,
            )


def _rydd_etter_slettet_artikkel(db_sti: Path, vault_rot: Path, vault_sti: str) -> None:
    """Rydder opp bilder og DB-rad etter at en artikkel er slettet.

    Rekkefølge:
    1. Hent rad fra elementer WHERE vault_sti = ?
    2. Parse bilder_json → slett hver bildefil fra vault/ressurser/bilder/
    3. DELETE rad fra elementer
    4. Logg INFO med antall slettede bilder

    Args:
        db_sti: Sti til SQLite-databasefilen.
        vault_rot: Rot-mappe for Obsidian-vault.
        vault_sti: Relativ sti til den slettede .md-filen (f.eks. 'artikler/abc-slug.md').
    """
    with sqlite3.connect(db_sti) as tilkobling:
        rad = tilkobling.execute(
            "SELECT id, bilder_json FROM elementer WHERE vault_sti = ?", (vault_sti,)
        ).fetchone()

    if rad is None:
        logger.info("Ingen DB-rad funnet for slettet fil: %s — hopper over", vault_sti)
        return

    element_id, bilder_json_tekst = rad
    bildefilnavn: list[str] = json.loads(bilder_json_tekst) if bilder_json_tekst else []

    bilde_mappe = vault_rot / "ressurser" / "bilder"
    antall_slettet = 0
    for filnavn in bildefilnavn:
        bilde_fil = bilde_mappe / filnavn
        if bilde_fil.exists():
            bilde_fil.unlink()
            antall_slettet += 1

    with sqlite3.connect(db_sti) as tilkobling:
        antall_triplets = tilkobling.execute(
            "DELETE FROM evalueringstriplets WHERE element_id = ?", (element_id,)
        ).rowcount
        antall_sammendrag = tilkobling.execute(
            "DELETE FROM sammendrag WHERE element_id = ?", (element_id,)
        ).rowcount
        tilkobling.execute("DELETE FROM elementer WHERE id = ?", (element_id,))

    logger.info(
        "Ryddet etter slettet artikkel '%s': %d bilde(r), %d sammendrag og %d triplet(s) fjernet",
        vault_sti,
        antall_slettet,
        antall_sammendrag,
        antall_triplets,
    )


# ---------------------------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------------------------


def _domene_fra_url(url: str) -> str:
    """Trekker ut domene fra URL for bruk som vault-mappe.

    Fjerner www.-prefiks og erstatter punktum med bindestrek.
    Returnerer 'ukjent-kilde' ved tom netloc.
    """
    netloc = urlparse(url).netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc.replace(".", "-") or "ukjent-kilde"


def _trekk_ut_pdf_innhold(fil_sti: Path) -> tuple[str, str]:
    """Trekker ut tittel og tekstinnhold fra en PDF-fil.

    Tittel hentes fra PDF-metadata (/Title) hvis tilgjengelig, ellers brukes filnavn.
    Innhold er alle sider slått sammen med dobbelt linjeskift.

    Args:
        fil_sti: Sti til .pdf-filen.

    Returns:
        Tuple (tittel, innhold).
    """
    reader = pypdf.PdfReader(fil_sti)

    tittel = ""
    if reader.metadata and reader.metadata.get("/Title"):
        tittel = str(reader.metadata["/Title"]).strip()
    if not tittel:
        tittel = fil_sti.stem

    sider = [side.extract_text() or "" for side in reader.pages]
    innhold = "\n\n".join(s for s in sider if s.strip())

    return tittel, innhold


def _les_frontmatter_og_kropp(fil_sti: Path) -> tuple[dict, str]:
    """Leser YAML-frontmatter og kropp fra en Markdown-fil.

    Args:
        fil_sti: Sti til .md-filen.

    Returns:
        Tuple (frontmatter-dict, kropp-streng). Frontmatter er tom dict
        hvis filen ikke starter med '---'.
    """
    innhold = fil_sti.read_text(encoding="utf-8")
    if not innhold.startswith("---"):
        return {}, innhold
    deler = innhold.split("---", 2)
    if len(deler) < 3:
        return {}, innhold
    frontmatter = yaml.safe_load(deler[1]) or {}
    kropp = deler[2].strip()
    return frontmatter, kropp


def _trekk_ut_tittel(
    frontmatter: dict, kropp: str, filnavn_uten_ext: str
) -> tuple[str, str]:
    """Trekker ut tittel og returnerer kropp uten tittel-heading.

    Prioritet: frontmatter-felt 'tittel'/'title' → første H1 i kropp → filnavn.
    Hvis tittel hentes fra første H1, fjernes den fra kroppen for å unngå
    duplisert heading (vault_skriver.py legger til # {tittel} selv).

    Args:
        frontmatter: Parsert YAML-frontmatter.
        kropp: Markdown-kropp uten frontmatter.
        filnavn_uten_ext: Filnavn uten .md-endelse — brukes som siste fallback.

    Returns:
        Tuple (tittel, kropp_uten_tittel_heading).
    """
    # Sjekk frontmatter først
    tittel = frontmatter.get("tittel") or frontmatter.get("title") or ""
    if tittel:
        return str(tittel).strip(), kropp

    # Prøv første H1 i kroppen
    treff = _H1_MONSTER.search(kropp)
    if treff:
        tittel = treff.group(1).strip()
        # Fjern heading-linjen fra kroppen
        kropp_uten = kropp[: treff.start()].rstrip() + "\n" + kropp[treff.end() :].lstrip()
        return tittel, kropp_uten.strip()

    # Siste fallback: filnavn
    return filnavn_uten_ext, kropp


def _hent_kilde_id(db_sti: Path, navn: str) -> int | None:
    """Returnerer primærnøkkel fra kilder-tabellen for gitt kildenavn.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        navn: Kildenavnet å slå opp.

    Returns:
        Heltalls-ID eller None hvis kilden ikke finnes.
    """
    with sqlite3.connect(db_sti) as tilkobling:
        rad = tilkobling.execute(
            "SELECT id FROM kilder WHERE navn = ?", (navn,)
        ).fetchone()
    return int(rad[0]) if rad else None


def _url_finnes(db_sti: Path, url: str) -> bool:
    """Sjekker om URL allerede er lagret i elementer-tabellen.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        url: URL å sjekke.

    Returns:
        True hvis URL finnes, False ellers.
    """
    with sqlite3.connect(db_sti) as tilkobling:
        rad = tilkobling.execute(
            "SELECT 1 FROM elementer WHERE url = ?", (url,)
        ).fetchone()
    return rad is not None


# ---------------------------------------------------------------------------
# Inngangspunkt
# ---------------------------------------------------------------------------


def start(vault_rot: Path, db_sti: Path) -> None:
    """Starter watchdog-observatøren og blokkerer til KeyboardInterrupt.

    Args:
        vault_rot: Rot-mappe for Obsidian-vault.
        db_sti: Sti til SQLite-databasefilen.
    """
    innboks = vault_rot / "innboks"
    innboks.mkdir(parents=True, exist_ok=True)
    artikler = vault_rot / "artikler"
    artikler.mkdir(parents=True, exist_ok=True)

    handler = _InnboksHandler(db_sti=db_sti, vault_rot=vault_rot)
    artikkel_handler = _ArtikkelHandler(db_sti=db_sti, vault_rot=vault_rot)

    # Skann eksisterende filer i innboks ved oppstart
    for fil in sorted(innboks.iterdir()):
        if fil.suffix == ".md":
            handler._prosesser(fil)
        elif fil.suffix == ".pdf":
            handler._prosesser_pdf(fil)

    observer = Observer()
    observer.schedule(handler, str(innboks), recursive=False)
    observer.schedule(artikkel_handler, str(artikler), recursive=True)
    observer.start()
    logger.info("Vakt startet — overvåker %s og %s", innboks, artikler)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    logger.info("Vakt stoppet.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _vault_rot = Path(os.getenv("VAULT_ROT", "vault"))
    _db_sti = Path(os.getenv("DATABASE_STI", "data/monitor.db"))
    start(vault_rot=_vault_rot, db_sti=_db_sti)
