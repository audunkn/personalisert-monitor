# A0 — Fundament: Implementeringsplan

## Oppgavegruppe 1: Mappestruktur

Etablerer katalogstrukturen som all Python-kode, tester og spesifikasjoner bygges på. En entydig mappestruktur fra dag én gjør det enkelt å finne frem og forhindrer at kode havner på feil sted etter hvert som prosjektet vokser.

- [x] Opprett `src/intelligence_monitor/` med tom `__init__.py`
- [x] Opprett undermapper: `innhenter/`, `sammendrag/prompts/`, `evaluering/`, `rag/`, `prosessering/`, `levering/`, `analyse/`, `db/`
- [x] Legg `__init__.py` i hver undermappe
- [x] Opprett `tester/` med `konfig/` og tom `__init__.py` i begge
- [x] Opprett `specs/features/` (allerede gjort)

---

## Oppgavegruppe 2: Prosjektkonfigurasjon

Setter opp verktøyene som alle utviklere og systemet bruker daglig: Makefile for kommandolinjearbeidsflyt, miljøvariabler for hemmeligheter og konfigurasjon, og kildelisten som bestemmer hva systemet overvåker. Uten denne konfigurasjonen kan ingen andre deler av systemet kjøres.

- [x] Lag `Makefile` med targets: `innhent`, `sammendrag`, `review`, `synk`, `regresjon`, `test`, `test-enkelt`, `rapport`, `alle`, `produksjon`
- [x] Legg til utfyllende kommentarer i `Makefile` — forklarer hver targets funksjon og systemkonsekvenser
  - **Merknad:** `regresjon`-targeten er en bevisst fase A-placeholder for et fase B-leverabel. Full implementasjon krever LLM-dommer og vil feile med «modul ikke funnet» frem til fase B er levert.
- [x] Lag `.env.mal` med komplett feltsett (se `specs/teknologi.md` → Miljøvariabler)
- [x] Lag `.env` fra `.env.mal` (ikke committes — dekkes av `.gitignore`)
- [x] Lag `konfig/kilder.yaml` med fem startkilder og `hent_fra`/`hent_til` per kilde

Startkilder (`konfig/teknologi.md` → Startkilder):
1. Simon Willison — RSS — simonwillison.net/atom/everything/
2. Anthropic-bloggen — RSS — anthropic.com/rss.xml
3. LangChain-bloggen — RSS — blog.langchain.dev/rss/
4. Paul Iusztin (Decoding AI) — Substack — decodingai.substack.com
5. Sebastian Raschka — Substack — magazine.sebastianraschka.com

---

## Oppgavegruppe 3: Vault-mapper

Oppretter mappestrukturen i Obsidian-vaulten der artikkeltekst og bilder lagres. Disse mappene eksisterer kun lokalt og er ikke en del av Git-repoet — de peker på den faktiske Obsidian-vaulten via `VAULT_STI` i `.env`.

- [x] Opprett vault-mappestruktur: `artikler/`, `ressurser/bilder/`, `innboks/`, `behandlet/`
- [x] Legg `.gitkeep` i hver tom mappe (bevarer struktur i Git)

*Vault-mappen for faktisk innhold konfigureres via `VAULT_STI` i `.env` og er i `.gitignore`.*

---

## Oppgavegruppe 4: Database

Definerer og oppretter SQLite-databasen som er systemets primærkilde for metadata, sammendrag og evalueringstriplets. Initialisering er idempotent — skriptet kan kjøres gjentatte ganger uten å slette eksisterende data, og synkroniserer automatisk kildelisten fra YAML-konfig til databasen.

- [x] Skriv `src/intelligence_monitor/db/skjema.sql` med fase A-tabeller:
  - `kilder` — inkl. `hent_fra`, `hent_til`, `aktiv`-flagg
  - `elementer` — inkl. `vault_sti`, `guid`, `dead_letter`-flagg
  - `sammendrag` — inkl. `element_id`, `prompt_versjon`
  - `evalueringstriplets` — inkl. `komponent`, `er_regresjonstest`, `tidsstempel`
- [x] Skriv `src/intelligence_monitor/db/init.py`:
  - Idempotent tabellopprettelse (`CREATE TABLE IF NOT EXISTS`)
  - Les `konfig/kilder.yaml` og synkroniser til `kilder`-tabellen
  - Ny kilde → insert. Fjernet kilde → sett `aktiv = false`. Eksisterende → oppdater.

---

## Oppgavegruppe 5: Opik-konfigurasjon

Kobler systemet til Opik for sporbarhet av alle LLM-kall. Opik-integrasjon er en forutsetning for observabilitet i fase A og videre.

- [x] Konfigurer Opik i egen modul `src/intelligence_monitor/opik_konfig.py`: obligatorisk, les nøkkel fra env, kall fra `db/init.py`
- [x] Verifiser at Opik-kontoen er opprettet og API-nøkkel fungerer

---

## Oppgavegruppe 6: Regulatorisk kontekst

Produserer det regulatoriske referansedokumentet som summarizer-prompten bruker for å koble artikkelinnhold til relevant lovgivning. Dokumentet er et selvstendig leverabel og kan oppdateres uavhengig av resten av systemet.

- [x] Skriv `specs/regulatorisk-kontekst.md` — strukturert utkast med høydepunkter fra:
  - EU AI Act (risikoklassifisering, krav til høyrisiko-systemer, transparens)
  - NIS2 (sikkerhetskrav, varslingsplikter, scope)
  - ISO 42001 (AI Management System, risikovurdering, dokumentasjon)
  - Datatilsynet og norsk AI-veiledning (DPIA, GDPR-krysningspunkter, åpenhet)
  - NSM grunnprinsipper (leverandørkjede, tilgangsstyring, hendelseshåndtering)

---

## Oppgavegruppe 7: Enhetstester

Verifiserer at databaselaget fungerer korrekt: at tabeller kan opprettes gjentatte ganger uten feil (idempotens), og at kildelisten i YAML-konfig alltid reflekteres korrekt i databasen. Grønne tester her er inngangskriteriet for å starte på A1.

- [x] Skriv `tester/test_db_init.py` — to tester:
  1. **Idempotens**: Kjør `init.py` to ganger mot midlertidig SQLite-fil. Verifiser at alle tabeller finnes og ingen data er slettet.
  2. **YAML→SQLite-synk**: Legg til ny kilde i YAML, kjør `init.py`. Verifiser at kilden dukker opp med korrekt `hent_fra` og `aktiv = true`. Fjern kilden fra YAML, kjør på nytt. Verifiser `aktiv = false`.
- [x] Kjør `make test` — alle tester grønne

---

## Rekkefølge

Gruppe 1 → 2 → 3 → 4 → 5 → 6 → 7. Gruppe 4 avhenger av at konfig/kilder.yaml finnes (gruppe 2).
