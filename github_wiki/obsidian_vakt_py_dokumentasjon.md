# obsidian_vakt.py — Teknisk dokumentasjon

## 1. Overordnet beskrivelse

`obsidian_vakt.py` implementerer en filsystemvakt (watchdog) som overvåker to mapper i Obsidian-vault i sanntid: `innboks/` for nye filer og `artikler/` for slettede filer. Nye `.md`- og `.pdf`-filer fra Obsidian Web Clipper prosesseres automatisk og lagres i databasen og vault. Slettede artikler ryddes opp umiddelbart — bilder og databaserader fjernes.

Filen løser tre konkrete problemer: (1) Manuelt klippede nettartikler og PDF-er skal registreres i SQLite uten manuell handling. (2) Artikler slettet fra vault under drift skal ryddes opp i sanntid uten å vente til neste `kjører.py`-kjøring. (3) Duplikater skal avvises automatisk basert på URL-dedup mot databasen.

Watchdog-arkitekturen bruker en `Observer` med to separate `FileSystemEventHandler`-instanser montert på hvert sitt mappe-mål. Feil i én fil stopper ikke behandling av neste.

Filen startes med `python -m intelligence_monitor.innhenter.obsidian_vakt` eller via Makefile.

**ASCII-flytdiagram:**

```
start(vault_rot, db_sti)
    │
    ├─► Opprett innboks/ og artikler/ hvis de mangler
    ├─► _rydd_foreldreløse()         ← rydd opp fra perioder vakt var nede
    ├─► Skann innboks/ ved oppstart
    │       ├─ .md  → _InnboksHandler._prosesser()
    │       └─ .pdf → _InnboksHandler._prosesser_pdf()
    ├─► Observer.schedule(_InnboksHandler  → innboks/, recursive=False)
    ├─► Observer.schedule(_ArtikkelHandler → artikler/, recursive=True)
    └─► Kjør til KeyboardInterrupt

_InnboksHandler.on_created(event)
    ├─ .md  → _prosesser(fil_sti)
    │         ├─► time.sleep(0.3)
    │         ├─► _les_frontmatter_og_kropp()
    │         ├─► _url_finnes()      ← dedup
    │         ├─► _hent_kilde_id()
    │         ├─► _trekk_ut_tittel()
    │         ├─► vault_skriver.lagre_artikkel()
    │         └─► shutil.move() → behandlet/
    └─ .pdf → _prosesser_pdf(fil_sti)
              ├─► time.sleep(0.3)
              ├─► _url_finnes()      ← dedup på "pdf://{stem}"
              ├─► _hent_kilde_id()
              ├─► _trekk_ut_pdf_innhold()
              ├─► vault_skriver.lagre_artikkel()
              └─► shutil.move() → behandlet/

_ArtikkelHandler.on_deleted(event)
    └─► _rydd_etter_slettet_artikkel(db_sti, vault_rot, vault_sti)
            ├─► SQLite READ: SELECT id, bilder_json WHERE vault_sti = ?
            ├─► slett bildefiler fra disk
            └─► SQLite WRITE: DELETE evalueringstriplets, sammendrag, elementer
```

**Mockup — sideeffekter per hendelse:**

```
Ny .md i innboks/:
  vault/
  ├── innboks/artikkel.md         ← trigger
  ├── behandlet/artikkel.md       ← flyttes hit
  └── artikler/kilde/slug.md      ← opprettet av vault_skriver
  monitor.db: ny rad i elementer, sammendrag (hvis generert)

Slettet .md fra artikler/:
  vault/ressurser/bilder/bilde.jpg ← slettes fra disk
  monitor.db: DELETE evalueringstriplets, sammendrag, elementer
```

---

## 2. Importer og moduloppsett

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `from __future__ import annotations` | Aktiverer utsatt evaluering av typeannotering (PEP 563). |
| `import json` | Brukes til å deserialisere `bilder_json`-kolonnen fra SQLite. |
| `import logging` | Strukturert loggutskrift. Logger feil, duplikater og vellykkede lagringer. |
| `import os` | Brukes til `os.getenv()` for å lese `VAULT_ROT` og `DATABASE_STI`. |
| `import re` | Regulære uttrykk. Brukes til å finne første H1-heading i Markdown-kropp. |
| `import shutil` | Filoperasjoner på høyere nivå. Brukes til `shutil.move()` for å flytte filer til `behandlet/`. |
| `import sqlite3` | SQLite-tilkobling for dedup-sjekk, kilde-oppslag og opprydding. |
| `import time` | Brukes til `time.sleep(0.3)` — kort pause etter watchdog-hendelse for å sikre at filen er ferdigskrevet. |
| `from pathlib import Path` | Objektorientert filsti-håndtering. |
| `import pypdf` | Tredjeparts PDF-leser. Brukes til å ekstrahere tekst og metadata fra PDF-filer. |
| `import yaml` | Brukes til `yaml.safe_load()` for å parse YAML-frontmatter fra Markdown-filer. |
| `from urllib.parse import urlparse` | Brukes til å trekke ut domenedelen av en URL. |
| `from dotenv import load_dotenv` | Laster miljøvariabler fra `.env`-fil. |
| `from watchdog.events import FileCreatedEvent, FileDeletedEvent, FileSystemEventHandler` | Watchdog-typer: baseklasse for hendelseshåndterere og hendelsestypene som brukes i de to handler-klassene. |
| `from watchdog.observers import Observer` | Watchdog-klassen som starter filsystemovervåking og dispatcher hendelser til handlers. |
| `from intelligence_monitor.innhenter import vault_skriver` | Intern modul for å lagre artikler i vault og SQLite. |
| `load_dotenv()` | Laster `.env`-filen umiddelbart ved modulinnlasting. |
| `logger = logging.getLogger(__name__)` | Logger bundet til `intelligence_monitor.innhenter.obsidian_vakt`. |
| `_H1_MONSTER = re.compile(r"^#\s+(.+)$", re.MULTILINE)` | Forhåndskompilert regex for å finne første H1 i Markdown. `re.MULTILINE` gjør at `^` matcher starten av hver linje. |
| `_MANUELL_KILDENAVN = "manuell-klipp"` | Konstant — kildenavnet i `kilder`-tabellen for manuelt klippede artikler. |
| `_PDF_KILDENAVN = "manuell-pdf"` | Konstant — kildenavnet for PDF-filer. |

---

## 3. Offentlig API — start()

`start()` starter watchdog-observatøren og blokkerer til brukeren avbryter med `Ctrl+C`. Den oppretter nødvendige mappestrukturer, rydder foreldreløse rader fra perioder vakten var nede, og prosesserer eksisterende filer i `innboks/` ved oppstart.

**Parametertabell:**

| Parameter | Type | Forklaring |
|---|---|---|
| `vault_rot` | `Path` | Rotmappe for Obsidian-vault. Eksempel: `Path("vault")`. |
| `db_sti` | `Path` | Absolutt sti til SQLite-databasefilen. Eksempel: `Path("data/monitor.db")`. |

**Linje-for-linje:**

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def start(vault_rot: Path, db_sti: Path) -> None:` | Definerer den offentlige funksjonen. Blokkerer til `KeyboardInterrupt`. |
| `"""Starter watchdog-observatøren og blokkerer til KeyboardInterrupt.` | Docstring. |
| `    Args:` | Args-seksjon i docstring. |
| `        vault_rot: Rot-mappe for Obsidian-vault.` | Dokumenterer `vault_rot`. |
| `        db_sti: Sti til SQLite-databasefilen.` | Dokumenterer `db_sti`. |
| `    """` | Avslutter docstring. |
| `    innboks = vault_rot / "innboks"` | Bygger sti til innboks-mappen. |
| `    innboks.mkdir(parents=True, exist_ok=True)` | Oppretter `innboks/` hvis den ikke finnes. `parents=True` oppretter hele stikjeden; `exist_ok=True` kaster ikke feil hvis mappen allerede finnes. |
| `    artikler = vault_rot / "artikler"` | Bygger sti til artikler-mappen. |
| `    artikler.mkdir(parents=True, exist_ok=True)` | Oppretter `artikler/` hvis den ikke finnes. |
| `    handler = _InnboksHandler(db_sti=db_sti, vault_rot=vault_rot)` | Instansierer hendelseshåndtereren for innboks-mappen. |
| `    artikkel_handler = _ArtikkelHandler(db_sti=db_sti, vault_rot=vault_rot)` | Instansierer hendelseshåndtereren for artikler-mappen. |
| `    # Rydd foreldreløse DB-rader (slettede mens vakten var nede)` | Kommentar. |
| `    _rydd_foreldreløse(db_sti, vault_rot)` | Rydder opp rader der vault-filen ble slettet mens vakten var inaktiv. |
| `    # Skann eksisterende filer i innboks ved oppstart` | Kommentar. |
| `    for fil in sorted(innboks.iterdir()):` | Itererer over eksisterende filer i innboks/ sortert etter navn. |
| `        if fil.suffix == ".md":` | Sjekker om filen er en Markdown-fil. |
| `            handler._prosesser(fil)` | Prosesserer .md-filen direkte (ikke via watchdog-hendelse). |
| `        elif fil.suffix == ".pdf":` | Sjekker om filen er en PDF-fil. |
| `            handler._prosesser_pdf(fil)` | Prosesserer .pdf-filen direkte. |
| `    observer = Observer()` | Oppretter watchdog-observatør-instansen. |
| `    observer.schedule(handler, str(innboks), recursive=False)` | Registrerer `_InnboksHandler` på `innboks/`. `recursive=False` — overvåker ikke undermapper. |
| `    observer.schedule(artikkel_handler, str(artikler), recursive=True)` | Registrerer `_ArtikkelHandler` på `artikler/`. `recursive=True` — overvåker undermapper (kildemapper). |
| `    observer.start()` | Starter observatøren i en bakgrunnstråd. |
| `    logger.info("Vakt startet — overvåker %s og %s", innboks, artikler)` | Logger at vakten er aktiv. |
| `    try:` | Starter try-blokk for å fange `KeyboardInterrupt`. |
| `        while True:` | Uendelig løkke — holder hovedtråden i live mens observatøren kjører i bakgrunnen. |
| `            time.sleep(1)` | Sover 1 sekund per iterasjon for å unngå 100 % CPU-bruk. |
| `    except KeyboardInterrupt:` | Fanger `Ctrl+C` fra brukeren. |
| `        observer.stop()` | Signaliserer til observatøren at den skal avslutte. |
| `    observer.join()` | Venter på at observatørens bakgrunnstråd er ferdig. |
| `    logger.info("Vakt stoppet.")` | Logger at vakten er avsluttet. |

---

## 4. Klasser og hjelpefunksjoner

### _InnboksHandler (FileSystemEventHandler)

Håndterer filopprettelse i `vault/innboks/`. Arver fra watchdog sin `FileSystemEventHandler`. To metoder: `on_created()` dispatcher til `_prosesser()` (.md) eller `_prosesser_pdf()` (.pdf). Feil per fil isoleres med `try/except`.

#### __init__

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def __init__(self, db_sti: Path, vault_rot: Path) -> None:` | Konstruktør. |
| `    self._db_sti = db_sti` | Lagrer databasestien som instansvariabel. |
| `    self._vault_rot = vault_rot` | Lagrer vault-roten som instansvariabel. |

#### on_created

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]` | Kalles av watchdog-tråden når en ny fil opprettes. `# type: ignore[override]` undertrykker mypy-advarsel for signaturen. |
| `    if event.is_directory:` | Ignorerer mappe-opprettelse (bare filer er relevante). |
| `        return` | Tidlig retur for mapper. |
| `    src = str(event.src_path)` | Konverterer sti-objektet til streng for endelsessjekk. |
| `    if src.endswith(".md"):` | Sjekker for Markdown-fil. |
| `        fil_sti = Path(src)` | Konverterer tilbake til Path-objekt. |
| `        try:` | Isolerer feil per fil. |
| `            self._prosesser(fil_sti)` | Prosesserer .md-filen. |
| `        except Exception as feil:` | Fanger alle unntak. |
| `            logger.error("Ubehandlet feil ved prosessering av %s: %s", fil_sti.name, feil, exc_info=True)` | Logger feilen med full stack trace. |
| `        return` | Avslutter etter .md-håndtering. |
| `    if src.endswith(".pdf"):` | Sjekker for PDF-fil. |
| `        fil_sti = Path(src)` | Konverterer til Path. |
| `        try:` | Isolerer feil per fil. |
| `            self._prosesser_pdf(fil_sti)` | Prosesserer .pdf-filen. |
| `        except Exception as feil:` | Fanger alle unntak. |
| `            logger.error("Ubehandlet feil ved prosessering av %s: %s", fil_sti.name, feil, exc_info=True)` | Logger feilen med full stack trace. |
| `        return` | Avslutter etter .pdf-håndtering. |

#### _prosesser

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _prosesser(self, fil_sti: Path) -> None:` | Prosesserer én .md-fil fra innboks/. |
| `    time.sleep(0.3)` | Kort pause — watchdog kan fyre før filen er ferdigskrevet til disk. |
| `    if not fil_sti.exists():` | Sjekker at filen faktisk finnes (kan ha forsvunnet i mellomtiden). |
| `        logger.warning("Fil forsvant før prosessering: %s", fil_sti.name)` | Logger advarsel. |
| `        return` | Tidlig retur. |
| `    frontmatter, kropp = _les_frontmatter_og_kropp(fil_sti)` | Leser YAML-frontmatter og Markdown-kropp fra filen. |
| `    url = (frontmatter.get("url") or frontmatter.get("source") or "").strip()` | Henter URL fra frontmatter. Prøver nøklene `url` og `source` (Obsidian Web Clipper bruker begge). |
| `    if not url:` | Hopper over filer uten URL — kan ikke dedup eller lagre uten den. |
| `        logger.warning("Ingen URL i frontmatter — hopper over %s", fil_sti.name)` | Logger advarsel. |
| `        return` | Tidlig retur. |
| `    if _url_finnes(self._db_sti, url):` | Sjekker om URL allerede er lagret (dedup). |
| `        logger.info(` | Starter INFO-logg for duplikat. |
| `            "Duplikat URL funnet — sletter innboks-fil: %s (%s)",` | Loggmelding med filnavn og URL. |
| `            fil_sti.name,` | Filnavnet som argument. |
| `            url,` | URL som argument. |
| `        )` | Avslutter logger.info-kallet. |
| `        fil_sti.unlink(missing_ok=True)` | Sletter duplikat-filen fra innboks/. `missing_ok=True` kaster ikke feil hvis filen allerede er borte. |
| `        return` | Tidlig retur etter dedup. |
| `    kilde_id = _hent_kilde_id(self._db_sti, _MANUELL_KILDENAVN)` | Henter primærnøkkel for `manuell-klipp`-kilden fra databasen. |
| `    if kilde_id is None:` | Kilden finnes ikke i databasen — databasen er ikke initialisert. |
| `        logger.error(` | Logger feil. |
| `            "Kilde '%s' ikke funnet i databasen — kjør db.init først",` | Feilmelding med kildenavn. |
| `            _MANUELL_KILDENAVN,` | Kildenavnet som argument. |
| `        )` | Avslutter logger.error-kallet. |
| `        return` | Tidlig retur — kan ikke lagre uten kilde_id. |
| `    tittel, kropp_uten_tittel = _trekk_ut_tittel(frontmatter, kropp, fil_sti.stem)` | Trekker ut tittel og returnerer kropp uten H1-heading. |
| `    klippet_dato = str(frontmatter.get("klippet_dato", "")) or None` | Leser valgfritt `klippet_dato`-felt fra frontmatter. Konverterer tom streng til `None`. |
| `    kildetype = str(frontmatter.get("kildetype", "manuell"))` | Leser kildetype fra frontmatter, standardverdi `"manuell"`. |
| `    vault_skriver.lagre_artikkel(` | Kaller lagrings-API-et. |
| `        kilde_id=kilde_id,` | Primærnøkkel for manuell-klipp-kilden. |
| `        url=url,` | Artikkelens URL. |
| `        tittel=tittel,` | Tittelen ekstrahert fra frontmatter eller H1. |
| `        innhold=kropp_uten_tittel,` | Markdown-kropp uten tittel-heading. |
| `        publisert=None,` | Publiseringsdato — ikke tilgjengelig for manuelt klippede artikler. |
| `        kildetype=kildetype,` | Kildetype fra frontmatter. |
| `        db_sti=self._db_sti,` | Databasestien. |
| `        vault_rot=self._vault_rot,` | Vault-roten. |
| `        klippet_dato=klippet_dato,` | Dato artikkelen ble klippet (valgfri). |
| `        kilde_mappe=_domene_fra_url(url),` | Vault-undermappe basert på domenet til URL. |
| `    )` | Avslutter `lagre_artikkel()`-kallet. |
| `    behandlet_mappe = self._vault_rot / "behandlet"` | Bygger sti til behandlet/-mappen. |
| `    behandlet_mappe.mkdir(parents=True, exist_ok=True)` | Oppretter behandlet/ hvis den ikke finnes. |
| `    shutil.move(str(fil_sti), str(behandlet_mappe / fil_sti.name))` | Flytter den prosesserte filen til behandlet/ for arkivering. |
| `    logger.info("Lagret og flyttet til behandlet/: %s", fil_sti.name)` | Logger vellykket lagring. |

#### _prosesser_pdf

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _prosesser_pdf(self, fil_sti: Path) -> None:` | Prosesserer én .pdf-fil fra innboks/. |
| `    time.sleep(0.3)` | Pause for å sikre at filen er ferdigskrevet. |
| `    if not fil_sti.exists():` | Sjekker at filen fortsatt finnes. |
| `        logger.warning("Fil forsvant før prosessering: %s", fil_sti.name)` | Logger advarsel. |
| `        return` | Tidlig retur. |
| `    url = f"pdf://{fil_sti.stem}"` | Konstruerer en syntetisk URL brukt som dedup-nøkkel for PDF-er (f.eks. `pdf://rapport-2026`). |
| `    if _url_finnes(self._db_sti, url):` | Dedup-sjekk mot databasen. |
| `        logger.info("Duplikat PDF — sletter: %s (%s)", fil_sti.name, url)` | Logger duplikat. |
| `        fil_sti.unlink(missing_ok=True)` | Sletter duplikat-filen. |
| `        return` | Tidlig retur. |
| `    kilde_id = _hent_kilde_id(self._db_sti, _PDF_KILDENAVN)` | Henter primærnøkkel for `manuell-pdf`-kilden. |
| `    if kilde_id is None:` | Kilden mangler i databasen. |
| `        logger.error(` | Logger feil. |
| `            "Kilde '%s' ikke funnet i databasen — kjør db.init først",` | Feilmelding. |
| `            _PDF_KILDENAVN,` | Kildenavnet. |
| `        )` | Avslutter logger.error-kallet. |
| `        return` | Tidlig retur. |
| `    tittel, innhold = _trekk_ut_pdf_innhold(fil_sti)` | Ekstraher tittel og tekstinnhold fra PDF. |
| `    if not innhold.strip():` | Sjekker at PDF-en faktisk inneholder tekst. |
| `        logger.warning("Ingen tekst å hente fra %s — hopper over", fil_sti.name)` | Logger advarsel for bildebaserte PDF-er. |
| `        return` | Tidlig retur — ingenting å lagre. |
| `    vault_skriver.lagre_artikkel(` | Lagrer PDF-innholdet. |
| `        kilde_id=kilde_id,` | manuell-pdf sin kilde_id. |
| `        url=url,` | Syntetisk `pdf://{stem}`-URL. |
| `        tittel=tittel,` | Tittelen fra PDF-metadata eller filnavn. |
| `        innhold=innhold,` | Ekstrahert tekst fra alle PDF-sider. |
| `        publisert=None,` | Ikke tilgjengelig for PDF. |
| `        kildetype="pdf",` | Fast kildetype. |
| `        db_sti=self._db_sti,` | Databasestien. |
| `        vault_rot=self._vault_rot,` | Vault-roten. |
| `        klippet_dato=None,` | Ikke tilgjengelig. |
| `        kilde_mappe=_PDF_KILDENAVN,` | Lagres under `manuell-pdf/`-mappen i vault. |
| `    )` | Avslutter `lagre_artikkel()`-kallet. |
| `    behandlet_mappe = self._vault_rot / "behandlet"` | Bygger sti til behandlet/-mappen. |
| `    behandlet_mappe.mkdir(parents=True, exist_ok=True)` | Oppretter behandlet/ hvis den ikke finnes. |
| `    shutil.move(str(fil_sti), str(behandlet_mappe / fil_sti.name))` | Flytter PDF til behandlet/. |
| `    logger.info("Lagret og flyttet til behandlet/: %s", fil_sti.name)` | Logger vellykket lagring. |

---

### _ArtikkelHandler (FileSystemEventHandler)

Håndterer sletting av `.md`-filer fra `vault/artikler/`. Kalles av watchdog når en artikkel slettes i Obsidian. Dispatcher til `_rydd_etter_slettet_artikkel()`.

#### on_deleted

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def on_deleted(self, event: FileDeletedEvent) -> None:  # type: ignore[override]` | Kalles av watchdog-tråden ved filsletting. |
| `    if event.is_directory or not str(event.src_path).endswith(".md"):` | Ignorerer mappe-sletting og ikke-.md-filer. |
| `        return` | Tidlig retur. |
| `    fil_sti = Path(str(event.src_path))` | Konverterer til Path-objekt. |
| `    vault_sti = fil_sti.relative_to(self._vault_rot).as_posix()` | Beregner relativ sti fra vault-rot, f.eks. `"artikler/kilde/slug.md"`. `.as_posix()` sikrer skråstrek-separator på alle plattformer. |
| `    try:` | Isolerer feil per fil. |
| `        _rydd_etter_slettet_artikkel(self._db_sti, self._vault_rot, vault_sti)` | Rydder opp bilder og DB-rader. |
| `    except Exception as feil:` | Fanger alle unntak. |
| `        logger.error(` | Logger feil med detaljer. |
| `            "Ubehandlet feil ved rydding etter slettet %s: %s",` | Feilmelding. |
| `            fil_sti.name,` | Filnavnet. |
| `            feil,` | Feilobjektet. |
| `            exc_info=True,` | Inkluderer full stack trace i loggen. |
| `        )` | Avslutter logger.error-kallet. |

---

### _rydd_etter_slettet_artikkel(db_sti, vault_rot, vault_sti)

Rydder bilder og databaserader etter at en artikkel er slettet. Brukes både av `_ArtikkelHandler` (sanntid) og `_rydd_foreldreløse()` (oppstart).

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _rydd_etter_slettet_artikkel(db_sti: Path, vault_rot: Path, vault_sti: str) -> None:` | Definerer hjelpefunksjonen. Parameteren `vault_sti` er relativ posix-sti, f.eks. `"artikler/kilde/slug.md"`. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Åpner SQLite-tilkobling som kontekst-manager. |
| `        rad = tilkobling.execute(` | Kjører SELECT-spørring. |
| `            "SELECT id, bilder_json FROM elementer WHERE vault_sti = ?", (vault_sti,)` | Henter element-ID og bilde-JSON for den slettede artikkelen. |
| `        ).fetchone()` | Henter én rad eller `None`. |
| `    if rad is None:` | Ingen DB-rad funnet — artikkelen var ikke lagret (eller allerede ryddet). |
| `        logger.info("Ingen DB-rad funnet for slettet fil: %s — hopper over", vault_sti)` | Logger informasjon. |
| `        return` | Tidlig retur. |
| `    element_id, bilder_json_tekst = rad` | Pakker ut tuppelet. |
| `    bildefilnavn: list[str] = json.loads(bilder_json_tekst) if bilder_json_tekst else []` | Deserialiserer bildeliste. Tom liste ved NULL. |
| `    bilde_mappe = vault_rot / "ressurser" / "bilder"` | Sti til bildemappen. |
| `    antall_slettet = 0` | Teller for slettede bilder. |
| `    for filnavn in bildefilnavn:` | Itererer over bildefilnavn. |
| `        bilde_fil = bilde_mappe / filnavn` | Bygger full sti til bildefilen. |
| `        if bilde_fil.exists():` | Sjekker at filen finnes. |
| `            bilde_fil.unlink()` | Sletter bildefilen. |
| `            antall_slettet += 1` | Øker bildesteller. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Ny tilkobling for skriveoperasjoner. |
| `        antall_triplets = tilkobling.execute(` | Sletter triplets og henter rowcount. |
| `            "DELETE FROM evalueringstriplets WHERE element_id = ?", (element_id,)` | SQL-sletteoperasjon. |
| `        ).rowcount` | Antall slettede rader. |
| `        antall_sammendrag = tilkobling.execute(` | Sletter sammendrag. |
| `            "DELETE FROM sammendrag WHERE element_id = ?", (element_id,)` | SQL-sletteoperasjon. |
| `        ).rowcount` | Antall slettede sammendrag. |
| `        tilkobling.execute("DELETE FROM elementer WHERE id = ?", (element_id,))` | Sletter element-raden sist. |
| `    logger.info(` | Logger oppsummering. |
| `        "Ryddet etter slettet artikkel '%s': %d bilde(r), %d sammendrag og %d triplet(s) fjernet",` | Loggmeldingsformat. |
| `        vault_sti,` | Relativ sti. |
| `        antall_slettet,` | Antall slettede bilder. |
| `        antall_sammendrag,` | Antall slettede sammendrag. |
| `        antall_triplets,` | Antall slettede triplets. |
| `    )` | Avslutter logger.info-kallet. |

---

### _rydd_foreldreløse(db_sti, vault_rot)

Henter alle elementer med `vault_sti IS NOT NULL` og rydder de som mangler på disk. Kalles ved oppstart for å håndtere slettinger som skjedde mens vakten var nede.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _rydd_foreldreløse(db_sti: Path, vault_rot: Path) -> int:` | Returnerer antall ryddede elementer. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Åpner lesetilkobling. |
| `        rader = tilkobling.execute(` | Starter SELECT. |
| `            "SELECT vault_sti FROM elementer WHERE vault_sti IS NOT NULL"` | Henter alle vault-stier med verdi. |
| `        ).fetchall()` | Henter alle rader. |
| `    antall = 0` | Initialiserer teller. |
| `    for (vault_sti,) in rader:` | Itererer — tuppelet pakkes ut med parentes-syntaks. |
| `        if not (vault_rot / vault_sti).exists():` | Sjekker om vault-filen mangler. |
| `            _rydd_etter_slettet_artikkel(db_sti, vault_rot, vault_sti)` | Delegerer oppryddingen. |
| `            antall += 1` | Øker teller. |
| `    logger.info("Ryddet %d foreldreløse element(er) fra SQLite", antall)` | Logger alltid, også ved null slettede. |
| `    return antall` | Returnerer antall. |

---

### _domene_fra_url(url)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _domene_fra_url(url: str) -> str:` | Trekker ut domene for bruk som vault-undermappe. |
| `    netloc = urlparse(url).netloc` | Henter nettlokasjon fra URL (f.eks. `www.example.com`). |
| `    if netloc.startswith("www."):` | Sjekker for www-prefiks. |
| `        netloc = netloc[4:]` | Fjerner `www.`-prefikset. |
| `    return netloc.replace(".", "-") or "ukjent-kilde"` | Erstatter punktum med bindestrek (f.eks. `example-com`). Returnerer `"ukjent-kilde"` hvis netloc er tom. |

**Eksempel:** `_domene_fra_url("https://www.example.com/artikkel")` → `"example-com"`

---

### _trekk_ut_pdf_innhold(fil_sti)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _trekk_ut_pdf_innhold(fil_sti: Path) -> tuple[str, str]:` | Returnerer `(tittel, innhold)`. |
| `    reader = pypdf.PdfReader(fil_sti)` | Oppretter PDF-leser for filen. |
| `    tittel = ""` | Initialiserer tom tittel. |
| `    if reader.metadata and reader.metadata.get("/Title"):` | Sjekker om PDF har metadata med `/Title`-nøkkel. |
| `        tittel = str(reader.metadata["/Title"]).strip()` | Henter tittel fra PDF-metadata. |
| `    if not tittel:` | Fallback hvis metadata-tittel mangler. |
| `        tittel = fil_sti.stem` | Bruker filnavn uten endelse som tittel. |
| `    sider = [side.extract_text() or "" for side in reader.pages]` | Ekstraher tekst fra alle sider. `or ""` håndterer sider uten tekst (bildeside). |
| `    innhold = "\n\n".join(s for s in sider if s.strip())` | Slår sammen ikke-tomme sider med dobbelt linjeskift. |
| `    return tittel, innhold` | Returnerer tittel og sammenslått innhold. |

---

### _les_frontmatter_og_kropp(fil_sti)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _les_frontmatter_og_kropp(fil_sti: Path) -> tuple[dict, str]:` | Returnerer `(frontmatter-dict, kropp-streng)`. |
| `    innhold = fil_sti.read_text(encoding="utf-8")` | Leser hele filen som UTF-8-tekst. |
| `    if not innhold.startswith("---"):` | Sjekker for YAML-frontmatter-markør. |
| `        return {}, innhold` | Ingen frontmatter — returner tom dict og hele innholdet. |
| `    deler = innhold.split("---", 2)` | Splitter på `---` maks 2 ganger → `["", yaml-tekst, kropp]`. |
| `    if len(deler) < 3:` | Ugyldig frontmatter (mangler avsluttende `---`). |
| `        return {}, innhold` | Returnerer hele innholdet som kropp. |
| `    frontmatter = yaml.safe_load(deler[1]) or {}` | Parser YAML. `safe_load` kjører ikke vilkårlig kode. `or {}` håndterer tom frontmatter. |
| `    kropp = deler[2].strip()` | Resten av filen etter frontmatter, med mellomrom fjernet. |
| `    return frontmatter, kropp` | Returnerer begge. |

**Eksempel:**
```
Input-fil:
---
url: https://example.com
tittel: Min artikkel
---
## Innhold her

Output: ({"url": "https://example.com", "tittel": "Min artikkel"}, "## Innhold her")
```

---

### _trekk_ut_tittel(frontmatter, kropp, filnavn_uten_ext)

Trekker ut tittel etter prioritetsrekkefølge: frontmatter → første H1 → filnavn. Hvis tittelen er H1, fjernes den fra kroppen for å unngå duplikering.

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _trekk_ut_tittel(` | Start av funksjonssignatur. |
| `    frontmatter: dict, kropp: str, filnavn_uten_ext: str` | Parameterlinje. |
| `) -> tuple[str, str]:` | Returnerer `(tittel, kropp_uten_tittel_heading)`. |
| `    tittel = frontmatter.get("tittel") or frontmatter.get("title") or ""` | Prioritet 1: sjekker begge vanlige frontmatter-nøkler. |
| `    if tittel:` | Tittel funnet i frontmatter. |
| `        return str(tittel).strip(), kropp` | Returnerer frontmatter-tittel og kropp uendret. |
| `    treff = _H1_MONSTER.search(kropp)` | Prioritet 2: søker etter første H1 i kroppen med regex. |
| `    if treff:` | H1 funnet. |
| `        tittel = treff.group(1).strip()` | Trekker ut H1-teksten. |
| `        kropp_uten = kropp[: treff.start()].rstrip() + "\n" + kropp[treff.end() :].lstrip()` | Fjerner H1-linjen fra kroppen ved å sette sammen teksten før og etter. |
| `        return tittel, kropp_uten.strip()` | Returnerer H1-tittel og kropp uten heading. |
| `    return filnavn_uten_ext, kropp` | Prioritet 3 (fallback): bruker filnavn uten endelse. |

---

### _hent_kilde_id(db_sti, navn)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _hent_kilde_id(db_sti: Path, navn: str) -> int \| None:` | Returnerer primærnøkkel eller `None`. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Åpner tilkobling. |
| `        rad = tilkobling.execute(` | Kjører SELECT. |
| `            "SELECT id FROM kilder WHERE navn = ?", (navn,)` | Parametrisert søk på kildenavn. |
| `        ).fetchone()` | Én rad eller `None`. |
| `    return int(rad[0]) if rad else None` | Konverterer til `int` hvis funnet, ellers `None`. |

---

### _url_finnes(db_sti, url)

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _url_finnes(db_sti: Path, url: str) -> bool:` | Returnerer `True` hvis URL finnes i databasen. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Åpner tilkobling. |
| `        rad = tilkobling.execute(` | Kjører SELECT. |
| `            "SELECT 1 FROM elementer WHERE url = ?", (url,)` | `SELECT 1` er en effektiv eksistenssjekk — henter ingen data, kun bekreftelse. |
| `        ).fetchone()` | `None` hvis ingen rad finnes. |
| `    return rad is not None` | `True` hvis rad eksisterer. |

---

## 5. Feilhåndtering

| Feilsituasjon | Håndtering | Resultat for systemet |
|---|---|---|
| Fil forsvinner mellom hendelse og prosessering | `if not fil_sti.exists(): return` | Stille hopp. Logger `WARNING`. Neste fil prosesseres normalt. |
| Ingen URL i frontmatter | `if not url: return` | Stille hopp. Logger `WARNING`. |
| Duplikat URL | `fil_sti.unlink(missing_ok=True); return` | Filen slettes, ingen lagring. Logger `INFO`. |
| `manuell-klipp` / `manuell-pdf` mangler i DB | `if kilde_id is None: return` | Stille hopp. Logger `ERROR`. Databasen er ikke initialisert. |
| PDF uten tekst | `if not innhold.strip(): return` | Stille hopp. Logger `WARNING`. |
| Vilkårlig unntak i `_prosesser()` eller `_prosesser_pdf()` | `except Exception: logger.error(..., exc_info=True)` | Feilen isoleres. Logger `ERROR` med stack trace. Neste fil behandles normalt. |
| Ingen DB-rad ved sletting | `if rad is None: return` | Stille hopp. Logger `INFO`. |
| SQLite-feil | Ingen eksplisitt `try/except` i hjelpefunksjoner — propagerer til `on_created`/`on_deleted` | Fanges av ytre `except Exception`. |
| `KeyboardInterrupt` | `except KeyboardInterrupt: observer.stop()` | Ryddig avslutning — observatørtråd stoppes og joinnes. |

---

## 6. Eksterne avhengigheter

| Pakke | Bruk i denne filen | Installasjon |
|---|---|---|
| `watchdog` | `Observer`, `FileSystemEventHandler`, `FileCreatedEvent`, `FileDeletedEvent` — sanntids filsystemovervåking | `uv add watchdog` |
| `pypdf` | `PdfReader` — ekstraher tekst og metadata fra PDF-filer | `uv add pypdf` |
| `pyyaml` | `yaml.safe_load()` — parser YAML-frontmatter fra Markdown-filer | `uv add pyyaml` |
| `python-dotenv` | `load_dotenv()` — laster miljøvariabler fra `.env` | `uv add python-dotenv` |
| `intelligence_monitor.innhenter.vault_skriver` | `lagre_artikkel()` — lagrer artikler i vault og SQLite | Del av prosjektet |

---

## 7. Oppsummering

**Funksjonstabell:**

| Funksjon / Klasse | Ansvar |
|---|---|
| `start(vault_rot, db_sti)` | Starter watchdog, rydder foreldreløse, blokkerer til Ctrl+C. |
| `_InnboksHandler` | Håndterer nye filer i innboks/. Dispatcher til `_prosesser()` og `_prosesser_pdf()`. |
| `_InnboksHandler._prosesser()` | Prosesserer .md-filer: dedup, lagring, flytt til behandlet/. |
| `_InnboksHandler._prosesser_pdf()` | Prosesserer .pdf-filer: dedup, tekstekstrahering, lagring, flytt. |
| `_ArtikkelHandler` | Håndterer slettede artikler i artikler/. Dispatcher til `_rydd_etter_slettet_artikkel()`. |
| `_rydd_etter_slettet_artikkel()` | Sletter bilder og DB-rader for én slettet artikkel. |
| `_rydd_foreldreløse()` | Rydder alle foreldreløse DB-rader ved oppstart. |
| `_domene_fra_url()` | Trekker ut domenenavn for vault-mappestruktur. |
| `_trekk_ut_pdf_innhold()` | Ekstraher tittel og tekst fra PDF via pypdf. |
| `_les_frontmatter_og_kropp()` | Parser YAML-frontmatter og kropp fra Markdown-fil. |
| `_trekk_ut_tittel()` | Prioritert tittelekstrahering: frontmatter → H1 → filnavn. |
| `_hent_kilde_id()` | Slår opp primærnøkkel for en kilde i databasen. |
| `_url_finnes()` | Dedup-sjekk: URL mot elementer-tabellen. |

**Kjørbart eksempel:**

```python
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from intelligence_monitor.innhenter.obsidian_vakt import start

vault_rot = Path(os.getenv("VAULT_ROT", "vault"))
db_sti = Path(os.getenv("DATABASE_STI", "data/monitor.db"))

# Starter vakten — blokkerer til Ctrl+C
start(vault_rot=vault_rot, db_sti=db_sti)
```

Alternativt:

```bash
python -m intelligence_monitor.innhenter.obsidian_vakt
make vakt
```
