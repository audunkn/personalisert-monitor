"""Enhetstester for src/intelligence_monitor/innhenter/rss.py.

Dekker seks grener av intervall- og dedup-logikken:
1. Artikkel innenfor intervall lagres.
2. Artikkel publisert før hent_fra hoppes over.
3. Artikkel publisert etter hent_til hoppes over.
4. Kjent URL lagres ikke på nytt (dedup).
5. HENT_FRA env-override overstyrer per-kilde-verdi.
6. Tom feed håndteres uten feil.

Bruker mock feedparser og midlertidig SQLite — ingen nettverkskall.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from intelligence_monitor.innhenter import rss
from tester.konfig.fixtures import db_sti, vault_rot  # noqa: F401

# kilde_id = 2 er RSS-kilden som legges inn i hjelpe-fixture nedenfor
_RSS_KILDE_ID = 2
_KILDE_URL = "https://test.example.com/feed.xml"
_ARTIKKEL_URL = "https://test.example.com/artikkel-1"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_med_rss_kilde(db_sti):
    """Midlertidig SQLite-database med én RSS-kilde (kilde_id=2).

    Args:
        db_sti: Midlertidig databasesti fra fixtures.py (kilde_id=1 finnes).

    Returns:
        Sti til testdatabasen med RSS-kilde lagt til.
    """
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute(
            """
            INSERT INTO kilder (navn, url, type, aktiv, hent_fra, hent_til)
            VALUES ('test-rss', ?, 'rss', 1, '2026-04-01', NULL)
            """,
            (_KILDE_URL,),
        )
    return db_sti


def _lag_entry(
    url: str = _ARTIKKEL_URL,
    tittel: str = "Testtittel",
    pub_dato: datetime | None = None,
) -> SimpleNamespace:
    """Lager et minimalt feedparser-entry-objekt.

    Args:
        url: Artikkellenkens URL (brukes som id og link).
        tittel: Artikkeltittel.
        pub_dato: Publiseringsdato. Standardverdi: 15. april 2026.

    Returns:
        SimpleNamespace som etterligner feedparser Entry.
    """
    if pub_dato is None:
        pub_dato = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
    # Konverter til time.struct_time slik feedparser returnerer det
    published_parsed = time.gmtime(pub_dato.timestamp())
    return SimpleNamespace(
        id=url,
        link=url,
        title=tittel,
        summary="Testinnhold for artikkelen.",
        published_parsed=published_parsed,
        updated_parsed=None,
        content=None,
    )


def _lag_feed(entries: list) -> MagicMock:
    """Lager et minimalt feedparser-feed-objekt.

    Args:
        entries: Liste av entry-objekter.

    Returns:
        MagicMock som etterligner feedparser FeedParserDict.
    """
    feed = MagicMock()
    feed.bozo = False
    feed.bozo_exception = None
    feed.entries = entries
    return feed


# ---------------------------------------------------------------------------
# Tester
# ---------------------------------------------------------------------------


def test_artikkel_innenfor_intervall_lagres(db_med_rss_kilde, vault_rot, monkeypatch):
    """Artikkel publisert innenfor hent_fra/hent_til-intervallet lagres i vault og SQLite."""
    pub_dato = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
    entry = _lag_entry(pub_dato=pub_dato)
    feed = _lag_feed([entry])

    monkeypatch.setenv("DATABASE_STI", str(db_med_rss_kilde))
    monkeypatch.setenv("VAULT_ROT", str(vault_rot))
    monkeypatch.delenv("HENT_FRA", raising=False)
    monkeypatch.delenv("HENT_TIL", raising=False)

    with patch("intelligence_monitor.innhenter.rss.feedparser.parse", return_value=feed), \
         patch("intelligence_monitor.innhenter.rss._hent_full_artikkel", return_value=None):
        nye = rss.innhent_alle()

    assert nye == 1
    with sqlite3.connect(db_med_rss_kilde) as tilkobling:
        antall = tilkobling.execute(
            "SELECT COUNT(*) FROM elementer WHERE kilde_id = ?", (_RSS_KILDE_ID,)
        ).fetchone()[0]
    assert antall == 1


def test_artikkel_utenfor_hent_fra_hoppes_over(db_med_rss_kilde, vault_rot, monkeypatch):
    """Artikkel publisert før hent_fra lagres ikke."""
    # Publisert 2026-03-01, kilde har hent_fra = 2026-04-01
    pub_dato = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    entry = _lag_entry(pub_dato=pub_dato)
    feed = _lag_feed([entry])

    monkeypatch.setenv("DATABASE_STI", str(db_med_rss_kilde))
    monkeypatch.setenv("VAULT_ROT", str(vault_rot))
    monkeypatch.delenv("HENT_FRA", raising=False)
    monkeypatch.delenv("HENT_TIL", raising=False)

    with patch("intelligence_monitor.innhenter.rss.feedparser.parse", return_value=feed), \
         patch("intelligence_monitor.innhenter.rss._hent_full_artikkel", return_value=None):
        nye = rss.innhent_alle()

    assert nye == 0
    with sqlite3.connect(db_med_rss_kilde) as tilkobling:
        antall = tilkobling.execute(
            "SELECT COUNT(*) FROM elementer WHERE kilde_id = ?", (_RSS_KILDE_ID,)
        ).fetchone()[0]
    assert antall == 0


def test_artikkel_utenfor_hent_til_hoppes_over(db_med_rss_kilde, vault_rot, monkeypatch):
    """Artikkel publisert etter hent_til lagres ikke."""
    pub_dato = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
    entry = _lag_entry(pub_dato=pub_dato)
    feed = _lag_feed([entry])

    # Sett hent_til til en dato som er tidligere enn artikkelen
    monkeypatch.setenv("DATABASE_STI", str(db_med_rss_kilde))
    monkeypatch.setenv("VAULT_ROT", str(vault_rot))
    monkeypatch.delenv("HENT_FRA", raising=False)
    monkeypatch.setenv("HENT_TIL", "2026-04-10")

    with patch("intelligence_monitor.innhenter.rss.feedparser.parse", return_value=feed), \
         patch("intelligence_monitor.innhenter.rss._hent_full_artikkel", return_value=None):
        nye = rss.innhent_alle()

    assert nye == 0


def test_kjent_url_lagres_ikke_på_nytt(db_med_rss_kilde, vault_rot, monkeypatch):
    """Artikkel med kjent URL legges ikke til i databasen på nytt (idempotens)."""
    pub_dato = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
    entry = _lag_entry(pub_dato=pub_dato)
    feed = _lag_feed([entry])

    monkeypatch.setenv("DATABASE_STI", str(db_med_rss_kilde))
    monkeypatch.setenv("VAULT_ROT", str(vault_rot))
    monkeypatch.delenv("HENT_FRA", raising=False)
    monkeypatch.delenv("HENT_TIL", raising=False)

    with patch("intelligence_monitor.innhenter.rss.feedparser.parse", return_value=feed), \
         patch("intelligence_monitor.innhenter.rss._hent_full_artikkel", return_value=None):
        første_kjøring = rss.innhent_alle()
        andre_kjøring = rss.innhent_alle()

    assert første_kjøring == 1
    assert andre_kjøring == 0  # Ingen duplikater

    with sqlite3.connect(db_med_rss_kilde) as tilkobling:
        antall = tilkobling.execute(
            "SELECT COUNT(*) FROM elementer WHERE kilde_id = ?", (_RSS_KILDE_ID,)
        ).fetchone()[0]
    assert antall == 1


def test_env_override_hent_fra_overstyrer_per_kilde(db_med_rss_kilde, vault_rot, monkeypatch):
    """HENT_FRA env-variabel overstyrer per-kilde hent_fra for alle kilder."""
    # Kilde har hent_fra = 2026-04-01
    # Artikkel publisert 2026-04-15 — ville normalt bli lagret
    # Men HENT_FRA settes til 2026-04-20 → artikkelen er for gammel og hoppes over
    pub_dato = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
    entry = _lag_entry(pub_dato=pub_dato)
    feed = _lag_feed([entry])

    monkeypatch.setenv("DATABASE_STI", str(db_med_rss_kilde))
    monkeypatch.setenv("VAULT_ROT", str(vault_rot))
    monkeypatch.setenv("HENT_FRA", "2026-04-20")
    monkeypatch.delenv("HENT_TIL", raising=False)

    with patch("intelligence_monitor.innhenter.rss.feedparser.parse", return_value=feed), \
         patch("intelligence_monitor.innhenter.rss._hent_full_artikkel", return_value=None):
        nye = rss.innhent_alle()

    assert nye == 0


def test_tom_feed_håndteres_uten_feil(db_med_rss_kilde, vault_rot, monkeypatch):
    """Tom feed (ingen entries) returnerer 0 uten feil."""
    feed = _lag_feed([])

    monkeypatch.setenv("DATABASE_STI", str(db_med_rss_kilde))
    monkeypatch.setenv("VAULT_ROT", str(vault_rot))
    monkeypatch.delenv("HENT_FRA", raising=False)
    monkeypatch.delenv("HENT_TIL", raising=False)

    with patch("intelligence_monitor.innhenter.rss.feedparser.parse", return_value=feed), \
         patch("intelligence_monitor.innhenter.rss._hent_full_artikkel", return_value=None):
        nye = rss.innhent_alle()

    assert nye == 0


def test_full_artikkel_brukes_når_tilgjengelig(db_med_rss_kilde, vault_rot, monkeypatch):
    """_hent_full_artikkel kalles med artikkelens URL og resultatet lagres."""
    entry = _lag_entry()
    feed = _lag_feed([entry])
    monkeypatch.setenv("DATABASE_STI", str(db_med_rss_kilde))
    monkeypatch.setenv("VAULT_ROT", str(vault_rot))
    monkeypatch.delenv("HENT_FRA", raising=False)
    monkeypatch.delenv("HENT_TIL", raising=False)

    with patch("intelligence_monitor.innhenter.rss.feedparser.parse", return_value=feed), \
         patch("intelligence_monitor.innhenter.rss._hent_full_artikkel", return_value="# Full tekst") as mock_hent:
        rss.innhent_alle()

    mock_hent.assert_called_once_with(_ARTIKKEL_URL)
    with sqlite3.connect(db_med_rss_kilde) as con:
        rad = con.execute("SELECT id FROM elementer WHERE kilde_id = ?", (_RSS_KILDE_ID,)).fetchone()
    assert rad is not None


def test_rss_summary_brukes_som_fallback(db_med_rss_kilde, vault_rot, monkeypatch):
    """Når _hent_full_artikkel returnerer None brukes RSS-summary som fallback."""
    entry = _lag_entry()
    feed = _lag_feed([entry])
    monkeypatch.setenv("DATABASE_STI", str(db_med_rss_kilde))
    monkeypatch.setenv("VAULT_ROT", str(vault_rot))
    monkeypatch.delenv("HENT_FRA", raising=False)
    monkeypatch.delenv("HENT_TIL", raising=False)

    with patch("intelligence_monitor.innhenter.rss.feedparser.parse", return_value=feed), \
         patch("intelligence_monitor.innhenter.rss._hent_full_artikkel", return_value=None):
        nye = rss.innhent_alle()

    assert nye == 1  # Artikkelen lagres med RSS-summary som fallback
