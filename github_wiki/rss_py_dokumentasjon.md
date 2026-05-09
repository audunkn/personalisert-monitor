# rss.py — Teknisk dokumentasjon

## 1. Overordnet beskrivelse

`rss.py` implementerer RSS/Atom-innhenting med datointervall-filtrering og URL-dedup. Filen henter aktive RSS-kilder fra SQLite, itererer over feed-elementer og lagrer nye artikler i Obsidian-vault og databasen via `vault_skriver`. Feil på én kilde stopper ikke innhenting fra de øvrige.

Filen løser tre konkrete problemer: (1) Artikler skal kun hentes innenfor et konfigurert datointervall per kilde, med mulighet for kjøringstids-override via miljøvariabler. (2) Allerede lagrede artikler skal ikke prosesseres på nytt (dedup via URL-sammenligning). (3) Full artikkeltekst skal hentes direkte fra kildelenken når RSS-feeden kun inneholder et sammendrag.

Kun `innhent_alle()` er eksponert som offentlig API. Alle øvrige funksjoner er interne hjelpefunksjoner.

**ASCII-flytdiagram:**

```
innhent_alle()
    │
    ├─► Les DATABASE_STI, VAULT_ROT, HENT_FRA, HENT_TIL fra miljø
    ├─► _hent_aktive_rss_kilder(db_sti)
    │       └─► SQLite: SELECT id, navn, url, hent_fra, hent_til
    │                   FROM kilder WHERE aktiv=1 AND type='rss'
    │
    └─► for kilde in kilder:
            _innhent_kilde(kilde, db_sti, vault_rot, env_hent_fra, env_hent_til)
                │
                ├─► Env-override prioriteres over per-kilde-verdi
                ├─► _parse_dato() for hent_fra og hent_til
                ├─► feedparser.parse(url)
                ├─► bozo-sjekk (XML-valideringsfeil)
                ├─► _hent_kjente_urls(db_sti, kilde_id)
                │
                └─► for entry in feed.entries:
                        ├─ guid/link-sjekk
                        ├─ dedup (link in kjente_urls)
                        ├─► _hent_publisert(entry)
                        ├─ datointervall-filter
                        ├─► _hent_full_artikkel(link)
                        │       ├─► httpx.get(url)
                        │       ├─► BeautifulSoup → <article>/<main>/<body>
                        │       └─► markdownify()
                        │   eller _hent_innhold(entry) ved feil
                        └─► lagre_artikkel(...)
                ├─► _nullstill_kilde_feil() ved suksess
                └─► _oppdater_kilde_feil() ved total feed-feil
```

**Mockup — dataintervall og dedup:**

```
Kilde i DB:
  { id: 1, navn: "MIT Tech Review", url: "https://feeds.technologyreview.com/...",
    hent_fra: "2026-01-01", hent_til: null }

Miljøvariabler:
  HENT_FRA=2026-04-01   ← overstyrer per-kilde-verdi

Kjøring:
  Artikkel publisert 2026-03-15  → under HENT_FRA → hoppes over
  Artikkel publisert 2026-04-10  → ny URL → lagres
  Artikkel publisert 2026-04-10  → kjent URL → hoppes over (dedup)

Logger:
  INFO  Fant 3 aktive RSS-kilder
  INFO  Innhenter MIT Tech Review (https://feeds.technologyreview.com/...)
  INFO  Lagret: Tittel på ny artikkel
  INFO  MIT Tech Review: 1 nye artikler
  INFO  (andre kilder...)
```

---

## 2. Importer og moduloppsett

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `from __future__ import annotations` | Aktiverer utsatt evaluering av typeannotering (PEP 563). |
| `import logging` | Strukturert loggutskrift. |
| `import os` | Brukes til `os.getenv()` for miljøvariabler. |
| `import sqlite3` | SQLite-tilkobling for kilde-oppslag og dedup. |
| `from calendar import timegm` | Konverterer `time.struct_time` (UTC) til Unix-tidsstempel. Brukes i `_hent_publisert()` for å tolke feedparser sin `published_parsed`. |
| `from datetime import datetime, timezone` | `datetime` for datosammenligninger; `timezone.utc` for UTC-bevisste objekter. |
| `from pathlib import Path` | Objektorientert filsti-håndtering. |
| `import feedparser` | Tredjeparts RSS/Atom-parser. Henter og tolker feed-XML fra URL. |
| `import httpx` | Async-kompatibel HTTP-klient. Brukes til å hente full artikkeltekst fra kildelenker. |
| `from bs4 import BeautifulSoup` | HTML-parser. Brukes til å finne `<article>`, `<main>` eller `<body>` i hentede nettsider. |
| `from dotenv import load_dotenv` | Laster miljøvariabler fra `.env`-fil. |
| `from markdownify import markdownify` | Konverterer HTML til Markdown. Brukes på artikkelteksten etter BeautifulSoup-ekstraksjon. |
| `from intelligence_monitor.innhenter.vault_skriver import lagre_artikkel` | Importerer lagrings-API-et direkte (ikke modulen) for enklere kallssyntaks. |
| `load_dotenv()` | Laster `.env` umiddelbart ved modulinnlasting. |
| `logger = logging.getLogger(__name__)` | Logger bundet til `intelligence_monitor.innhenter.rss`. |
| `_PROSJEKTROT = Path(__file__).resolve().parents[3]` | Prosjektrotens absolutte sti. Samme logikk som i `kjører.py`. |

---

## 3. Offentlig API — innhent_alle()

`innhent_alle()` er det eneste offentlige inngangspunktet. Den henter alle aktive RSS-kilder fra databasen og kjører innhenting på hver. Returnerer totalt antall nye artikler lagret i denne kjøringen.

**Miljøvariabler:**

| Variabel | Type | Standardverdi | Forklaring |
|---|---|---|---|
| `DATABASE_STI` | `str` (sti) | `<prosjektrot>/data/monitor.db` | Sti til SQLite-databasefilen. |
| `VAULT_ROT` | `str` (sti) | `<prosjektrot>/vault` | Rotmappe for Obsidian-vault. |
| `HENT_FRA` | `str` (ISO-dato) | `None` — bruker per-kilde-verdi | Overstyrer nedre dategrense for alle kilder i denne kjøringen. |
| `HENT_TIL` | `str` (ISO-dato) | `None` — bruker per-kilde-verdi | Overstyrer øvre dategrense for alle kilder i denne kjøringen. |

**Linje-for-linje:**

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def innhent_alle() -> int:` | Definerer offentlig funksjon. Returnerer `int` — antall nye artikler. |
| `    """Innhenter nye artikler fra alle aktive RSS-kilder.` | Docstring. |
| `    Leser kilder fra SQLite, filtrerer på datointervall og lagrer nye` | Docstring fortsetter. |
| `    artikler via vault_skriver. Feil på én kilde stopper ikke de øvrige.` | Docstring — viktig arkitekturavgjørelse dokumentert her. |
| `    Returns:` | Returns-seksjon. |
| `        Antall nye artikler lagret i denne kjøringen.` | Returverdi. |
| `    """` | Avslutter docstring. |
| `    db_sti = Path(os.getenv("DATABASE_STI", str(_PROSJEKTROT / "data" / "monitor.db")))` | Leser databasesti fra miljø med standardverdi. |
| `    vault_rot = Path(os.getenv("VAULT_ROT", str(_PROSJEKTROT / "vault")))` | Leser vault-rot fra miljø med standardverdi. |
| `    # Env-override overstyrer per-kilde-verdi for hele kjøringen` | Kommentar. |
| `    env_hent_fra = os.getenv("HENT_FRA")` | Leser global dategrense fra miljø. `None` hvis ikke satt. |
| `    env_hent_til = os.getenv("HENT_TIL")` | Leser global øvre dategrense. `None` hvis ikke satt. |
| `    kilder = _hent_aktive_rss_kilder(db_sti)` | Henter alle aktive RSS-kilder fra databasen. |
| `    logger.info("Fant %d aktive RSS-kilder", len(kilder))` | Logger antall kilder. |
| `    totalt_nye = 0` | Initialiserer total-teller. |
| `    for kilde in kilder:` | Itererer over alle aktive kilder. |
| `        nye = _innhent_kilde(kilde, db_sti, vault_rot, env_hent_fra, env_hent_til)` | Kjører innhenting for én kilde. Feil propagerer ikke (håndteres internt). |
| `        totalt_nye += nye` | Akkumulerer totalen. |
| `    return totalt_nye` | Returnerer totalt antall nye artikler. |

---

## 4. Hjelpefunksjoner

### _hent_aktive_rss_kilder(db_sti)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _hent_aktive_rss_kilder(db_sti: Path) -> list[dict]:` | Returnerer liste av kilderader som dict. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Åpner tilkobling som kontekst-manager. |
| `        tilkobling.row_factory = sqlite3.Row` | Setter `row_factory` til `sqlite3.Row` — gjør at rader kan aksesseres som dict med kolonnenavn. |
| `        rader = tilkobling.execute(` | Starter SELECT. |
| `            "SELECT id, navn, url, hent_fra, hent_til FROM kilder WHERE aktiv = 1 AND type = 'rss'"` | Henter kun aktive RSS-kilder. `aktiv = 1` og `type = 'rss'` er begge påkrevde betingelser. |
| `        ).fetchall()` | Henter alle matchende rader. |
| `    return [dict(rad) for rad in rader]` | Konverterer hvert `sqlite3.Row`-objekt til en vanlig Python-dict. |

---

### _innhent_kilde(kilde, db_sti, vault_rot, env_hent_fra, env_hent_til)

Innhenter og lagrer nye artikler fra én RSS-kilde. Håndterer XML-valideringsfeil, datointervall-filtrering og dedup internt.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _innhent_kilde(` | Start av funksjonssignatur. |
| `    kilde: dict,` | Kildedict med id, navn, url, hent_fra, hent_til. |
| `    db_sti: Path,` | Databasesti. |
| `    vault_rot: Path,` | Vault-rot. |
| `    env_hent_fra: str \| None,` | Global dategrense fra miljø (kan være `None`). |
| `    env_hent_til: str \| None,` | Global øvre dategrense fra miljø. |
| `) -> int:` | Returnerer antall nye artikler for denne kilden. |
| `    kilde_id: int = kilde["id"]` | Trekker ut kilde-ID. |
| `    kilde_navn: str = kilde["navn"]` | Trekker ut kildenavn for logging. |
| `    url: str = kilde["url"]` | Trekker ut feed-URL. |
| `    # Env-override prioriteres; fallback til per-kilde-verdi` | Kommentar. |
| `    hent_fra_str = env_hent_fra or kilde.get("hent_fra")` | Env-override prioriteres. Fallback til per-kilde-verdi fra SQLite. |
| `    hent_til_str = env_hent_til or kilde.get("hent_til")` | Samme logikk for øvre grense. |
| `    hent_fra = _parse_dato(hent_fra_str) if hent_fra_str else None` | Parser til datetime hvis streng finnes, ellers `None` (ingen nedre grense). |
| `    hent_til = _parse_dato(hent_til_str) if hent_til_str else None` | Parser øvre grense. |
| `    logger.info("Innhenter %s (%s)", kilde_navn, url)` | Logger hvilken kilde som prosesseres. |
| `    feed = feedparser.parse(url)` | Henter og parser RSS/Atom-feeden. Nettverksfeil returnerer et tomt feed-objekt med `bozo=True`. |
| `    if feed.bozo:` | `bozo` er feedparser sin indikator for XML-valideringsfeil. |
| `        feil_melding = str(feed.bozo_exception) if feed.bozo_exception else "Ukjent feed-feil"` | Henter feilmeldingstekst. |
| `        if not feed.entries:` | Ingen elementer hentet — feeden er ubrukelig. |
| `            logger.error("Feed-feil for %s (ingen elementer): %s", kilde_navn, feil_melding)` | Logger feil. |
| `            _oppdater_kilde_feil(db_sti, kilde_id, feil_melding)` | Skriver feilinformasjon til databasen. |
| `            return 0` | Returnerer 0 nye artikler. |
| `        logger.warning("Feed-advarsel for %s (fortsetter med %d elementer): %s", kilde_navn, len(feed.entries), feil_melding)` | Feedparser klarte å parse elementer til tross for XML-feil — fortsetter med advarsel. |
| `    # Hent kjente URL-er fra databasen for dedup.` | Kommentar. |
| `    # vault_skriver lagrer UUID4 som guid i SQLite, så vi deduper på url-kolonnen` | Kommentar — forklarer dedup-strategi. |
| `    # som alltid inneholder den kanoniske artikkellenkens URL.` | Kommentar fortsetter. |
| `    kjente_urls = _hent_kjente_urls(db_sti, kilde_id)` | Henter alle kjente URL-er for kilden som et set — O(1) oppslagstid. |
| `    nye = 0` | Teller for nye artikler fra denne kilden. |
| `    for entry in feed.entries:` | Itererer over alle feed-elementer. |
| `        guid = getattr(entry, "id", None) or getattr(entry, "link", None)` | Henter feed-elementets unike identifikator. Prøver `id` (GUID/URN) først, deretter `link`. |
| `        if not guid:` | Elementet mangler identifikator — kan ikke dedup. |
| `            logger.warning("Element uten guid/link i %s — hoppes over", kilde_navn)` | Logger advarsel. |
| `            continue` | Hopper til neste element. |
| `        link = getattr(entry, "link", guid)` | Henter artikkellenken. Faller tilbake til GUID hvis `link` mangler. |
| `        # Dedup — kjent URL lagres ikke på nytt` | Kommentar. |
| `        if link in kjente_urls:` | Sjekker mot in-memory set for O(1) ytelse. |
| `            continue` | Allerede lagret — hopper over. |
| `        pub_dato = _hent_publisert(entry)` | Henter publiseringsdato fra feed-elementet. |
| `        # Datointervall-filtrering — utenfor intervall hoppes over stille` | Kommentar. |
| `        if hent_fra and pub_dato and pub_dato < hent_fra:` | For gammel — under nedre grense. |
| `            continue` | Hopper stille over. |
| `        if hent_til and pub_dato and pub_dato > hent_til:` | For ny — over øvre grense. |
| `            continue` | Hopper stille over. |
| `        tittel = getattr(entry, "title", "") or "Uten tittel"` | Henter tittel. Standardverdi `"Uten tittel"` ved manglende felt. |
| `        # Hent full artikkeltekst; fall tilbake til RSS-summary ved feil` | Kommentar. |
| `        innhold = _hent_full_artikkel(link) or _hent_innhold(entry)` | Prøver full tekst fra URL. `_hent_full_artikkel()` returnerer `None` ved feil — `or` aktiverer fallback til RSS-sammendrag. |
| `        publisert_iso = pub_dato.date().isoformat() if pub_dato else None` | Konverterer datetime til ISO-datostreng (YYYY-MM-DD) for lagring. |
| `        try:` | Isolerer lagrings-feil per artikkel. |
| `            lagre_artikkel(` | Kaller vault_skriver for å lagre. |
| `                kilde_id=kilde_id,` | Kilde-ID. |
| `                url=link,` | Artikkelens URL brukes som kanonisk identifikator. |
| `                tittel=tittel,` | Artikkeltittelen. |
| `                innhold=innhold,` | Full tekst eller RSS-sammendrag. |
| `                publisert=publisert_iso,` | Publiseringsdato. |
| `                kildetype="rss",` | Fast kildetype. |
| `                db_sti=db_sti,` | Databasesti. |
| `                vault_rot=vault_rot,` | Vault-rot. |
| `                kilde_mappe=kilde["navn"],` | Vault-undermappe satt til kildenavn (f.eks. `"MIT Tech Review"`). |
| `            )` | Avslutter `lagre_artikkel()`-kallet. |
| `            kjente_urls.add(link)` | Legger URL til in-memory set for å unngå duplikater innen samme kjøring. |
| `            nye += 1` | Øker ny-teller. |
| `            logger.info("Lagret: %s", tittel)` | Logger vellykket lagring. |
| `        except Exception as feil:` | Fanger alle lagrings-feil. |
| `            logger.error("Kunne ikke lagre '%s' fra %s: %s", tittel, kilde_navn, feil)` | Logger feil uten å avbryte øvrige artikler. |
| `    # Vellykket henting — nullstill eventuelle feilfelt` | Kommentar. |
| `    _nullstill_kilde_feil(db_sti, kilde_id)` | Nullstiller `sist_feil_tidsstempel` og `sist_feil_melding` etter vellykket gjennomkjøring. |
| `    logger.info("%s: %d nye artikler", kilde_navn, nye)` | Logger antall nye artikler for denne kilden. |
| `    return nye` | Returnerer antall nye artikler. |

---

### _parse_dato(dato_str)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _parse_dato(dato_str: str) -> datetime:` | Parser ISO-datostreng til UTC-bevisst datetime. |
| `    return datetime.fromisoformat(dato_str).replace(tzinfo=timezone.utc)` | `fromisoformat("2026-01-01")` → naiv datetime; `.replace(tzinfo=timezone.utc)` gjør den UTC-bevisst for sammenligning med `_hent_publisert()`-resultater. |

**Eksempel:** `_parse_dato("2026-04-01")` → `datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)`

---

### _hent_publisert(entry)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _hent_publisert(entry: object) -> datetime \| None:` | Returnerer UTC-bevisst datetime eller `None`. |
| `    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)` | Henter publisert- eller oppdatert-tidsstempel fra feed-elementet. Begge er `time.struct_time` i UTC. |
| `    if parsed is None:` | Ingen dato tilgjengelig. |
| `        return None` | Returnerer `None` — datointervall-sjekken håndterer dette. |
| `    # timegm tolker struct_time som UTC og returnerer Unix-tidsstempel` | Kommentar. |
| `    return datetime.fromtimestamp(timegm(parsed), tz=timezone.utc)` | `timegm()` konverterer `struct_time` til Unix-tidsstempel uten å anta lokal tidssone. `datetime.fromtimestamp(..., tz=timezone.utc)` gir UTC-bevisst datetime. |

> **Begrep — `time.struct_time`**: En C-lignende tidsstruktur med felt som `tm_year`, `tm_mon`, osv. feedparser returnerer alltid `published_parsed` i UTC. `timegm()` er UTC-ekvivalenten til `mktime()` (som antar lokaltid).

---

### _hent_innhold(entry)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _hent_innhold(entry: object) -> str:` | Henter tekstinnhold fra feed-element. Fallback når `_hent_full_artikkel()` feiler. |
| `    # summary er vanligvis RSS <description> eller Atom <summary>` | Kommentar. |
| `    sammendrag = getattr(entry, "summary", None)` | Henter RSS-sammendrag. `getattr` med `None` default unngår `AttributeError`. |
| `    if sammendrag:` | Sammendrag tilgjengelig — brukes som primærkilde. |
| `        return sammendrag` | Returnerer RSS-sammendraget. |
| `    # content er Atom <content> — liste av innholdsobjekter` | Kommentar. |
| `    innhold_liste = getattr(entry, "content", None)` | Henter Atom-innholdsliste. |
| `    if innhold_liste:` | Innhold tilgjengelig. |
| `        return innhold_liste[0].get("value", "") if isinstance(innhold_liste[0], dict) else ""` | Henter `value`-feltet fra første innholdsobjekt. Sjekker `isinstance` for å unngå feil på uventet type. |
| `    return ""` | Tom streng som siste fallback. |

---

### _hent_full_artikkel(url)

Henter og konverterer full artikkeltekst fra artikkelens URL. Returnerer `None` ved nettverksfeil eller manglende innhold.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _hent_full_artikkel(url: str) -> str \| None:` | Returnerer Markdown-streng eller `None`. |
| `    try:` | Isolerer nettverksfeil. |
| `        respons = httpx.get(url, follow_redirects=True, timeout=15)` | HTTP GET med redirect-følging og 15 sekunders timeout. |
| `        respons.raise_for_status()` | Kaster `httpx.HTTPStatusError` for 4xx/5xx-statuskoder. |
| `    except Exception as feil:` | Fanger nettverksfeil, timeout, HTTP-feil o.l. |
| `        logger.warning("Kunne ikke hente full tekst fra %s: %s", url, feil)` | Logger advarsel — fallback til RSS-sammendrag aktiveres. |
| `        return None` | Signaliserer at full tekst ikke er tilgjengelig. |
| `    suppe = BeautifulSoup(respons.text, "html.parser")` | Parser HTML-responsen. `"html.parser"` er Pythons innebygde parser. |
| `    hovedelement = suppe.find("article") or suppe.find("main") or suppe.find("body")` | Prioritert søk etter hovedinnhold: `<article>` er semantisk korrekt for artikler; `<main>` er alternativ; `<body>` som siste utvei. |
| `    if hovedelement is None:` | Ingen relevant HTML-element funnet. |
| `        return None` | Returnerer `None`. |
| `    tekst = markdownify(str(hovedelement), heading_style="ATX").strip()` | Konverterer HTML til Markdown. `heading_style="ATX"` gir `# H1` i stedet for underline-stil. `.strip()` fjerner ledende/etterfølgende mellomrom. |
| `    return tekst or None` | Returnerer Markdown-teksten, eller `None` hvis resultatet er tomt. |

---

### _hent_kjente_urls(db_sti, kilde_id)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _hent_kjente_urls(db_sti: Path, kilde_id: int) -> set[str]:` | Returnerer sett av URL-strenger for rask dedup. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Åpner tilkobling. |
| `        rader = tilkobling.execute(` | SELECT. |
| `            "SELECT url FROM elementer WHERE kilde_id = ?", (kilde_id,)` | Henter alle URL-er for kilden. |
| `        ).fetchall()` | Henter alle rader. |
| `    return {rad[0] for rad in rader}` | Set comprehension — konverterer liste av en-element-tupler til sett av strenger for O(1) oppslagstid. |

---

### _oppdater_kilde_feil(db_sti, kilde_id, feil_melding)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _oppdater_kilde_feil(db_sti: Path, kilde_id: int, feil_melding: str) -> None:` | Skriver feilinformasjon til `kilder`-tabellen. |
| `    tidsstempel = datetime.now(timezone.utc).isoformat()` | Genererer ISO 8601-tidsstempel i UTC, f.eks. `"2026-05-09T12:00:00+00:00"`. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Åpner tilkobling. |
| `        tilkobling.execute(` | Kjører UPDATE. |
| `            "UPDATE kilder SET sist_feil_tidsstempel = ?, sist_feil_melding = ? WHERE id = ?",` | Oppdaterer to feil-kolonner for kilden. |
| `            (tidsstempel, feil_melding, kilde_id),` | Parameterverdier. |
| `        )` | Avslutter execute-kallet. |

---

### _nullstill_kilde_feil(db_sti, kilde_id)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _nullstill_kilde_feil(db_sti: Path, kilde_id: int) -> None:` | Nullstiller feilfelt etter vellykket henting. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Åpner tilkobling. |
| `        tilkobling.execute(` | Kjører UPDATE. |
| `            "UPDATE kilder SET sist_feil_tidsstempel = NULL, sist_feil_melding = NULL WHERE id = ?",` | Setter begge felt til `NULL`. |
| `            (kilde_id,),` | Kilde-ID som parameter. |
| `        )` | Avslutter execute-kallet. |

---

## 5. Feilhåndtering

| Feilsituasjon | Håndtering | Resultat for systemet |
|---|---|---|
| Feed-URL utilgjengelig (nettverksfeil) | feedparser returnerer `bozo=True`, tom `entries`-liste → `_oppdater_kilde_feil()`, `return 0` | Kilden hoppes over. Feilinformasjon lagres i DB. |
| XML-valideringsfeil, men elementer tilgjengelig | `feed.bozo=True`, `len(feed.entries) > 0` → `logger.warning`, fortsetter | Logger advarsel. Elementer prosesseres normalt. |
| Element uten guid/link | `if not guid: continue` | Elementet hoppes stille over. Logger `WARNING`. |
| Allerede lagret URL | `if link in kjente_urls: continue` | Stille dedup. Ingen logging. |
| Publiseringsdato mangler | `pub_dato = None` → datointervall-sjekk utløses ikke | Artikkelen lagres uten datointervall-filtrering. |
| Full artikkeltekst kan ikke hentes | `_hent_full_artikkel()` returnerer `None` → fallback til `_hent_innhold(entry)` | RSS-sammendrag brukes. Logger `WARNING` med URL. |
| `lagre_artikkel()` kaster unntak | `except Exception: logger.error(...)` | Feilen isoleres. Neste artikkel prosesseres normalt. |
| Per-kilde-feil rullerer ikke tilbake | Ingen transaksjonsgrense over kilde-grensen | Delvis lagrede resultater fra én kilde påvirker ikke de øvrige. |

---

## 6. Eksterne avhengigheter

| Pakke | Bruk i denne filen | Installasjon |
|---|---|---|
| `feedparser` | `feedparser.parse(url)` — henter og tolker RSS/Atom-feeder | `uv add feedparser` |
| `httpx` | `httpx.get()` — henter full artikkeltekst fra kildelenker | `uv add httpx` |
| `beautifulsoup4` | `BeautifulSoup` — parser HTML og ekstraher `<article>`/`<main>` | `uv add beautifulsoup4` |
| `markdownify` | `markdownify()` — konverterer HTML til Markdown | `uv add markdownify` |
| `python-dotenv` | `load_dotenv()` — laster miljøvariabler | `uv add python-dotenv` |
| `intelligence_monitor.innhenter.vault_skriver` | `lagre_artikkel()` — lagrer artikler i vault og SQLite | Del av prosjektet |

---

## 7. Oppsummering

**Funksjonstabell:**

| Funksjon | Ansvar |
|---|---|
| `innhent_alle()` | Koordinerer innhenting fra alle aktive RSS-kilder. |
| `_hent_aktive_rss_kilder()` | Leser aktive RSS-kilder fra `kilder`-tabellen. |
| `_innhent_kilde()` | Innhenter og lagrer nye artikler fra én kilde. |
| `_parse_dato()` | Konverterer ISO-datostreng til UTC-bevisst datetime. |
| `_hent_publisert()` | Trekker ut publiseringsdato fra feed-element. |
| `_hent_innhold()` | Henter RSS-sammendrag eller Atom-innhold som fallback-tekst. |
| `_hent_full_artikkel()` | Henter og Markdown-konverterer full artikkeltekst fra URL. |
| `_hent_kjente_urls()` | Laster eksisterende URL-er for dedup innen én kjøring. |
| `_oppdater_kilde_feil()` | Skriver feilinformasjon til `kilder`-tabellen. |
| `_nullstill_kilde_feil()` | Nullstiller feilfelt etter vellykket henting. |

**Kjørbart eksempel:**

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Valgfritt: begrens til spesifikt datointervall
os.environ["HENT_FRA"] = "2026-04-01"
os.environ["HENT_TIL"] = "2026-05-01"

from intelligence_monitor.innhenter.rss import innhent_alle

antall_nye = innhent_alle()
print(f"Hentet {antall_nye} nye artikler")
```

Alternativt via `kjører.py` eller Makefile:

```bash
make innhent
python -m intelligence_monitor.innhenter.kjører
```
