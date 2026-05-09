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
  ┌──────────────▼───────────────┐    ╔═══════════════════╗
  │  Steg 5: Skriv til SQLite    │    ║  FEIL?            ║
  │          _skriv_til_db()     │───►║  slett .md        ║
  └──────────────┬───────────────┘    ║  re-raise error   ║
                 │                    ╚═══════════════════╝
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
kilde_id │ guid              │ publisert  │ hentet                    │ vault_sti                         │ bilder_json
─────────┼───────────────────┼────────────┼───────────────────────────┼───────────────────────────────────┼──────────────────
42       │ a1b2c3d4-...-uuid │ 2024-01-15 │ 2024-01-16T08:30:00+00:00 │ artikler/kilde/a1b2c3d4-tittel.md │ ["e5f6g7h8.jpg"]
```

---

## 2. Importer og moduloppsett

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `from __future__ import annotations` | Aktiverer utsatt type-evaluering (PEP 563). Gjør at type hints som `str \| None` fungerer i Python 3.9 og eldre uten å importere `Optional` fra `typing`. |
| `import json` | Standardbibliotek. Brukes til å serialisere lister med bildefilnavn til JSON-streng for lagring i SQLite. |
| `import logging` | Standardbibliotek. Gir strukturert logging med nivåer (DEBUG, INFO, WARNING, ERROR). Brukes for å logge advarsler om bilder som ikke kan lastes ned. |
| `import re` | Standardbibliotek for regulære uttrykk. Brukes til å finne bilde-URL-er i innhold og rydde slugs. |
| `import sqlite3` | Standardbibliotek for SQLite-tilgang. Brukes for å skrive artikkelrader til databasen. |
| `import unicodedata` | Standardbibliotek. Brukes for NFKD-normalisering av titler slik at æøå konverteres til ASCII for filnavn. |
| `import uuid` | Standardbibliotek. Genererer UUID4-identifikatorer — globalt unike tilfeldige ID-er. |
| `from datetime import datetime, timezone` | `datetime`: for å hente nåværende tidspunkt. `timezone`: for å sikre UTC (Coordinated Universal Time) i tidsstempel. |
| `from pathlib import Path` | Objektorientert filstimanipulasjon (Python 3.4+). Tryggere og mer lesbar enn `os.path`. |
| `import httpx` | Tredjeparts HTTP-klient. Brukes for å laste ned bilder fra nettet. Støtter timeout og redirect-håndtering. |
| `from urllib.parse import urljoin` | Standardbibliotek. Kombinerer en base-URL og en relativ URL til en absolutt URL. |
| `logger = logging.getLogger(__name__)` | Oppretter et logger-objekt med modulens eget navn (`vault_skriver`) som identifikator. Lar konfigurasjonen styres fra toppen av applikasjonen. |

---

## 3. Offentlig funksjon: `lagre_artikkel()`

`lagre_artikkel()` er den eneste offentlige funksjonen i modulen. Den orkestrerer hele skrivesekvensen og sørger for atomisitet via rollback ved SQLite-feil.

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
| `innhold: str` | Markdown-tekst fra innhentingskanalen. Bilder i teksten lastes ned og erstattes. |
| `publisert: str \| None` | ISO-dato fra kilden, f.eks. `'2024-01-15'`. Kan være `None` hvis kilden ikke oppgir dato. |
| `kildetype: str` | Kanaltype-streng: `'rss'`, `'manuell'`, `'youtube'`, osv. Lagres i frontmatter. |
| `db_sti: Path` | Filsti til SQLite-databasefilen, f.eks. `Path('/data/artikler.db')`. |
| `vault_rot: Path` | Rot-mappe for Obsidian-vaultet, f.eks. `Path('/home/user/vault')`. |
| `klippet_dato: str \| None` | Valgfri. ISO-dato for manuell klipping. Fallback for `publisert` hvis `publisert` er `None`. |
| `kilde_mappe: str \| None` | Valgfri. Artikkelen lagres i `artikler/{kilde_mappe}/`. Påvirker også relativ bildesti. |

### 3.3 Linje-for-linje

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `element_id = str(uuid.uuid4())` | Genererer en ny UUID4 og konverterer til streng. Eks: `'a1b2c3d4-e5f6-7890-abcd-ef1234567890'`. Artikkelen sin globalt unike ID. |
| `uuid_kort = element_id.replace("-", "")[:8]` | Fjerner bindestreker og tar de første 8 tegnene, f.eks. `'a1b2c3d4'`. Brukes i filnavnet for korthet. |
| `slug = _lag_slug(tittel)` | Kaller intern hjelpefunksjon som konverterer tittelen til en URL-trygg slug. Se seksjon 4.1. |
| `filnavn = f"{uuid_kort}-{slug}.md"` | Setter sammen filnavn: kortUUID + bindestrek + slug + `.md`. Eks: `'a1b2c3d4-min-artikkel-om-ai.md'`. |
| `if kilde_mappe:` | Sjekker om kallstedet oppga et kildenavn. Bestemmer undermappe og relativ bildesti. |
| `    artikkel_mappe = vault_rot / "artikler" / kilde_mappe` | Bygger målmappe med kildenavn som undermappe. `Path /`-operator tilsvarer `os.path.join()`. |
| `    bilde_prefix = "../../ressurser/bilder"` | Relativ sti fra artikkelmappe til bildemappen. To nivåer opp fordi filen er i `artikler/kilde/`. |
| `else:` | Kjøres hvis `kilde_mappe` er `None` eller tom streng. |
| `    artikkel_mappe = vault_rot / "artikler"` | Filen legges direkte i `artikler/` uten undermappe. |
| `    bilde_prefix = "../ressurser/bilder"` | Kun ett nivå opp siden filen er i `artikler/` direkte. |
| `artikkel_mappe.mkdir(parents=True, exist_ok=True)` | Oppretter mappestien på disk. `parents=True` oppretter mellomliggende mapper. `exist_ok=True` feiler ikke hvis mappen allerede finnes. |
| `innhold_behandlet, bildefilnavn = _behandle_bilder(innhold, vault_rot, url, bilde_prefix)` | Laster ned alle bilder i innholdet og erstatter URL-ene. Returnerer endret innholdsstreng og liste med filnavn. |
| `effektiv_publisert = publisert or klippet_dato` | Python `or` kort-slutning: bruker `publisert` hvis den er truthy, ellers `klippet_dato`. Gir ett kanonisk dato-felt. |
| `md_innhold = _bygg_markdown(` | Starter kall til `_bygg_markdown()` som setter sammen frontmatter + H1-tittel + innhold. |
| `    element_id=element_id,` | Sender UUID4 inn som navngitt argument. |
| `    url=url,` | Sender artikkelen sin URL inn — lagres i YAML-frontmatter. |
| `    tittel=tittel,` | Sender tittel inn — brukes som H1-overskrift i dokumentet. |
| `    kildetype=kildetype,` | Sender kanaltype inn — lagres i YAML-frontmatter. |
| `    klippet_dato=klippet_dato,` | Sender klippedato inn — legges kun til frontmatter hvis ikke `None`. |
| `    publisert=effektiv_publisert,` | Sender effektiv publiseringsdato (med fallback) inn. |
| `    innhold=innhold_behandlet,` | Sender det bildeprosesserte innholdet inn — URL-er er nå lokale. |
| `)` | Avslutter kallet til `_bygg_markdown()`. Returnert streng lagres i `md_innhold`. |
| `fil_sti = artikkel_mappe / filnavn` | Bygger full filsti for den ferdige Markdown-filen. |
| `fil_sti.write_text(md_innhold, encoding="utf-8")` | Skriver Markdown-dokumentet til disk med UTF-8-koding. **STEG 4 — filen finnes nå på disk.** |
| `hentet = datetime.now(timezone.utc).isoformat()` | Henter nåværende UTC-tidspunkt og konverterer til ISO 8601-streng, f.eks. `'2024-01-16T08:30:00+00:00'`. Tidssone-bevisst. |
| `if kilde_mappe:` | Velger riktig relativ vault-sti avhengig av om `kilde_mappe` er satt. |
| `    vault_sti = (Path("artikler") / kilde_mappe / filnavn).as_posix()` | Bygger relativ sti med kildeundermappe. `.as_posix()` gir skråstrek uavhengig av OS. |
| `else:` | Alternativ sti uten kildeundermappe. |
| `    vault_sti = (Path("artikler") / filnavn).as_posix()` | Bygger relativ sti direkte under `artikler/`. |
| `bilder_json = json.dumps(bildefilnavn) if bildefilnavn else None` | Serialiserer bildeliste til JSON-streng hvis listen ikke er tom. `None` hvis ingen bilder ble lastet ned. |
| `try:` | Starter try-blokk for rollback-logikk. Alt under her rulles tilbake ved SQLite-feil. |
| `    _skriv_til_db(` | Kaller intern funksjon som skriver raden til SQLite. Se seksjon 4.6. |
| `        db_sti=db_sti,` | Filsti til databasen. |
| `        kilde_id=kilde_id,` | Fremmednøkkel til `kilder`-tabellen. |
| `        guid=element_id,` | UUID4 for artikkelen — `UNIQUE` i databasen. |
| `        url=url,` | Original URL. |
| `        tittel=tittel,` | Artikkeltittel. |
| `        publisert=effektiv_publisert,` | Effektiv publiseringsdato. |
| `        hentet=hentet,` | UTC-tidsstempel for henting. |
| `        vault_sti=vault_sti,` | Relativ sti til `.md`-filen. |
| `        bilder_json=bilder_json,` | JSON-streng med bildefilnavn, eller `None`. |
| `    )` | Avslutter kallet til `_skriv_til_db()`. |
| `except sqlite3.Error:` | Fanger alle SQLite-feil: `IntegrityError`, `OperationalError`, `DatabaseError` osv. |
| `    fil_sti.unlink(missing_ok=True)` | **ROLLBACK:** sletter `.md`-filen som ble skrevet i steg 4. `missing_ok=True` feiler ikke om filen allerede er borte. |
| `    raise` | Kaster SQLite-feilen videre opp til kalleren. Ingen stille svelging av feil. |
| `return element_id` | Returnerer den fulle UUID4-strengen. Kallstedet kan bruke denne til videre referanser. |

---

## 4. Hjelpefunksjoner

### 4.1 `_lag_slug(tittel: str) -> str`

Konverterer en artikkeltittel til en URL-trygg slug egnet for filnavn. Eks: `'Norsk økonomi i 2024!'` → `'norsk-konomi-i-2024'`.

> **Begrep — NFKD-normalisering:** En Unicode-normaliseringsform som dekomponerer sammensatte tegn til grunntegn + diakritiske tegn. `'ø'` blir til `'o'` + combining-tegn som filtreres ut av ASCII-konvertering.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `normalisert = unicodedata.normalize("NFKD", tittel)` | Dekomponerer Unicode-tegn. `'ø'` → `o` + combining-tegn. Gjør at æøå kan strippes til ASCII-ekvivalenter. |
| `ascii_bytes = normalisert.encode("ascii", errors="ignore")` | Koder til ASCII-bytes og kaster tegn som ikke finnes i ASCII (combining-tegnene). Returnerer `bytes`-objekt. |
| `slug = ascii_bytes.decode("ascii").lower()` | Dekoder bytes tilbake til streng og konverterer til lowercase. |
| `slug = slug.replace(" ", "-").replace("_", "-").replace(".", "-")` | Erstatter mellomrom, understrek og punktum med bindestreker — standard slug-separatorer. |
| `slug = re.sub(r"[^a-z0-9-]", "", slug)` | Regex: fjerner alle tegn som ikke er bokstav, tall eller bindestrek. `!`, `?`, `#` osv. forsvinner. |
| `slug = re.sub(r"-+", "-", slug).strip("-")` | Kollapser flere påfølgende bindestreker til én, og fjerner bindestreker i starten/slutten. |
| `return slug or "artikkel"` | Returnerer slugen. Fallback til `'artikkel'` hvis tittelen var tom eller kun spesialtegn. |

**Transformasjon trinn for trinn:**

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

### 4.2 `_bygg_markdown(...) -> str`

Bygger det ferdige Markdown-dokumentet med YAML-frontmatter, H1-overskrift og artikkeltekst. Returnerer en streng klar for skriving til disk.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `linjer = [` | Starter en liste med frontmatter-linjer. |
| `    "---",` | `'---'` er YAML-blokkens åpningsmarkør. |
| `    f"element_id: {element_id}",` | Legger til artikkelen sin UUID4 som YAML-felt. |
| `    f"url: {url}",` | Original kildeadresse i frontmatter — gjør det mulig å gå tilbake til kilden. |
| `    f"kildetype: {kildetype}",` | Kanaltype-streng i frontmatter — brukes til filtrering. |
| `]` | Avslutter listen med de obligatoriske frontmatter-feltene. |
| `if klippet_dato is not None:` | Betinget: `klippet_dato`-feltet legges kun til for manuelt klippede artikler. |
| `    linjer.append(f"klippet_dato: {klippet_dato}")` | Legger til klippedato-felt i frontmatter. |
| `if publisert is not None:` | Betinget: `publisert` utelates hvis ingen dato er kjent — unngår tomme YAML-felt. |
| `    linjer.append(f"publisert: {publisert}")` | Legger til publiseringsdato-felt i frontmatter. |
| `linjer.append("---")` | Avslutter YAML-blokken med lukkemarkør. |
| `frontmatter = "\n".join(linjer)` | Setter linjene sammen med linjeskift til én frontmatter-streng. |
| `return f"{frontmatter}\n\n# {tittel}\n\n{innhold}\n"` | Returnerer hele dokumentet: frontmatter + to linjeskift + H1-tittel + to linjeskift + innhold + avsluttende linjeskift. |

**Eksempel output:**

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

### 4.3 `_behandle_bilder(innhold, vault_rot, base_url, bilde_prefix) -> tuple[str, list[str]]`

Skanner artikkelteksten for bildereferanser i Markdown-syntaks og HTML, laster ned hvert unike bilde, og erstatter URL-ene med lokale relative stier.

> **Begrep — Regulært uttrykk (regex):** Et mønster-språk for å søke i tekst. `r'![...](...)'` matcher Markdown-bildesyntaks. `re.compile()` kompilerer mønsteret til et raskt søkeobjekt som gjenbrukes for hvert søk.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `bilde_mappe = vault_rot / "ressurser" / "bilder"` | Bygger sti til bildemappe. Alle nedlastede bilder havner her uavhengig av kilde. |
| `bilde_mappe.mkdir(parents=True, exist_ok=True)` | Oppretter bildemappen hvis den ikke finnes. Trygt å kalle gjentatte ganger. |
| `md_monster = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")` | Kompilert regex for Markdown-bilder. Gruppe 1: alt-tekst. Gruppe 2: URL. Matcher f.eks. `![bilde](https://...)`. |
| `html_monster = re.compile(r'<img\s+[^>]*src=["\'']([^"\']+)["\']', re.IGNORECASE)` | Kompilert regex for HTML `img`-tagger. Gruppe 1: `src`-URL. `re.IGNORECASE` matcher `SRC=` og `src=` likt. |
| `url_til_lokal: dict[str, str] = {}` | Tom ordbok som mapper original bilde-URL → lokal relativ sti. Sikrer at samme bilde lastes ned kun én gang. |
| `for treff in md_monster.finditer(innhold):` | Itererer over alle Markdown-bildematches i teksten. |
| `    bilde_url = treff.group(2)` | Henter URL fra andre fangstgruppe i regex-matchen. |
| `    if bilde_url not in url_til_lokal:` | Hopper over URL-er som allerede er prosessert (dedup). |
| `        abs_url = urljoin(base_url, bilde_url) if base_url else bilde_url` | Gjør relative URL-er absolutte. `urljoin('https://ex.com/art/', '../img.jpg')` → `'https://ex.com/img.jpg'`. |
| `        lokal = _last_ned_bilde(abs_url, bilde_mappe, bilde_prefix)` | Forsøker å laste ned bildet. Returnerer lokal relativ sti eller `None` ved feil. |
| `        if lokal:` | Registrerer mapping kun hvis nedlasting lyktes. |
| `            url_til_lokal[bilde_url] = lokal` | Lagrer original URL → lokal sti i ordboken. |
| `for treff in html_monster.finditer(innhold):` | Itererer over alle HTML `img src`-matches i teksten. |
| `    bilde_url = treff.group(1)` | Henter `src`-URL fra første fangstgruppe (HTML-regex har kun én gruppe). |
| `    if bilde_url not in url_til_lokal:` | Hopper over URL-er som allerede er prosessert via Markdown-løkken. |
| `        abs_url = urljoin(base_url, bilde_url) if base_url else bilde_url` | Gjør relativ URL absolutt. Samme logikk som for Markdown-bilder. |
| `        lokal = _last_ned_bilde(abs_url, bilde_mappe, bilde_prefix)` | Forsøker nedlasting. Returnerer lokal sti eller `None`. |
| `        if lokal:` | Registrerer mapping kun ved suksess. |
| `            url_til_lokal[bilde_url] = lokal` | Lagrer i ordboken. |
| `bildefilnavn: list[str] = []` | Tom liste som samler filnavnene til nedlastede bilder — returneres til `lagre_artikkel()`. |
| `for original_url, lokal_sti in url_til_lokal.items():` | Itererer over alle vellykkede URL→sti-mappinger. |
| `    innhold = innhold.replace(original_url, lokal_sti)` | Tekstersetting: alle forekomster av original-URL erstattes med lokal relativ sti i innholdet. |
| `    bildefilnavn.append(Path(lokal_sti).name)` | Henter kun filnavnet (f.eks. `'e5f6g7h8.jpg'`) fra full sti. |
| `return innhold, bildefilnavn` | Returnerer endret innholdsstreng og liste med filnavn. |

**Teksterstatning i praksis:**

| Innhold FØR | Innhold ETTER |
|---|---|
| `![graf](https://ex.com/graf.png)` | `![graf](../../ressurser/bilder/a1b2.png)` |
| `<img src="https://ex.com/logo.jpg">` | `<img src="../../ressurser/bilder/c3d4.jpg">` |

---

### 4.4 `_last_ned_bilde(url, bilde_mappe, bilde_prefix) -> str | None`

Laster ned ett enkeltbilde fra nettet, lagrer det lokalt med et UUID-basert filnavn, og returnerer den relative stien. Returnerer `None` og logger advarsel ved ethvert problem.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `if not url.startswith(("http://", "https://"))` | Validerer at URL-en bruker et støttet protokollskjema. `data:`, `file://` osv. avvises stille. |
| `    logger.warning("Ugyldig bilde-URL (ikke http/https): %s", url)` | Logger advarsel på WARNING-nivå med URL. Kallestedet ser feilen i logg uten at programmet krasjer. |
| `    return None` | Returnerer `None` for å signalere at nedlasting ikke ble utført. |
| `try:` | Starter try-blokk som fanger alle nettverks- og HTTP-feil. |
| `    respons = httpx.get(url, follow_redirects=True, timeout=10.0)` | HTTP GET. `follow_redirects=True`: følger 301/302-videresendinger. `timeout=10.0`: avbryter etter 10 sekunder. |
| `    respons.raise_for_status()` | Kaster `httpx.HTTPStatusError` hvis HTTP-statuskoden er 4xx eller 5xx (f.eks. 404 Not Found, 403 Forbidden). |
| `except Exception as feil:` | Fanger alle unntak — nettverksfeil, timeout, HTTP-feil, SSL-feil osv. |
| `    logger.warning("Kunne ikke laste ned bilde %s: %s", url, feil)` | Logger advarsel med URL og feilmelding. Programmet fortsetter med neste bilde. |
| `    return None` | Returnerer `None`: bildet beholdes med original-URL i innholdet. |
| `innholdstype = respons.headers.get("content-type", "")` | Henter `Content-Type`-headeren, f.eks. `'image/jpeg; charset=utf-8'`. Fallback til tom streng. |
| `ext = _finn_ext(innholdstype, url)` | Delegerer filendelse-beslutning til `_finn_ext()`. Se seksjon 4.5. |
| `filnavn = f"{uuid.uuid4().hex[:8]}.{ext}"` | Genererer unikt filnavn: 8 hex-tegn fra ny UUID + filendelse. Eks: `'a1b2c3d4.jpg'`. |
| `(bilde_mappe / filnavn).write_bytes(respons.content)` | Skriver bildets rå bytes til disk. `.content` er `bytes`-objektet fra HTTP-svaret. |
| `return f"{bilde_prefix}/{filnavn}"` | Returnerer relativ sti fra artikkelens plassering til bildet. Eks: `'../../ressurser/bilder/a1b2c3d4.jpg'`. |

---

### 4.5 `_finn_ext(innholdstype: str, url: str) -> str`

Bestemmer riktig filendelse for et nedlastet bilde. Prioriterer `Content-Type`-headeren, faller tilbake til URL-suffiks, og bruker `'bin'` som siste utvei.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `type_til_ext = {` | Starter oppslagstabell (dict) som mapper MIME-type til filendelse. |
| `    "image/jpeg": "jpg",` | JPEG-bilder → `.jpg` |
| `    "image/png": "png",` | PNG-bilder → `.png` |
| `    "image/gif": "gif",` | GIF-bilder → `.gif` |
| `    "image/webp": "webp",` | WebP-bilder → `.webp` |
| `    "image/svg+xml": "svg",` | SVG-vektorgrafik → `.svg` |
| `}` | Avslutter oppslagstabellen. |
| `mime = innholdstype.split(";")[0].strip().lower()` | Renser `Content-Type`: splitter på semikolon, striper whitespace, konverterer til lowercase. |
| `if mime in type_til_ext:` | Sjekker om den rensede MIME-typen finnes i oppslagstabellen. |
| `    return type_til_ext[mime]` | Returnerer riktig endelse direkte. Raskeste og sikreste vei. |
| `url_sti = url.split("?")[0]` | Fallback: fjerner query-parametre fra URL. Eks: `'.../bilde.png?v=2'` → `'.../bilde.png'`. |
| `siste_del = url_sti.split("/")[-1]` | Henter siste path-segment — vanligvis filnavnet. Eks: `'bilde.png'`. |
| `if "." in siste_del:` | Sjekker om det finnes en filendelse i URL-segmentet. |
| `    ext = siste_del.rsplit(".", 1)[-1].lower()` | Splitter på siste punktum og tar det som kommer etter. `rsplit` med `maxsplit=1` håndterer `'fil.min.png'` korrekt. |
| `    if ext in {"jpg", "jpeg", "png", "gif", "webp", "svg"}:` | Sjekker at endelsen er en kjent og trygg bildetype. |
| `        return "jpg" if ext == "jpeg" else ext` | `'jpeg'` normaliseres til `'jpg'`. Alle andre godkjente endelser returneres uendret. |
| `return "bin"` | Siste fallback: `'bin'` = binær fil — indikerer ukjent format. |

---

### 4.6 `_skriv_til_db(...) -> None`

Skriver én rad til `elementer`-tabellen i SQLite-databasen. Bruker kontekstmanager (`with`-blokk) for automatisk commit ved suksess og rollback ved unntak.

> **Begrep — `PRAGMA foreign_keys = ON`:** SQLite har fremmednøkkel-støtte deaktivert som standard. Denne linjen aktiverer det for tilkoblingen, slik at `kilde_id` må referere en eksisterende rad i `kilder`-tabellen.

> **Begrep — Parameterisert SQL (`?` placeholders):** Verdier settes inn via parameter-tuple, ikke direkte string-interpolering. Hindrer SQL-injeksjon og håndterer spesialtegn korrekt automatisk.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `with sqlite3.connect(db_sti) as tilkobling:` | Åpner tilkobling til SQLite-filen. `with`-blokken sikrer automatisk commit ved slutt og rollback ved unntak. |
| `    tilkobling.execute("PRAGMA foreign_keys = ON")` | Aktiverer fremmednøkkel-validering for denne tilkoblingen. |
| `    tilkobling.execute(` | Starter `execute()`-kallet med SQL-setningen. |
| `        """` | Åpner triple-quoted streng for flerlinjet SQL. |
| `        INSERT INTO elementer (kilde_id, guid, url, tittel, publisert, hentet, vault_sti, bilder_json)` | SQL INSERT-setningen med alle kolonnene som skal fylles. |
| `        VALUES (?, ?, ?, ?, ?, ?, ?, ?)` | Parameteriserte plassholdere. Antall `?` matcher antall kolonner og parameterverdier nøyaktig. |
| `        """,` | Avslutter SQL-strengen. |
| `        (kilde_id, guid, url, tittel, publisert, hentet, vault_sti, bilder_json),` | Parametertupelen — verdiene settes inn i samme rekkefølge som `?`-plassholderne. |
| `    )` | Avslutter `execute()`-kallet. SQLite-transaksjonen committes automatisk av `with`-blokken. |

**Forventet databaseskjema:**

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

| Feilsituasjon | Håndtering | Resultat for systemet |
|---|---|---|
| Bildenedlasting feiler (nettverk, timeout, HTTP 4xx/5xx) | `logger.warning()` + `return None` i `_last_ned_bilde()` | Artikkelen lagres med original bilde-URL intakt |
| Ugyldig bilde-URL (ikke http/https) | `logger.warning()` + `return None` i `_last_ned_bilde()` | Som over |
| SQLite-feil etter `.md` er skrevet | `fil_sti.unlink(missing_ok=True)` + `raise` i `lagre_artikkel()` | Disk og DB er synkrone — ingen halvferdig tilstand |
| Mappe kan ikke opprettes (disk full, tilgang nektet) | `OSError` kastes, ikke fanget | Propagerer opp til kalleren |
| Feil i `_behandle_bilder()` eller `_bygg_markdown()` | Ikke fanget — propagerer opp | Ingen `.md`-fil skrevet — ingenting å rulle tilbake |

> ⚠️ **Viktig:** Rollback-logikken gjelder kun tilfellet der `.md`-filen er skrevet men SQLite-skriving feiler. Feil som oppstår FØR `.md`-filen skrives propagerer direkte.

---

## 6. Eksterne avhengigheter

| Pakke | Bruk i denne filen | Installasjon |
|---|---|---|
| `httpx` | Laster ned bilder i `_last_ned_bilde()`. Støtter `timeout` og `follow_redirects`. | `pip install httpx` |
| `pathlib.Path` | Filstimanipulasjon gjennom hele modulen. `/`-operatoren bygger stier. | Standardbibliotek |
| `sqlite3` | Databaseskriving i `_skriv_til_db()`. | Standardbibliotek |
| `unicodedata, uuid, re, json, logging, datetime, timezone` | Se seksjon 2 for detaljer. | Standardbibliotek |

---

## 7. Oppsummering

`vault_skriver.py` løser ett problem: sørg for at en artikkel enten er fullstendig lagret — med Markdown-fil på disk og rad i database — eller ikke lagret i det hele tatt. Modulen eksponerer én funksjon og holder alt internt privat.

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
