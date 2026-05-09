# kjører.py — Teknisk dokumentasjon

## 1. Overordnet beskrivelse

`kjører.py` er innhentingsskallet for Intelligence Monitor. Filen koordinerer alle aktive innhentingskanaler og sikrer at SQLite-databasen holdes i sync med Obsidian-vault ved å fjerne foreldreløse rader — det vil si databaserader som peker til vault-filer som ikke lenger eksisterer på disk.

Filen løser to konkrete problemer: (1) Det oppstår over tid inkonsistens mellom vault og SQLite når artikler slettes fra vault uten at databasen oppdateres. `kjører.py` rydder opp disse foreldreløse radene automatisk ved hver kjøring. (2) Innhenting fra ulike kilder (RSS, nett, YouTube, Substack) skal koordineres fra ett sted fremfor å kjøres manuelt per kanal.

I fase A1 støttes kun RSS-innhenting. Øvrige kanaler er reservert med TODO-kommentarer til fase A4 og A6.

Filen kjøres som modul (`python -m intelligence_monitor.innhenter.kjører`) eller via Makefile-target (`make innhent`).

**ASCII-flytdiagram:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  oppdater()                                                             │
│                                                                         │
│  1. Les DATABASE_STI og VAULT_ROT fra miljøvariabler (.env)            │
│  2. Kall _rydd_foreldreløse(db_sti, vault_rot)                         │
│         │                                                               │
│         ├─► SQLite READ:                                                │
│         │     SELECT id, vault_sti, bilder_json                        │
│         │     FROM elementer WHERE vault_sti IS NOT NULL               │
│         │                                                               │
│         └─► for kvar rad:                                              │
│                 ├─ filen finnes? ──YES──► continue (neste rad)         │
│                 │                                                       │
│                 NO                                                      │
│                 ├─► json.loads(bilder_json) → liste med filnavn        │
│                 ├─► slett bilder fra disk (vault/ressurser/bilder/)    │
│                 └─► SQLite WRITE (per element):                         │
│                         DELETE evalueringstriplets WHERE element_id    │
│                         DELETE sammendrag WHERE element_id             │
│                         DELETE elementer WHERE id                      │
│                                                                         │
│  3. rss.innhent_alle() ──► nye_rss (int)                               │
│  4. Logg totalt antall nye artikler                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

**Mockup — sideeffekter per kjøring:**

```
monitor.db (SQLite)
├── elementer            ← foreldreløse rader slettes
├── sammendrag           ← tilhørende rader slettes
└── evalueringstriplets  ← tilhørende rader slettes

vault/
└── ressurser/
    └── bilder/
        └── [bildefiler slettes hvis tilhørende artikkel mangler]

Terminallogg:
2026-05-09 12:00:00 INFO     intelligence_monitor.innhenter.kjører: === Innhenting starter ===
2026-05-09 12:00:00 INFO     intelligence_monitor.innhenter.kjører: Ryddet 2 foreldreløse element(er) fra SQLite
2026-05-09 12:00:01 INFO     intelligence_monitor.innhenter.kjører: === Innhenting ferdig — 5 nye artikler totalt ===
```

---

## 2. Importer og moduloppsett

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `from __future__ import annotations` | Aktiverer utsatt evaluering av typeannotering (PEP 563). Typeannoteringar som `-> int` og `Path` lagres som strenger ved innlasting i stedet for å evalueres umiddelbart. Nødvendig for fremtidskompatibilitet med Python-typing. |
| `import json` | Standardbibliotek for JSON-parsing. Brukes til å deserialisere `bilder_json`-kolonnen fra SQLite, som er en JSON-kodet liste med bildefilnavn. |
| `import logging` | Standardbibliotek for strukturert loggutskrift. Brukes til å rapportere innhentingsstatus og antall slettede elementer. |
| `import os` | Standardbibliotek for tilgang til operativsystemet. Brukes utelukkende til `os.getenv()` for å lese miljøvariabler. |
| `from pathlib import Path` | Objektorientert filsti-håndtering. Alle stier i filen er `Path`-objekter fremfor råstrenger, noe som gir portabilitet og enkle operasjoner som `/`-konkatenering og `.exists()`. |
| `from dotenv import load_dotenv` | Importerer `load_dotenv`-funksjonen fra `python-dotenv`-pakken. Laster nøkkelverdi-par fra `.env`-filen inn i `os.environ`. |
| `load_dotenv()` | Kalles umiddelbart ved modulinnlasting for å sikre at `DATABASE_STI` og `VAULT_ROT` er tilgjengelig i miljøet før de leses. |
| `from intelligence_monitor.innhenter import rss  # noqa: E402` | Importerer RSS-innhentingsmodulen. Plassert etter `load_dotenv()` fordi `rss`-modulen kan lese miljøvariabler ved import. `# noqa: E402` undertrykker flake8-advarsel om import plassert etter ikke-import-kode. |
| `logging.basicConfig(` | Konfigurerer rot-loggeren for hele applikasjonen. Siden dette kalles tidlig i modulen, gjelder innstillingene alle logger-instanser med mindre de overstyres eksplisitt. |
| `    level=logging.INFO,` | Setter minimumsterskel for logging til INFO. DEBUG-meldinger vil ikke vises. |
| `    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",` | Definerer loggformatet: tidsstempel, loggnivå (venstrejustert i 8 tegn), logger-navn (modulsti) og melding. |
| `    datefmt="%Y-%m-%d %H:%M:%S",` | Formaterer tidsstempelet som `2026-05-09 12:00:00`. |
| `)` | Avslutter `basicConfig()`-kallet. |
| `logger = logging.getLogger(__name__)` | Oppretter en logger bundet til denne modulen. `__name__` er `intelligence_monitor.innhenter.kjører` ved import og `__main__` ved direkte kjøring. |
| `_PROSJEKTROT = Path(__file__).resolve().parents[3]` | Beregner prosjektrotens absolutte sti. `__file__` er stien til `kjører.py`; `.parents[0]` = `innhenter/`; `.parents[1]` = `intelligence_monitor/`; `.parents[2]` = `src/`; `.parents[3]` = prosjektrot. |

---

## 3. Offentlig API — oppdater()

`oppdater()` er hovedinngangspunktet for innhenting. Den rydder foreldreløse SQLite-rader og kjører alle aktive innhentingskanaler i sekvens. Konfigurasjon leses fra miljøvariabler — funksjonen tar ingen parametere. Returnerer `None`; effektene er logglinjer og sideeffekter i database og vault.

**Miljøvariabler (erstatning for parametere):**

| Variabel | Type | Standardverdi | Forklaring |
|---|---|---|---|
| `DATABASE_STI` | `str` (sti) | `<prosjektrot>/data/monitor.db` | Absolutt sti til SQLite-databasefilen. |
| `VAULT_ROT` | `str` (sti) | `<prosjektrot>/vault` | Rotmappe for Obsidian-vault. |

**Linje-for-linje:**

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def oppdater() -> None:` | Definerer den offentlige funksjonen. `-> None` angir at den ikke returnerer en verdi. |
| `"""Rydder foreldreløse SQLite-rader og kjører alle aktive innhentingskanaler."""` | Docstring — én-linje oppsummering av funksjonens ansvar. |
| `logger.info("=== Innhenting starter ===")` | Logger startmelding. Brukes til å identifisere kjøringens begynnelse i loggfilen. |
| `db_sti = Path(os.getenv("DATABASE_STI", str(_PROSJEKTROT / "data" / "monitor.db")))` | Leser `DATABASE_STI` fra miljøet. Hvis variabelen ikke er satt, brukes standardstien `<prosjektrot>/data/monitor.db`. Resultatet konverteres til `Path`-objekt. |
| `vault_rot = Path(os.getenv("VAULT_ROT", str(_PROSJEKTROT / "vault")))` | Leser `VAULT_ROT` fra miljøet på tilsvarende måte. Standardverdi er `<prosjektrot>/vault`. |
| `_rydd_foreldreløse(db_sti, vault_rot)` | Kaller hjelpefunksjonen som fjerner SQLite-rader der vault-filen mangler. Returverdien (antall slettede) brukes ikke videre — loggingen skjer inne i hjelpefunksjonen. |
| `nye_rss = rss.innhent_alle()` | Kjører RSS-innhenting for alle konfigurerte kilder. Returnerer antall nye artikler hentet i denne kjøringen. |
| `# TODO A4: legg til nett.innhent_alle() og substack.innhent_alle()` | Reservert plass for web- og Substack-innhenting som implementeres i fase A4. |
| `# TODO A6: legg til youtube.innhent_alle()` | Reservert plass for YouTube-innhenting som implementeres i fase A6. |
| `totalt = nye_rss` | Summer antall nye artikler fra alle kanaler. I A1 er dette kun RSS-tallet. |
| `logger.info("=== Innhenting ferdig — %d nye artikler totalt ===", totalt)` | Logger avslutningsmelding med totalt antall nye artikler. `%d` er printf-stil formatering — logging-modulens eget format, ikke f-streng. |

---

## 4. Hjelpefunksjoner

### _rydd_foreldreløse(db_sti, vault_rot)

Funksjonen sikrer konsistens mellom SQLite-databasen og Obsidian-vault. Den henter alle artikler med en registrert vault-sti og sjekker om filen fortsatt finnes på disk. Manglende filer regnes som foreldreløse. For slike elementer slettes tilhørende bildefiler fra disk, og deretter fjernes alle relaterte databaserader i riktig rekkefølge.

> **Begrep — foreldreløs rad**: En rad i `elementer`-tabellen der `vault_sti` peker til en fil som ikke lenger finnes i vault. Kan oppstå hvis brukeren sletter en artikkel direkte i Obsidian uten å gå via applikasjonen.

> **Begrep — evalueringstriplets**: Tredoble vurderinger (kontekst, spørsmål, svar) lagret i en egen tabell, knyttet til et element via `element_id`. Brukes til evaluering og RAG-oppsett.

> **Begrep — kontekst-manager (`with`-blokk)**: En Python-konstruksjon som automatisk kaller oppryddingskode (her: commit/rollback av SQLite-transaksjon) ved utgang av blokken, uavhengig av om det oppstår feil.

**Parametertabell:**

| Parameter | Type | Forklaring |
|---|---|---|
| `db_sti` | `Path` | Absolutt sti til SQLite-databasefilen. Eksempel: `Path("data/monitor.db")`. |
| `vault_rot` | `Path` | Rotmappe for Obsidian-vault. Eksempel: `Path("vault")`. |

**Linje-for-linje:**

| Kodelinje (fullstendig) | Forklaring |
|---|---|
| `def _rydd_foreldreløse(db_sti: Path, vault_rot: Path) -> int:` | Definerer funksjonen. Prefiks `_` markerer den som intern (ikke del av offentlig API). Returnerer `int` — antall slettede elementer. |
| `"""Sletter SQLite-rader der vault-filen ikke lenger eksisterer.` | Start av docstring. |
| `    Henter alle elementer med vault_sti IS NOT NULL og sjekker om filen` | Docstring fortsetter med detaljert atferdsbeskrivelse. |
| `    finnes. Manglende filer behandles likt som i obsidian_vakt:` | Refererer til `obsidian_vakt`-modulen som bruker tilsvarende slettelogikk. |
| `    bilder slettes fra vault/ressurser/bilder/, deretter evalueringstriplets,` | Dokumenterer slettesekvensen: disk først, deretter database. |
| `    sammendrag og elementer-raden.` | Avslutter beskrivelsen av slettesekvensen. |
| `    Args:` | Start av Args-seksjon i docstring. |
| `        db_sti: Sti til SQLite-databasefilen.` | Dokumenterer `db_sti`-parameteren. |
| `        vault_rot: Rot-mappe for Obsidian-vault.` | Dokumenterer `vault_rot`-parameteren. |
| `    Returns:` | Start av Returns-seksjon. |
| `        Antall slettede elementer.` | Returnert verdi er et heltall. |
| `    """` | Avslutter docstring. |
| `    with sqlite3.connect(db_sti) as tilkobling:` | Åpner tilkobling til SQLite som kontekst-manager. Transaksjonen committes automatisk ved utgang. |
| `        rader = tilkobling.execute(` | Starter en SQL-spørring. `.execute()` returnerer en cursor. |
| `            "SELECT id, vault_sti, bilder_json FROM elementer WHERE vault_sti IS NOT NULL"` | SQL-spørring: henter `id`, `vault_sti` og `bilder_json` for alle elementer med en registrert vault-sti. `IS NOT NULL` ekskluderer elementer som aldri fikk en vault-fil. |
| `        ).fetchall()` | Henter alle rader fra cursoren som en liste av tupler, f.eks. `[(1, "innboks/art.md", '["bilde.jpg"]'), ...]`. |
| `    antall_slettet = 0` | Initialiserer telleren for slettede elementer. |
| `    bilde_mappe = vault_rot / "ressurser" / "bilder"` | Bygger sti til bildemappen ved `/`-konkatenering med `Path`. |
| `    for element_id, vault_sti, bilder_json_tekst in rader:` | Itererer over alle hentede rader. Hvert tuppel pakkes ut i tre variabler. |
| `        if (vault_rot / vault_sti).exists():` | Sjekker om vault-filen fortsatt finnes på disk. `vault_rot / vault_sti` gir full absolutt sti. |
| `            continue` | Filen finnes — hopp til neste rad uten videre behandling. |
| `        bildefilnavn: list[str] = json.loads(bilder_json_tekst) if bilder_json_tekst else []` | Deserialiserer `bilder_json`-kolonnen. Hvis kolonnen er `NULL` eller tom (falsy), brukes tom liste for å unngå `json.loads(None)`-feil. |
| `        for filnavn in bildefilnavn:` | Itererer over hvert bildefilnavn tilknyttet elementet. |
| `            bilde_fil = bilde_mappe / filnavn` | Bygger full absolutt sti til bildefilen. |
| `            if bilde_fil.exists():` | Sjekker om bildefilen faktisk finnes (kan allerede være slettet). |
| `                bilde_fil.unlink()` | Sletter bildefilen fra disk. `.unlink()` er `Path`-ekvivalenten til `os.remove()`. |
| `        with sqlite3.connect(db_sti) as tilkobling:` | Åpner ny tilkobling for skriveoperasjoner. Én tilkobling per element sikrer at feil på ett element ikke avbryter oppryddingen av øvrige. |
| `            tilkobling.execute(` | Starter første SQL-sletteoperasjon. |
| `                "DELETE FROM evalueringstriplets WHERE element_id = ?", (element_id,)` | Sletter alle evalueringstriplets tilknyttet elementet. `?` er parametrisert spørring (hindrer SQL-injeksjon). `(element_id,)` er en tuppel med én verdi. |
| `            )` | Avslutter første `execute()`-kall. |
| `            tilkobling.execute(` | Starter andre SQL-sletteoperasjon. |
| `                "DELETE FROM sammendrag WHERE element_id = ?", (element_id,)` | Sletter alle sammendrag tilknyttet elementet. |
| `            )` | Avslutter andre `execute()`-kall. |
| `            tilkobling.execute("DELETE FROM elementer WHERE id = ?", (element_id,))` | Sletter selve element-raden. Kjøres sist for å bevare referanseintegritet — barn slettes alltid før forelder. |
| `        antall_slettet += 1` | Øker telleren etter at ett element er fullstendig ryddet. |
| `    if antall_slettet:` | Sjekker om noen elementer ble slettet. `0` er falsy — unngår overflødig loggutskrift ved normale kjøringer uten foreldreløse. |
| `        logger.info("Ryddet %d foreldreløse element(er) fra SQLite", antall_slettet)` | Logger antall slettede elementer. |
| `    return antall_slettet` | Returnerer antall slettede elementer til kalleren. `oppdater()` bruker ikke verdien, men den er nyttig for testing. |

**Mockup — input → output:**

```
Inndata (SQLite-rader):
  elementer: [(1, "innboks/artikkel1.md", '["bilde1.jpg"]'),
              (2, "innboks/artikkel2.md", None)]

Vault-disk:
  vault/innboks/artikkel1.md    → FINNES IKKE
  vault/innboks/artikkel2.md    → FINNES IKKE
  vault/ressurser/bilder/bilde1.jpg → FINNES

Etter kjøring:
  Disk:    bilde1.jpg slettet
  SQLite:  evalueringstriplets WHERE element_id IN (1, 2) → slettet
           sammendrag WHERE element_id IN (1, 2) → slettet
           elementer WHERE id IN (1, 2) → slettet
  Retur:   2
```

---

## 5. Feilhåndtering

| Feilsituasjon | Håndtering | Resultat for systemet |
|---|---|---|
| `bilder_json_tekst` er `NULL` i SQLite | `if bilder_json_tekst else []` — bruker tom liste | Elementet slettes uten forsøk på bildeslettig. Ingen unntak kastes. |
| Bildefil finnes ikke på disk | `if bilde_fil.exists(): bilde_fil.unlink()` — sjekk før sletting | Slettingen hoppes over stille. Ingen feil. |
| SQLite-tilkobling feiler (f.eks. låst fil) | Ingen eksplisitt `try/except` — `sqlite3`-unntak propagerer opp | `oppdater()` avbrytes med stack trace i terminalen. |
| Miljøvariabel mangler (`os.getenv` returnerer `None`) | Standardverdi benyttes: `_PROSJEKTROT / "data" / "monitor.db"` og `_PROSJEKTROT / "vault"` | Programmet fortsetter med standardstiene. |
| `rss.innhent_alle()` kaster unntak | Ingen `try/except` i `oppdater()` — unntak propagerer | `oppdater()` avbrytes. Foreldreløs-opprydding er allerede gjennomført og rulles ikke tilbake. |

**Merk:** Disk-sletting og SQLite-sletting er ikke atomiske i forhold til hverandre. Hvis bildeslettig (disk) lykkes men SQLite-skriving feiler, vil bildet være borte mens databaseraden fortsatt eksisterer. Det finnes ingen rollback for disksiden.

---

## 6. Eksterne avhengigheter

| Pakke | Bruk i denne filen | Installasjon |
|---|---|---|
| `python-dotenv` | `load_dotenv()` — laster `DATABASE_STI` og `VAULT_ROT` fra `.env`-fil til `os.environ` | `uv add python-dotenv` |
| `intelligence_monitor.innhenter.rss` | `rss.innhent_alle()` — intern modul for RSS-innhenting | Del av prosjektet |

Standardbibliotekmoduler (`json`, `logging`, `os`, `pathlib`, `sqlite3`) krever ingen installasjon.

---

## 7. Oppsummering

**Funksjonstabell:**

| Funksjon | Ansvar |
|---|---|
| `oppdater()` | Koordinerer opprydding og innhenting. Leser konfigurasjon fra miljøvariabler. |
| `_rydd_foreldreløse(db_sti, vault_rot)` | Fjerner SQLite-rader og bildefiler der tilhørende vault-fil mangler. |

**Kjørbart eksempel:**

```python
import os
from pathlib import Path

# Sett miljøvariabler (normalt definert i .env-filen)
os.environ["DATABASE_STI"] = str(Path("data/monitor.db").resolve())
os.environ["VAULT_ROT"] = str(Path("vault").resolve())

from intelligence_monitor.innhenter.kjører import oppdater

# Kjør innhenting: rydder foreldreløse SQLite-rader og henter nye RSS-artikler
oppdater()
```

Alternativt fra terminalen:

```bash
# Via Python-modul
python -m intelligence_monitor.innhenter.kjører

# Via Makefile
make innhent
```
