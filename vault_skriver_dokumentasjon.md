# `vault_skriver.py` — Teknisk kodedokumentasjon

> Obsidian-vault og SQLite — atomisk lagringsmodul

---

## Innhold

1. [Overordnet beskrivelse](#1-overordnet-beskrivelse)
2. [Importer og moduloppsett](#2-importer-og-moduloppsett)
3. [Offentlig funksjon: lagre\_artikkel()](#3-offentlig-funksjon-lagre_artikkel)
4. [Hjelpefunksjoner](#4-hjelpefunksjoner)
5. [Feilhåndtering og rollback-strategi](#5-feilhåndtering-og-rollback-strategi)
6. [Eksterne avhengigheter](#6-eksterne-avhengigheter)
7. [Oppsummering](#7-oppsummering)

---

## 1. Overordnet beskrivelse

`vault_skriver.py` er kjernemodelen for atomisk lagring av artikler i et Obsidian-vault med SQLite som indeks. Alle innhentingskanaler — RSS-feeds, nettskraping, YouTube-transkripsjon, eller manuell klipping — bruker denne modulen som sin ene skrivevei.

Filen løser tre konkrete problemer:

- **Konsistens:** alle artikler skrives på identisk måte uansett kilde
- **Atomisitet:** hvis SQLite-skriving feiler rulles Markdown-filen tilbake slik at disk og database aldri er ute av synk
- **Selvstendige filer:** bilder lastes ned lokalt og URL-er i innholdet erstattes, slik at vaultet fungerer offline

> **Begrep — Obsidian vault:** En mappe med Markdown-filer som Obsidian (en notatapplikasjon) leser som en kunnskapsbase. Frontmatter er YAML-metadata øverst i en `.md`-fil, avgrenset av `---`-linjer.

> **Begrep — Atomisk operasjon:** En operasjon som enten fullføres helt eller ikke i det hele tatt — ingen halvferdige tilstander. Kjent fra database-transaksjoner (ACID).

---

### 1.1 Flyt og sammenhenger

```
KALLER:  lagre_artikkel(kilde_id, url, tittel, innhold, publisert, ...)
         │
         ▼
  ┌──────────────────────────────┐
  │  Steg 1: Generer UUID        │  → element_id (full UUID4)
  └──────────────┬───────────────┘
                 │
  ┌──────────────▼───────────────┐
  │  Steg 2: Bygg mappe + slug   │  → artikkel_mappe, filnavn
  └──────────────┬───────────────┘
                 │
  ┌──────────────▼───────────────┐
  │  Steg 3: Last ned bilder     │  → _behandle_bilder()
  │           Erstatt URL-er     │     → _last_ned_bilde() × N
  └──────────────┬───────────────┘
                 │
  ┌──────────────▼───────────────┐
  │  Steg 4: Bygg + skriv .md    │  → _bygg_markdown() → fil_sti.write_text()
  └──────────────┬───────────────┘
                 │
  ┌──────────────▼───────────────┐    ╔══════════════════╗
  │  Steg 5: Skriv til SQLite    │    ║  FEIL?           ║
  │          _skriv_til_db()     │───►║  slett .md       ║
  └──────────────┬───────────────┘    ║  re-raise error  ║
                 │                    ╚══════════════════╝
         ▼
  RETURNERER: element_id (UUID4-streng)
```

---

### 1.2 Filstruktur som produseres

```
vault/
├── artikler/
│   ├── kilde_mappe/          ← hvis kilde_mappe er oppgitt
│   │   └── a1b2c3d4-tittel-pa-artikkelen.md
│   └── a1b2c3d4-tittel.md    ← uten kilde_mappe
└── ressurser/
    └── bilder/
        └── e5f6g7h8.jpg      ← nedlastede bilder
```

Tilsvarende SQL-rad i `elementer`-tabellen:

```
kilde_id │ guid              │ url         │ tittel │ publisert  │ hentet                    │ vault_sti                          │ bilder_json
─────────┼───────────────────┼─────────────┼────────┼────────────┼───────────────────────────┼────────────────────────────────────┼──────────────────────
42       │ a1b2c3d4-...-uuid │ https://... │ Tittel │ 2024-01-15 │ 2024-01-16T08:30:00+00:00 │ artikler/kilde/a1b2c3d4-tittel.md  │ ["e5f6g7h8.jpg"]
```

---

## 2. Importer og moduloppsett

| Kodelinje | Forklaring |
|---|---|
| `from __future__ import annotations` | Aktiverer utsatt type-evaluering (PEP 563). Gjør at type hints som `str \| None` fungerer i Python 3.9 og eldre uten å importere `Optional` fra `typing`. |
| `import json` | Standardbibliotek. Brukes til å serialisere lister med bildefilnavn til JSON-streng for lagring i SQLite. |
| `import logging` | Standardbibliotek. Gir strukturert logging med nivåer (DEBUG, INFO, WARNING, ERROR). Brukes for å logge advarsler om bilder som ikke kan lastes ned. |
| `import re` | Standardbibliotek for regulære uttrykk. Brukes til å finne bilde-URL-er i innhold og rydde slugs. |
| `import sqlite3` | Standardbibliotek for SQLite-tilgang. Brukes for å skrive artikkelrader til databasen. |
| `import unicodedata` | Standardbibliotek. Brukes for NFKD-normalisering av titler slik at æøå konverteres til ASCII for filnavn. |
| `import uuid` | Standardbibliotek. Genererer UUID4-identifikatorer — globalt unike tilfeldige ID-er. |
| `from datetime import datetime, timezone` | `datetime`: for å hente nåværende tidspunkt. `timezone`: for å sikre UTC i tidsstempel. |
| `from pathlib import Path` | Objektorientert filstimanipulasjon (Python 3.4+). Tryggere og mer lesbar enn `os.path`. |
| `import httpx` | Tredjeparts HTTP-klient. Brukes for å laste ned bilder fra nettet. Støtter timeout og redirect-håndtering. |
| `from urllib.parse import urljoin` | Standardbibliotek. Kombinerer en base-URL og en relativ URL til en absolutt URL. |
| `logger = logging.getLogger(__name__)` | Oppretter et logger-objekt med modulens eget navn (`vault_skriver`) som identifikator. Lar konfigurasjonen styres fra toppen av applikasjonen. |

---

## 3. Offentlig funksjon: `lagre_artikkel()`

`lagre_artikkel()` er den eneste offentlige funksjonen i modulen — det er her alle innhentingskanaler kaller inn. Den orkestrerer hele skrivesekvensen og sørger for atomisitet via rollback.

### 3.1 Signatur

```python
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
    kilde_mappe: str | None = None,
) -> str:
```

### 3.2 Parametre

| Parameter | Forklaring |
|---|---|
| `kilde_id: int` | Primærnøkkel fra `kilder`-tabellen i SQLite. Kobler artikkelen til dens kilde. |
| `url: str` | Artikkelen sin opprinnelige URL. Lagres i frontmatter og i databasen. |
| `tittel: str` | Artikkeltittel. Brukes som H1-overskrift i `.md`-filen og som filnavnkomponent. |
| `innhold: str` | Markdown-tekst fra innhentingskanalen. Bilder i denne teksten vil lastes ned og erstattes. |
| `publisert: str \| None` | ISO-dato eller datetime fra kilden, f.eks. `'2024-01-15'`. Kan være `None` hvis kilden ikke oppgir dato. |
| `kildetype: str` | Tekststreng som beskriver kanaltype: `'rss'`, `'manuell'`, `'youtube'`, osv. Lagres i frontmatter. |
| `db_sti: Path` | Filsti til SQLite-databasefilen, f.eks. `Path('/data/artikler.db')`. |
| `vault_rot: Path` | Rot-mappe for Obsidian-vaultet, f.eks. `Path('/home/user/vault')`. |
| `klippet_dato: str \| None` | Valgfri. ISO-dato for manuell klipping. Brukes som fallback for `publisert` hvis `publisert` er `None`. |
| `kilde_mappe: str \| None` | Valgfri. Navn på kildemappe — artikkelen lagres i `artikler/{kilde_mappe}/`. Påvirker også relativ bildesti. |

### 3.3 Linje-for-linje

| Kodelinje | Forklaring |
|---|---|
| `element_id = str(uuid.uuid4())` | Genererer en ny UUID4 (128-bit tilfeldig tall) og konverterer til streng, f.eks. `'a1b2c3d4-e5f6-7890-abcd-ef1234567890'`. Artikkelen sin globalt unike ID. |
| `uuid_kort = element_id.replace("-", "")[:8]` | Fjerner bindestrekene fra UUID og tar de første 8 tegnene, f.eks. `'a1b2c3d4'`. Brukes i filnavnet for korthet. |
| `slug = _lag_slug(tittel)` | Kaller intern hjelpefunksjon som konverterer tittelen til en URL-trygg slug. Se [seksjon 4.1](#41-_lag_slugtittel--str). |
| `filnavn = f"{uuid_kort}-{slug}.md"` | Setter sammen filnavn: kortUUID + bindestrek + slug + `.md`. Eks: `'a1b2c3d4-min-artikkel-om-ai.md'`. |
| `if kilde_mappe:` | Sjekker om kallstedet oppga et kildenavn. Bestemmer undermappe og relativ bildesti. |
| `artikkel_mappe = vault_rot / "artikler" / kilde_mappe` | Bygger målmappe med kildenavn som undermappe. `Path /` operator tilsvarer `os.path.join()`. |
| `bilde_prefix = "../../ressurser/bilder"` | Relativ sti fra artikkelmappe til bildemappen. To nivåer opp fordi filen er i `artikler/kilde/`. |
| `else:` | Kjøres hvis `kilde_mappe` er `None` eller tom streng. |
| `artikkel_mappe = vault_rot / "artikler"` | Filen legges direkte i `artikler/` uten undermappe. |
| `bilde_prefix = "../ressurser/bilder"` | Kun ett nivå opp siden filen er i `artikler/` direkte. |
| `artikkel_mappe.mkdir(parents=True, exist_ok=True)` | Oppretter mappestien på disk. `parents=True` oppretter mellomliggende mapper. `exist_ok=True` feiler ikke hvis mappen allerede finnes. |
| `innhold_behandlet, bildefilnavn = _behandle_bilder(...)` | Laster ned alle bilder i innholdet og erstatter URL-ene. Returnerer endret innholdsstreng og liste med filnavn. |
| `effektiv_publisert = publisert or klippet_dato` | Python `or` kort-slutning: bruker `publisert` hvis den er truthy, ellers `klippet_dato`. Gir ett kanonisk dato-felt. |
| `md_innhold = _bygg_markdown(...)` | Kaller intern hjelpefunksjon som setter sammen frontmatter + H1-tittel + innhold til komplett `.md`-dokument. |
| `fil_sti = artikkel_mappe / filnavn` | Bygger full filsti for den ferdige Markdown-filen. |
| `fil_sti.write_text(md_innhold, encoding="utf-8")` | Skriver Markdown-dokumentet til disk med UTF-8-koding. **Steg 4 i skrivesekvensen — filen finnes nå på disk.** |
| `hentet = datetime.now(timezone.utc).isoformat()` | Henter nåværende UTC-tidspunkt og konverterer til ISO 8601-streng, f.eks. `'2024-01-16T08:30:00+00:00'`. Tidssone-bevisst. |
| `if kilde_mappe: vault_sti = ...` | Bygger relativ vault-sti for databaseraden. Posix-format (skråstrek) uavhengig av OS. |
| `bilder_json = json.dumps(...) if bildefilnavn else None` | Serialiserer bildeliste til JSON-streng kun hvis listen ikke er tom. `None` hvis ingen bilder ble lastet ned. |
| `try: _skriv_til_db(...)` | Forsøker å skrive raden til SQLite. Wrappet i `try/except` for rollback-logikk. |
| `except sqlite3.Error:` | Fanger alle SQLite-feil (`IntegrityError`, `OperationalError`, osv.). |
| `fil_sti.unlink(missing_ok=True)` | **Rollback:** sletter `.md`-filen som ble skrevet i steg 4. `missing_ok=True` feiler ikke selv om filen allerede er borte. |
| `raise` | Kaster SQLite-feilen videre opp til kalleren. Ingen stille svelging av feil. |
| `return element_id` | Returnerer den fulle UUID4-strengen. Kallstedet kan bruke denne til videre referanser. |

---

## 4. Hjelpefunksjoner

### 4.1 `_lag_slug(tittel)` → `str`

Konverterer en artikkeltittel til en URL-trygg slug egnet for filnavn.

> **Begrep — NFKD-normalisering:** En Unicode-normaliseringsform som dekomponerer sammensatte tegn til grunntegn + diakritiske tegn. `'ø'` blir til `'o'` + combining-tegn som deretter filtreres ut av ASCII-konvertering.

**Eks:** `'Norsk økonomi i 2024!'` → `'norsk-konomi-i-2024'`

| Kodelinje | Forklaring |
|---|---|
| `normalisert = unicodedata.normalize("NFKD", tittel)` | Dekomponerer Unicode-tegn. `'ø'` → `o` + combining-tegn. Gjør at æøå kan strippes til ASCII-ekvivalenter. |
| `ascii_bytes = normalisert.encode("ascii", errors="ignore")` | Koder til ASCII-bytes og kaster tegn som ikke finnes i ASCII (combining-tegnene). Returnerer `bytes`-objekt. |
| `slug = ascii_bytes.decode("ascii").lower()` | Dekoder bytes tilbake til streng og konverterer til lowercase. |
| `slug = slug.replace(" ", "-").replace("_", "-").replace(".", "-")` | Erstatter mellomrom, understrek og punktum med bindestreker — standard slug-separatorer. |
| `slug = re.sub(r"[^a-z0-9-]", "", slug)` | Regex: fjerner alle tegn som ikke er bokstav, tall eller bindestrek. `!`, `?`, `#` osv. forsvinner. |
| `slug = re.sub(r"-+", "-", slug).strip("-")` | Kollapser flere påfølgende bindestreker til én, og fjerner bindestreker i starten/slutten. |
| `return slug or "artikkel"` | Returnerer slugen. Fallback til `'artikkel'` hvis tittelen var tom eller kun spesialtegn. |

**Transformasjonen trinn for trinn:**

| Steg | Verdi |
|---|---|
| Input | `"Norsk økonomi — 3 trender i 2024!"` |
| NFKD | `"Norsk økonomi — 3 trender i 2024!"` (ø dekomponert) |
| ASCII encode/decode | `"Norsk konomi  3 trender i 2024!"` |
| `.lower()` | `"norsk konomi  3 trender i 2024!"` |
| Erstatt mellomrom/`.` m.m. | `"norsk-konomi--3-trender-i-2024!"` |
| Fjern ulovlige tegn | `"norsk-konomi--3-trender-i-2024"` |
| Kollaps `--` → `-` | `"norsk-konomi-3-trender-i-2024"` |

---

### 4.2 `_bygg_markdown(...)` → `str`

Bygger det ferdige Markdown-dokumentet med YAML-frontmatter, H1-overskrift og artikkeltekst. Returnerer en streng klar for skriving til disk.

| Kodelinje | Forklaring |
|---|---|
| `linjer = ["---", ...]` | Starter en liste med frontmatter-linjer. `'---'` er YAML-blokkens åpningsmarkør. |
| `f"element_id: {element_id}"` | Legger til artikkelen sin UUID4 som YAML-felt. Brukes av Obsidian til søk og referanser. |
| `f"url: {url}"` | Original kildeadresse. Gjør det mulig å gå tilbake til kilden. |
| `f"kildetype: {kildetype}"` | Kanaltype-streng. Brukes til filtrering i Obsidian og SQLite-spørringer. |
| `if klippet_dato is not None:` | Betinget: `klippet_dato`-feltet legges kun til for manuelt klippede artikler. |
| `if publisert is not None:` | Betinget: `publisert` utelates hvis ingen dato er kjent — unngår tomme YAML-felt. |
| `linjer.append("---")` | Avslutter YAML-blokken med lukkemarkør. |
| `frontmatter = "\n".join(linjer)` | Setter linjene sammen med linjeskift til én frontmatter-streng. |
| `return f"{frontmatter}\n\n# {tittel}\n\n{innhold}\n"` | Returnerer hele dokumentet: frontmatter + to linjeskift + H1-tittel + to linjeskift + innhold + avsluttende linjeskift. |

**Eksempel output** (manuelt klippet artikkel):

```yaml
---
element_id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
url: https://example.com/artikkel
kildetype: manuell
klippet_dato: 2024-01-16
publisert: 2024-01-15
---

# Tittelen på artikkelen

Her er artikkelteksten i Markdown...
```

---

### 4.3 `_behandle_bilder(innhold, vault_rot, base_url, bilde_prefix)` → `tuple[str, list[str]]`

Skanner artikkelteksten for bildereferanser i både Markdown-syntaks og HTML, laster ned hvert unike bilde, og erstatter URL-ene i teksten med lokale relative stier.

> **Begrep — Regulært uttrykk (regex):** Et mønster-språk for å søke i tekst. `r'![...](...)'` matcher Markdown-bildesyntaks. `re.compile()` kompilerer mønsteret til et raskt søkeobjekt.

| Kodelinje | Forklaring |
|---|---|
| `bilde_mappe = vault_rot / "ressurser" / "bilder"` | Bygger sti til bildemappe. Alle nedlastede bilder havner her uavhengig av kilde. |
| `bilde_mappe.mkdir(parents=True, exist_ok=True)` | Oppretter bildemappen hvis den ikke finnes. Trygt å kalle gjentatte ganger. |
| `md_monster = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")` | Kompilert regex for Markdown-bilder. Gruppe 1: alt-tekst. Gruppe 2: URL. Matcher f.eks. `![bilde](https://...)`. |
| `html_monster = re.compile(r'<img\s+[^>]*src=["\'](...)["\']]', re.IGNORECASE)` | Kompilert regex for HTML `img`-tagger. Gruppe 1: `src`-URL. Matcher `<img src="...">` og variasjoner. |
| `url_til_lokal: dict[str, str] = {}` | Tom ordbok som mapper original bilde-URL → lokal relativ sti. Dedup: samme bilde lastes kun ned én gang. |
| `for treff in md_monster.finditer(innhold):` | Itererer over alle Markdown-bildematches i teksten. |
| `bilde_url = treff.group(2)` | Henter URL fra andre fangstgruppe i regex-matchen. |
| `if bilde_url not in url_til_lokal:` | Hopper over URL-er som allerede er prosessert (dedup). |
| `abs_url = urljoin(base_url, bilde_url) if base_url else bilde_url` | Gjør relative URL-er absolutte. `urljoin('https://ex.com/art/', '../img.jpg')` → `'https://ex.com/img.jpg'`. |
| `lokal = _last_ned_bilde(abs_url, ...)` | Forsøker å laste ned bildet. Returnerer lokal sti eller `None` ved feil. |
| `if lokal: url_til_lokal[bilde_url] = lokal` | Registrerer mapping kun hvis nedlasting lyktes. |
| *(tilsvarende for `html_monster`)* | Samme prosess gjentas for HTML `img src`-attributter. |
| `innhold = innhold.replace(original_url, lokal_sti)` | Tekstersetting: alle forekomster av original-URL erstattes med lokal relativ sti. |
| `bildefilnavn.append(Path(lokal_sti).name)` | Henter kun filnavnet (f.eks. `'e5f6g7h8.jpg'`) fra full sti. |
| `return innhold, bildefilnavn` | Returnerer endret innholdsstreng og liste med filnavn. |

**Teksterstatning i praksis:**

| Innhold FØR | Innhold ETTER |
|---|---|
| `![graf](https://ex.com/graf.png)` | `![graf](../../ressurser/bilder/a1b2.png)` |
| `<img src="https://ex.com/logo.jpg">` | `<img src="../../ressurser/bilder/c3d4.jpg">` |

---

### 4.4 `_last_ned_bilde(url, bilde_mappe, bilde_prefix)` → `str | None`

Laster ned ett enkeltbilde fra nettet, lagrer det lokalt med et UUID-basert filnavn, og returnerer den relative stien. Returnerer `None` og logger advarsel ved ethvert problem.

| Kodelinje | Forklaring |
|---|---|
| `if not url.startswith(("http://", "https://"))` | Validerer at URL-en bruker et støttet protokollskjema. `data:`, `file://` osv. avvises stille. |
| `logger.warning("Ugyldig bilde-URL ...")` | Logger advarsel på WARNING-nivå. Kallestedet ser feilen i loggfilen uten at programmet krasjer. |
| `return None` | Returnerer `None` for å signalere at nedlasting ikke ble utført. |
| `respons = httpx.get(url, follow_redirects=True, timeout=10.0)` | HTTP GET-forespørsel. `follow_redirects=True`: følger 301/302-videresendinger. `timeout=10.0`: avbryter etter 10 sekunder. |
| `respons.raise_for_status()` | Kaster `httpx.HTTPStatusError` hvis HTTP-statuskoden er 4xx eller 5xx (f.eks. 404, 403). |
| `except Exception as feil:` | Fanger alle unntak — nettverksfeil, timeout, HTTP-feil, osv. |
| `logger.warning("Kunne ikke laste ned ...")` | Logger advarsel med URL og feilmelding. Programmet fortsetter. |
| `innholdstype = respons.headers.get("content-type", "")` | Henter `Content-Type`-headeren, f.eks. `'image/jpeg; charset=utf-8'`. Fallback til tom streng. |
| `ext = _finn_ext(innholdstype, url)` | Delegerer filendelse-beslutning til `_finn_ext()`. Se [seksjon 4.5](#45-_finn_extinnholdstype-url--str). |
| `filnavn = f"{uuid.uuid4().hex[:8]}.{ext}"` | Genererer unikt filnavn: 8 hex-tegn fra ny UUID + filendelse. Eks: `'a1b2c3d4.jpg'`. |
| `(bilde_mappe / filnavn).write_bytes(respons.content)` | Skriver bildets rå bytes til disk. `.content` er `bytes`-objektet fra HTTP-svaret. |
| `return f"{bilde_prefix}/{filnavn}"` | Returnerer relativ sti fra artikkelens plassering til bildet. |

---

### 4.5 `_finn_ext(innholdstype, url)` → `str`

Bestemmer riktig filendelse for et nedlastet bilde. Prioriterer `Content-Type`-headeren, faller tilbake til URL-suffiks, og bruker `'bin'` som siste utvei.

| Kodelinje | Forklaring |
|---|---|
| `type_til_ext = {"image/jpeg": "jpg", ...}` | Oppslagstabell (dict) som mapper MIME-type til filendelse. Dekker de vanligste bildeformatene. |
| `mime = innholdstype.split(";")[0].strip().lower()` | Renser `Content-Type`: splitter på semikolon for å fjerne params som `charset=utf-8`, striper whitespace, konverterer til lowercase. |
| `if mime in type_til_ext: return type_til_ext[mime]` | Rask oppslag: hvis MIME-typen er kjent returneres riktig endelse direkte. |
| `url_sti = url.split("?")[0]` | Fjerner query-parametre fra URL (alt etter `?`). Eks: `'.../bilde.png?v=2'` → `'.../bilde.png'`. |
| `siste_del = url_sti.split("/")[-1]` | Henter siste path-segment — vanligvis filnavnet. Eks: `'bilde.png'`. |
| `if "." in siste_del:` | Sjekker om det finnes en filendelse. |
| `ext = siste_del.rsplit(".", 1)[-1].lower()` | Splitter på siste punktum og tar det som kommer etter. `rsplit` med `maxsplit=1` håndterer filnavn med flere punktum. |
| `if ext in {"jpg", "jpeg", ...}: return ...` | Sjekker at endelsen er en kjent bildetype. `'jpeg'` normaliseres til `'jpg'`. |
| `return "bin"` | Fallback-endelse hvis ingen metode lyktes. `'bin'` = binær fil — indikerer ukjent format. |

---

### 4.6 `_skriv_til_db(...)` → `None`

Skriver én rad til `elementer`-tabellen i SQLite-databasen. Bruker kontekstmanager (`with`-blokk) for automatisk commit ved suksess og rollback ved unntak.

> **Begrep — `PRAGMA foreign_keys = ON`:** SQLite har fremmednøkkel-støtte deaktivert som standard. Denne linjen aktiverer det for tilkoblingen, slik at `kilde_id` må referere en eksisterende rad i `kilder`-tabellen.

> **Begrep — Parameterisert SQL (`?` placeholders):** Verdier settes inn via parameter-tuple, ikke direkte string-interpolering. Hindrer SQL-injeksjon og håndterer spesialtegn korrekt.

| Kodelinje | Forklaring |
|---|---|
| `with sqlite3.connect(db_sti) as tilkobling:` | Åpner tilkobling til SQLite-filen. `with`-blokken sikrer automatisk commit ved slutt og rollback ved unntak. |
| `tilkobling.execute("PRAGMA foreign_keys = ON")` | Aktiverer fremmednøkkel-validering for denne tilkoblingen. |
| `tilkobling.execute("INSERT INTO elementer ...")` | Kjører `INSERT`-setningen med parameteriserte verdier. |
| `(kilde_id, guid, url, tittel, publisert, hentet, vault_sti, bilder_json)` | Parametertupelen i samme rekkefølge som `?`-plassholderne i SQL. Python-verdiene serialiseres automatisk til SQL-typer. |

**Forventet databaseskjema** (ikke definert i denne filen, men antatt av koden):

```sql
CREATE TABLE elementer (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  kilde_id    INTEGER NOT NULL REFERENCES kilder(id),
  guid        TEXT    NOT NULL UNIQUE,
  url         TEXT    NOT NULL,
  tittel      TEXT    NOT NULL,
  publisert   TEXT,
  hentet      TEXT    NOT NULL,
  vault_sti   TEXT    NOT NULL,
  bilder_json TEXT
);
```

---

## 5. Feilhåndtering og rollback-strategi

Modulen opererer med to distinkte feilhåndteringsstrategier avhengig av hva som feiler:

| Feilsituasjon | Håndtering | Resultat for systemet |
|---|---|---|
| Bildenedlasting feiler | `logger.warning()` + returnerer `None` | Artikkelen lagres med original bilde-URL intakt |
| Ugyldig bilde-URL | `logger.warning()` + returnerer `None` | Som over |
| SQLite-feil etter `.md` er skrevet | `fil_sti.unlink()` + `raise` | Disk og DB er synkrone — ingen halvferdig tilstand |
| Mappe kan ikke opprettes | Kaster `OSError` (ikke fanget) | Propagerer opp til kalleren |

> ⚠️ **Viktig:** Feil som oppstår FØR `.md`-filen er skrevet (f.eks. i `_behandle_bilder`) rulles ikke tilbake — det er ingenting å rulle tilbake. Rollback-logikken gjelder kun for tilfellet der filen er skrevet men SQLite-skriving feiler.

---

## 6. Eksterne avhengigheter

| Pakke | Bruk i denne filen | Installasjon |
|---|---|---|
| `httpx` | Laster ned bilder i `_last_ned_bilde()`. Støtter timeout og redirect. | `pip install httpx` |
| `pathlib.Path` | Filstimanipulasjon gjennom hele modulen | Standardbibliotek |
| `sqlite3` | Databaseskriving i `_skriv_til_db()` | Standardbibliotek |
| `unicodedata`, `uuid`, `re`, `json`, `logging`, `datetime` | Se [seksjon 2](#2-importer-og-moduloppsett) | Standardbibliotek |

---

## 7. Oppsummering

`vault_skriver.py` løser ett problem: sørg for at en artikkel enten er fullstendig lagret — med Markdown-fil på disk og rad i database — eller ikke lagret i det hele tatt.

| Funksjon | Ansvar |
|---|---|
| `lagre_artikkel()` | Offentlig API. Orkestrerer hele skrivesekvensen med rollback-garanti. |
| `_lag_slug()` | Konverterer tittel til filnavn-trygt slug med ASCII-fallback for æøå. |
| `_bygg_markdown()` | Bygger komplett `.md`-dokument med YAML-frontmatter. |
| `_behandle_bilder()` | Skanner innhold for bilder, laster ned, erstatter URL-er. |
| `_last_ned_bilde()` | Laster ned ett bilde med feilhåndtering og unik filnavngiving. |
| `_finn_ext()` | Bestemmer filendelse fra `Content-Type` eller URL-suffix. |
| `_skriv_til_db()` | Atomisk `INSERT` til SQLite med fremmednøkkel-validering. |

**Typisk bruk:**

```python
from vault_skriver import lagre_artikkel
from pathlib import Path

element_id = lagre_artikkel(
    kilde_id=42,
    url="https://example.com/artikkel",
    tittel="Min første artikkel",
    innhold="## Intro\n\nTekst med ![bilde](https://ex.com/b.png)",
    publisert="2024-01-15",
    kildetype="rss",
    db_sti=Path("data/artikler.db"),
    vault_rot=Path("vault"),
    kilde_mappe="example-com",
)
print(element_id)  # 'a1b2c3d4-...-uuid4'
```
