"""Atomisk lagring av artikler til Obsidian-vault og SQLite.

Alle innhentingskanaler (RSS, nett, YouTube, manuell) bruker denne modulen
for å lagre artikler konsistent. Skrivesekvensen er:

    1. Generer UUID
    2. Last ned bilder og erstatt URL-er i innhold
    3. Skriv .md-fil til vault/artikler/
    4. Skriv rad til elementer i SQLite
    5. Feil i steg 4 → slett fil fra steg 3 (rollback)
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Offentlig API
# ---------------------------------------------------------------------------


def lagre_artikkel(
    kilde_id: int,
    url: str,
    tittel: str,
    innhold: str,
    publisert: str | None,
    kildetype: str,
    db_sti: Path,
    vault_rot: Path,
    klippet_dato: str | None = None,
) -> str:
    """Lagrer en artikkel atomisk til vault og SQLite.

    Args:
        kilde_id: Primærnøkkel fra kilder-tabellen.
        url: Artikkelen sin URL.
        tittel: Artikkeltittel — brukes i filnavn og frontmatter.
        innhold: Markdown-tekst fra kilden.
        publisert: ISO-dato/datetime fra kilden. Kan være None.
        kildetype: Kildetypen (f.eks. 'rss', 'manuell').
        db_sti: Sti til SQLite-databasefilen.
        vault_rot: Rot-mappe for Obsidian-vault.
        klippet_dato: ISO-dato for manuell klipping. Brukes som fallback for publisert.

    Returns:
        element_id som full UUID4-streng.

    Raises:
        sqlite3.Error: Hvis SQLite-skriving feiler etter at filen er skrevet.
    """
    element_id = str(uuid.uuid4())
    uuid_kort = element_id.replace("-", "")[:8]

    # Steg 2: Last ned bilder og erstatt URL-er
    innhold_behandlet, bildefilnavn = _behandle_bilder(innhold, vault_rot, url)

    # Steg 3: Skriv .md-fil til vault/artikler/
    effektiv_publisert = publisert or klippet_dato
    md_innhold = _bygg_markdown(
        element_id=element_id,
        url=url,
        tittel=tittel,
        kildetype=kildetype,
        klippet_dato=klippet_dato,
        publisert=effektiv_publisert,
        innhold=innhold_behandlet,
    )
    slug = _lag_slug(tittel)
    filnavn = f"{uuid_kort}-{slug}.md"
    artikkel_mappe = vault_rot / "artikler"
    artikkel_mappe.mkdir(parents=True, exist_ok=True)
    fil_sti = artikkel_mappe / filnavn
    fil_sti.write_text(md_innhold, encoding="utf-8")

    # Steg 4 + 5: Skriv SQLite — rollback på feil
    hentet = datetime.now(timezone.utc).isoformat()
    vault_sti = str(Path("artikler") / filnavn)
    bilder_json = json.dumps(bildefilnavn) if bildefilnavn else None
    try:
        _skriv_til_db(
            db_sti=db_sti,
            kilde_id=kilde_id,
            guid=element_id,
            url=url,
            tittel=tittel,
            publisert=effektiv_publisert,
            hentet=hentet,
            vault_sti=vault_sti,
            bilder_json=bilder_json,
        )
    except sqlite3.Error:
        fil_sti.unlink(missing_ok=True)
        raise

    return element_id


# ---------------------------------------------------------------------------
# Interne hjelpefunksjoner
# ---------------------------------------------------------------------------


def _lag_slug(tittel: str) -> str:
    """Genererer en URL-trygg slug fra tittel.

    Bruker NFKD-normalisering slik at sammensatte tegn (f.eks. å → a)
    mappes til ASCII der det er mulig. Tegn som ikke kan mappes fjernes stille.

    Args:
        tittel: Artikkeltittel.

    Returns:
        Lowercase slug med kun a-z, 0-9 og bindestreker.
    """
    normalisert = unicodedata.normalize("NFKD", tittel)
    ascii_bytes = normalisert.encode("ascii", errors="ignore")
    slug = ascii_bytes.decode("ascii").lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "artikkel"


def _bygg_markdown(
    element_id: str,
    url: str,
    tittel: str,
    kildetype: str,
    klippet_dato: str | None,
    publisert: str | None,
    innhold: str,
) -> str:
    """Bygger Markdown-fil med YAML-frontmatter.

    Args:
        element_id: Full UUID4 for artikkelen.
        url: Artikkelen sin URL.
        tittel: Artikkeltittel.
        kildetype: Kildetypen.
        klippet_dato: ISO-dato for manuell klipping (None hvis ikke manuell).
        publisert: Effektiv publiseringsdato (kan være None).
        innhold: Behandlet Markdown-tekst.

    Returns:
        Komplett Markdown-dokument med frontmatter.
    """
    linjer = [
        "---",
        f"element_id: {element_id}",
        f"url: {url}",
        f"kildetype: {kildetype}",
    ]
    if klippet_dato is not None:
        linjer.append(f"klippet_dato: {klippet_dato}")
    if publisert is not None:
        linjer.append(f"publisert: {publisert}")
    linjer.append("---")
    frontmatter = "\n".join(linjer)
    return f"{frontmatter}\n\n# {tittel}\n\n{innhold}\n"


def _behandle_bilder(innhold: str, vault_rot: Path, base_url: str = "") -> tuple[str, list[str]]:
    """Laster ned alle bilder i innholdet og erstatter URL-er med lokale stier.

    Finner bilder på formene:
    - Markdown: ``![alt](url)``
    - HTML: ``<img src="url">``

    Bilder lagres i ``vault/ressurser/bilder/{uuid8}.{ext}``.
    Ugyldig URL eller HTTP-feil: logg WARNING, behold original-URL.

    Args:
        innhold: Markdown-tekst med potensielle bilde-URL-er.
        vault_rot: Rot-mappe for Obsidian-vault.
        base_url: Artikkelens kanoniske URL — brukes til å løse relative bilde-URL-er.

    Returns:
        Tuple (innhold med lokale bildestier, liste med nedlastede bildefilnavn).
    """
    bilde_mappe = vault_rot / "ressurser" / "bilder"
    bilde_mappe.mkdir(parents=True, exist_ok=True)

    md_monster = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    html_monster = re.compile(r'<img\s+[^>]*src=["\']([^"\']+)["\']', re.IGNORECASE)

    # Samle unike bilde-URL-er og slå opp lokal sti
    url_til_lokal: dict[str, str] = {}

    for treff in md_monster.finditer(innhold):
        bilde_url = treff.group(2)
        if bilde_url not in url_til_lokal:
            abs_url = urljoin(base_url, bilde_url) if base_url else bilde_url
            lokal = _last_ned_bilde(abs_url, bilde_mappe)
            if lokal:
                url_til_lokal[bilde_url] = lokal

    for treff in html_monster.finditer(innhold):
        bilde_url = treff.group(1)
        if bilde_url not in url_til_lokal:
            abs_url = urljoin(base_url, bilde_url) if base_url else bilde_url
            lokal = _last_ned_bilde(abs_url, bilde_mappe)
            if lokal:
                url_til_lokal[bilde_url] = lokal

    bildefilnavn: list[str] = []
    for original_url, lokal_sti in url_til_lokal.items():
        innhold = innhold.replace(original_url, lokal_sti)
        bildefilnavn.append(Path(lokal_sti).name)

    return innhold, bildefilnavn


def _last_ned_bilde(url: str, bilde_mappe: Path) -> str | None:
    """Laster ned ett bilde og lagrer det lokalt.

    Args:
        url: Bilde-URL.
        bilde_mappe: Målmappe for nedlastede bilder.

    Returns:
        Relativ sti fra vault/artikler/ til bildet som streng,
        eller None ved feil.
    """
    if not url.startswith(("http://", "https://")):
        logger.warning("Ugyldig bilde-URL (ikke http/https): %s", url)
        return None

    try:
        respons = httpx.get(url, follow_redirects=True, timeout=10.0)
        respons.raise_for_status()
    except Exception as feil:
        logger.warning("Kunne ikke laste ned bilde %s: %s", url, feil)
        return None

    innholdstype = respons.headers.get("content-type", "")
    ext = _finn_ext(innholdstype, url)

    filnavn = f"{uuid.uuid4().hex[:8]}.{ext}"
    (bilde_mappe / filnavn).write_bytes(respons.content)

    # Relativ sti fra vault/artikler/ til vault/ressurser/bilder/
    return f"../ressurser/bilder/{filnavn}"


def _finn_ext(innholdstype: str, url: str) -> str:
    """Bestemmer filendelse fra Content-Type-header eller URL.

    Args:
        innholdstype: Verdien av Content-Type-headeren.
        url: Bilde-URL som fallback.

    Returns:
        Filendelse uten punktum (f.eks. 'jpg', 'png'). Standard: 'bin'.
    """
    type_til_ext = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/svg+xml": "svg",
    }
    mime = innholdstype.split(";")[0].strip().lower()
    if mime in type_til_ext:
        return type_til_ext[mime]

    # Prøv URL-suffix
    url_sti = url.split("?")[0]
    siste_del = url_sti.split("/")[-1]
    if "." in siste_del:
        ext = siste_del.rsplit(".", 1)[-1].lower()
        if ext in {"jpg", "jpeg", "png", "gif", "webp", "svg"}:
            return "jpg" if ext == "jpeg" else ext

    return "bin"


def _skriv_til_db(
    db_sti: Path,
    kilde_id: int,
    guid: str,
    url: str,
    tittel: str,
    publisert: str | None,
    hentet: str,
    vault_sti: str,
    bilder_json: str | None = None,
) -> None:
    """Skriver én rad til elementer-tabellen.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        kilde_id: Primærnøkkel fra kilder-tabellen.
        guid: Full UUID4 for artikkelen.
        url: Artikkelen sin URL.
        tittel: Artikkeltittel.
        publisert: Effektiv publiseringsdato (kan være None).
        hentet: ISO-datetime for henting.
        vault_sti: Relativ sti til .md-filen i vaulten.
        bilder_json: JSON-liste med filnavn for nedlastede bilder, eller None.
    """
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute("PRAGMA foreign_keys = ON")
        tilkobling.execute(
            """
            INSERT INTO elementer (kilde_id, guid, url, tittel, publisert, hentet, vault_sti, bilder_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (kilde_id, guid, url, tittel, publisert, hentet, vault_sti, bilder_json),
        )
