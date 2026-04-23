"""RSS/Atom-innhenting med datointervall og dedup.

Leser alle aktive RSS-kilder fra SQLite, filtrerer på publiseringsdato
og skriver nye artikler til Obsidian-vault og SQLite via vault_skriver.

Env-variabler (overstyrer per-kilde-verdi):
    HENT_FRA: ISO-dato YYYY-MM-DD — nedre grense for publiseringsdato
    HENT_TIL: ISO-dato YYYY-MM-DD — øvre grense for publiseringsdato
    DATABASE_STI: Sti til SQLite-databasefilen
    VAULT_ROT: Rot-mappe for Obsidian-vault
"""

from __future__ import annotations

import logging
import os
import sqlite3
from calendar import timegm
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from dotenv import load_dotenv

from intelligence_monitor.innhenter.vault_skriver import lagre_artikkel

load_dotenv()

logger = logging.getLogger(__name__)

_PROSJEKTROT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Offentlig API
# ---------------------------------------------------------------------------


def innhent_alle() -> int:
    """Innhenter nye artikler fra alle aktive RSS-kilder.

    Leser kilder fra SQLite, filtrerer på datointervall og lagrer nye
    artikler via vault_skriver. Feil på én kilde stopper ikke de øvrige.

    Returns:
        Antall nye artikler lagret i denne kjøringen.
    """
    db_sti = Path(os.getenv("DATABASE_STI", str(_PROSJEKTROT / "data" / "monitor.db")))
    vault_rot = Path(os.getenv("VAULT_ROT", str(_PROSJEKTROT / "vault")))

    # Env-override overstyrer per-kilde-verdi for hele kjøringen
    env_hent_fra = os.getenv("HENT_FRA")
    env_hent_til = os.getenv("HENT_TIL")

    kilder = _hent_aktive_rss_kilder(db_sti)
    logger.info("Fant %d aktive RSS-kilder", len(kilder))

    totalt_nye = 0
    for kilde in kilder:
        nye = _innhent_kilde(kilde, db_sti, vault_rot, env_hent_fra, env_hent_til)
        totalt_nye += nye

    return totalt_nye


# ---------------------------------------------------------------------------
# Interne hjelpefunksjoner
# ---------------------------------------------------------------------------


def _hent_aktive_rss_kilder(db_sti: Path) -> list[dict]:
    """Henter alle aktive RSS-kilder fra databasen.

    Args:
        db_sti: Sti til SQLite-databasefilen.

    Returns:
        Liste av kilderader som dict med nøklene id, navn, url, hent_fra, hent_til.
    """
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.row_factory = sqlite3.Row
        rader = tilkobling.execute(
            "SELECT id, navn, url, hent_fra, hent_til FROM kilder WHERE aktiv = 1 AND type = 'rss'"
        ).fetchall()
    return [dict(rad) for rad in rader]


def _innhent_kilde(
    kilde: dict,
    db_sti: Path,
    vault_rot: Path,
    env_hent_fra: str | None,
    env_hent_til: str | None,
) -> int:
    """Innhenter og lagrer nye artikler fra én RSS-kilde.

    Args:
        kilde: Kildedict med id, navn, url, hent_fra, hent_til.
        db_sti: Sti til SQLite-databasefilen.
        vault_rot: Rot-mappe for Obsidian-vault.
        env_hent_fra: Env-override for nedre dategrense (YYYY-MM-DD eller None).
        env_hent_til: Env-override for øvre dategrense (YYYY-MM-DD eller None).

    Returns:
        Antall nye artikler lagret fra denne kilden.
    """
    kilde_id: int = kilde["id"]
    kilde_navn: str = kilde["navn"]
    url: str = kilde["url"]

    # Env-override prioriteres; fallback til per-kilde-verdi
    hent_fra_str = env_hent_fra or kilde.get("hent_fra")
    hent_til_str = env_hent_til or kilde.get("hent_til")

    hent_fra = _parse_dato(hent_fra_str) if hent_fra_str else None
    hent_til = _parse_dato(hent_til_str) if hent_til_str else None

    logger.info("Innhenter %s (%s)", kilde_navn, url)

    feed = feedparser.parse(url)

    # bozo = True indikerer ugyldig XML eller nettverksfeil
    if feed.bozo:
        feil_melding = str(feed.bozo_exception) if feed.bozo_exception else "Ukjent feed-feil"
        logger.error("Feed-feil for %s: %s", kilde_navn, feil_melding)
        _oppdater_kilde_feil(db_sti, kilde_id, feil_melding)
        return 0

    # Hent kjente guider fra databasen for dedup
    kjente_guider = _hent_kjente_guider(db_sti, kilde_id)

    nye = 0
    for entry in feed.entries:
        guid = getattr(entry, "id", None) or getattr(entry, "link", None)
        if not guid:
            logger.warning("Element uten guid/link i %s — hoppes over", kilde_navn)
            continue

        # Dedup — kjent guid lagres ikke på nytt
        if guid in kjente_guider:
            continue

        pub_dato = _hent_publisert(entry)

        # Datointervall-filtrering — utenfor intervall hoppes over stille
        if hent_fra and pub_dato and pub_dato < hent_fra:
            continue
        if hent_til and pub_dato and pub_dato > hent_til:
            continue

        tittel = getattr(entry, "title", "") or "Uten tittel"
        link = getattr(entry, "link", guid)

        # Hent innhold — foretrekk summary/description over content
        innhold = _hent_innhold(entry)

        publisert_iso = pub_dato.date().isoformat() if pub_dato else None

        try:
            lagre_artikkel(
                kilde_id=kilde_id,
                url=link,
                tittel=tittel,
                innhold=innhold,
                publisert=publisert_iso,
                kildetype="rss",
                db_sti=db_sti,
                vault_rot=vault_rot,
            )
            kjente_guider.add(guid)
            nye += 1
            logger.info("Lagret: %s", tittel)
        except Exception as feil:
            logger.error("Kunne ikke lagre '%s' fra %s: %s", tittel, kilde_navn, feil)

    # Vellykket henting — nullstill eventuelle feilfelt
    _nullstill_kilde_feil(db_sti, kilde_id)
    logger.info("%s: %d nye artikler", kilde_navn, nye)
    return nye


def _parse_dato(dato_str: str) -> datetime:
    """Parser ISO-datostreng til UTC-bevisst datetime.

    Args:
        dato_str: ISO-dato på formatet YYYY-MM-DD.

    Returns:
        datetime-objekt med UTC-tidssone.
    """
    return datetime.fromisoformat(dato_str).replace(tzinfo=timezone.utc)


def _hent_publisert(entry: object) -> datetime | None:
    """Henter publiseringsdato fra feed-element.

    feedparser returnerer published_parsed som time.struct_time (UTC).
    Konverterer til timezone-bevisst datetime via calendar.timegm.

    Args:
        entry: feedparser-element.

    Returns:
        UTC-bevisst datetime, eller None hvis ikke tilgjengelig.
    """
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed is None:
        return None
    # timegm tolker struct_time som UTC og returnerer Unix-tidsstempel
    return datetime.fromtimestamp(timegm(parsed), tz=timezone.utc)


def _hent_innhold(entry: object) -> str:
    """Henter tekstinnhold fra feed-element.

    Prioriterer summary over full content for å holde vault-filer kompakte.
    Full content brukes kun hvis summary mangler.

    Args:
        entry: feedparser-element.

    Returns:
        Innholdstekst (kan være tom streng).
    """
    # summary er vanligvis RSS <description> eller Atom <summary>
    sammendrag = getattr(entry, "summary", None)
    if sammendrag:
        return sammendrag

    # content er Atom <content> — liste av innholdsobjekter
    innhold_liste = getattr(entry, "content", None)
    if innhold_liste:
        return innhold_liste[0].get("value", "") if isinstance(innhold_liste[0], dict) else ""

    return ""


def _hent_kjente_guider(db_sti: Path, kilde_id: int) -> set[str]:
    """Henter alle kjente guider for én kilde fra databasen.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        kilde_id: Primærnøkkel for kilden.

    Returns:
        Sett av guid-strenger (URL-er eller RSS guid-er).
    """
    with sqlite3.connect(db_sti) as tilkobling:
        rader = tilkobling.execute(
            "SELECT guid FROM elementer WHERE kilde_id = ?", (kilde_id,)
        ).fetchall()
    return {rad[0] for rad in rader}


def _oppdater_kilde_feil(db_sti: Path, kilde_id: int, feil_melding: str) -> None:
    """Skriver feilinformasjon til kilder-tabellen.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        kilde_id: Primærnøkkel for kilden.
        feil_melding: Feilmeldingstekst.
    """
    tidsstempel = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute(
            "UPDATE kilder SET sist_feil_tidsstempel = ?, sist_feil_melding = ? WHERE id = ?",
            (tidsstempel, feil_melding, kilde_id),
        )


def _nullstill_kilde_feil(db_sti: Path, kilde_id: int) -> None:
    """Nullstiller feilfelt etter vellykket henting.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        kilde_id: Primærnøkkel for kilden.
    """
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute(
            "UPDATE kilder SET sist_feil_tidsstempel = NULL, sist_feil_melding = NULL WHERE id = ?",
            (kilde_id,),
        )
