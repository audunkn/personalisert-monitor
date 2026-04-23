# Oppsett og oppstart

*Steg-for-steg guide for å sette opp Intelligence Monitor på en ny maskin eller etter en ren kloning. Følg stegene i rekkefølge.*

---

## Forutsetninger

| Verktøy | Versjon | Formål |
|---|---|---|
| Python | 3.11+ | Kjøretidsmiljø |
| uv | siste | Pakke- og miljøhåndtering |
| Git | siste | Versjonskontroll |
| Obsidian | siste | Vault-visning og manuell klipping |
| Anthropic API-nøkkel | — | Sammendragsmodul (fase A2+) |
| Opik API-nøkkel | — | Observabilitet og triplet-lagring |

Obsidian Web Clipper installeres som nettleserutvidelse. Se [Obsidian Web Clipper](https://obsidian.md/clipper) for installasjonsinstruksjoner.

---

## 1. Klon og installer

```bash
git clone <repo-url>
cd personalisert_monitor

uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

uv pip install -e ".[dev]"
```

Verifiser at pakken er installert:

```bash
python -c "import intelligence_monitor; print('OK')"
```

---

## 2. Konfigurer miljøvariabler

Kopier malen og fyll inn verdiene:

```bash
cp .env.mal .env
```

Åpne `.env` og fyll inn:

| Variabel | Påkrevd | Beskrivelse |
|---|---|---|
| `ANTHROPIC_API_NØKKEL` | Fase A2+ | API-nøkkel fra console.anthropic.com |
| `OPIK_API_NØKKEL` | Fase A2+ | API-nøkkel fra Opik-kontoen |
| `OPIK_PROSJEKTNAVN` | Nei | Standard: `intelligence-monitor` |
| `DATABASE_STI` | Nei | Standard: `data/monitor.db` |
| `VAULT_ROT` | Ja | Absolutt sti til Obsidian-vault-rotmappen |
| `MAKS_ARTIKKEL_TOKENS` | Nei | Standard: `4000` |
| `HENT_FRA` | Nei | Overstyr nedre datointervall midlertidig (YYYY-MM-DD) |
| `HENT_TIL` | Nei | Overstyr øvre datointervall midlertidig (YYYY-MM-DD) |

E-post- og Whisper-felt er kun nødvendig fra fase A5 og fremover.

**Eksempel på VAULT_ROT:**

```
VAULT_ROT=C:\Users\Audun\2026\claude\OBSIDIAN\monitor-evals
```

---

## 3. Konfigurer Obsidian-vault

Opprett vault-mappen hvis den ikke finnes, og sørg for at den inneholder disse undermappene:

```
<vault-rot>/
├── artikler/
├── behandlet/
├── innboks/
└── ressurser/
    └── bilder/
```

Mappene opprettes automatisk av `obsidian_vakt.py` ved oppstart, men det er trygt å opprette dem manuelt på forhånd.

Åpne `<vault-rot>` som vault i Obsidian via *Fil > Åpne mappe som vault*.

**Web Clipper-konfigurasjon:** Pek Web Clipper mot `innboks/`-mappen i din vault. Legg til frontmatter-feltene `url`, `klippet_dato` og `kildetype: manuell` i clipper-malen.

Se `docs/vault-mappestruktur.md` for detaljert beskrivelse av flyten mellom mappene.

---

## 4. Konfigurer innhentingskilder

Åpne `konfig/kilder.yaml` og juster kildene:

```yaml
kilder:
  - navn: Simon Willison
    url: https://simonwillison.net/atom/everything/
    type: rss
    aktiv: true
    emnemerker: [ai, tools]
    hent_fra: 2026-01-01     # Ikke hent artikler eldre enn denne datoen
    hent_til:                # Tom = ingen øvre grense
```

Feltet `hent_fra` bør settes til en rimelig startdato for å unngå å hente hele arkivet ved første kjøring.

---

## 5. Initialiser databasen

Dette steget oppretter alle tabeller og synkroniserer kildelisten fra `konfig/kilder.yaml`:

```bash
python -m intelligence_monitor.db.init
```

Forventet output:

```
Initialiserer database: data/monitor.db
Ferdig.
```

**Kjør dette steget på nytt etter hver oppdatering av kodebasen.** `db.init` er idempotent og sletter aldri eksisterende data. Det er det som legger til nye kolonner når skjemaet utvides — unnlatelse av dette steget er årsaken til feil som `sqlite3.OperationalError: no such column: bilder_json`.

---

## 6. Start bakgrunnsvakten

Bakgrunnsvakten overvåker `innboks/` for nye filer fra Web Clipper og PDF-er, og overvåker `artikler/` for slettinger:

```bash
python -m intelligence_monitor.innhenter.obsidian_vakt
```

Vakten kjører i forgrunnen og blokkerer terminalen. Start den i et eget terminalvindu. Forventet oppstartslogg:

```
INFO intelligence_monitor.innhenter.obsidian_vakt: Vakt startet — overvåker <innboks> og <artikler>
```

Avslutt med `Ctrl+C`.

---

## 7. Verifiser oppsettet

Kjør testsuite for å bekrefte at installasjonen er korrekt:

```bash
make test
```

Alle tester skal passere. Tester bruker midlertidige SQLite-filer og påvirker ikke produksjonsdata.

---

## 8. Første innhenting

Sett et smalt `HENT_FRA`-intervall i `.env` for å begrense første kjøring:

```
HENT_FRA=2026-04-01
```

Kjør innhenting:

```bash
make innhent
```

Artiklene lagres i `<vault-rot>/artikler/` og metadata skrives til SQLite. Verifiser i Obsidian at filer dukker opp i `artikler/`-mappen.

---

## Daglig arbeidsflyt

```
make alle        → henter nye artikler og lager sammendrag (fase A2+)
make review      → manuell gjennomgang i Streamlit-appen
make synk        → synkroniser vurderinger til Opik etter review
make produksjon  → full kjøring inkl. analyserapport
```

Se `make help` for fullstendig oversikt over tilgjengelige targets.

---

## Kjente problemer

### `sqlite3.OperationalError: no such column: <kolonnenavn>`

Årsak: Kodebasen er oppdatert med ny databasekolonne, men `db.init` er ikke kjørt mot den eksisterende databasen.

Løsning:

```bash
python -m intelligence_monitor.db.init
```

### Vakten finner ikke kilde i databasen

Feilmelding: `Kilde 'manuell-klipp' ikke funnet i databasen — kjør db.init først`

Årsak: Databasen er ikke initialisert, eller `konfig/kilder.yaml` er ikke synkronisert.

Løsning: Kjør `python -m intelligence_monitor.db.init`.

### Artikkel lagres ikke fra innboks

Mulige årsaker:
- Filen mangler `url`-felt i YAML-frontmatter — vakten logger WARNING og hopper over filen.
- URL-en er allerede registrert i databasen (duplikat) — filen slettes stille fra `innboks/`.
- Vakten kjører ikke — start den med `python -m intelligence_monitor.innhenter.obsidian_vakt`.

---

## Referanser

| Dokument | Innhold |
|---|---|
| `docs/vault-mappestruktur.md` | Vault-mapper, flyt og kodeansvar |
| `specs/teknologi.md` | Arkitektur, tabellskjema, kodekonvensjoner |
| `specs/veikart.md` | Implementasjonsfaser og status |
| `konfig/kilder.yaml` | Kildekonfigurasjon med datointervall |
| `.env.mal` | Komplett feltsett for miljøvariabler |
