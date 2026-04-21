# A0 — Fundament: Implementeringsplan

## Oppgavegruppe 1: Mappestruktur

- [ ] Opprett `src/intelligence_monitor/` med tom `__init__.py`
- [ ] Opprett undermapper: `innhenter/`, `sammendrag/prompts/`, `evaluering/`, `rag/`, `prosessering/`, `levering/`, `analyse/`, `db/`
- [ ] Legg `__init__.py` i hver undermappe
- [ ] Opprett `tester/` med `konfig/` og tom `__init__.py` i begge
- [ ] Opprett `specs/features/` (allerede gjort)

---

## Oppgavegruppe 2: Prosjektkonfigurasjon

- [ ] Lag `Makefile` med targets: `innhent`, `sammendrag`, `review`, `synk`, `regresjon`, `test`, `test-enkelt`, `rapport`, `alle`, `produksjon`
- [ ] Lag `.env.mal` med komplett feltsett (se `specs/teknologi.md` → Miljøvariabler)
- [ ] Lag `.env` fra `.env.mal` (ikke committes — dekkes av `.gitignore`)
- [ ] Lag `konfig/kilder.yaml` med fem startkilder og `hent_fra`/`hent_til` per kilde

Startkilder (`konfig/teknologi.md` → Startkilder):
1. Simon Willison — RSS — simonwillison.net/atom/everything/
2. Anthropic-bloggen — RSS — anthropic.com/rss.xml
3. LangChain-bloggen — RSS — blog.langchain.dev/rss/
4. Paul Iusztin (Decoding AI) — Substack — decodingai.substack.com
5. Sebastian Raschka — Substack — magazine.sebastianraschka.com

---

## Oppgavegruppe 3: Vault-mapper

- [ ] Opprett vault-mappestruktur: `artikler/`, `ressurser/bilder/`, `innboks/`, `behandlet/`
- [ ] Legg `.gitkeep` i hver tom mappe (bevarer struktur i Git)

*Vault-mappen for faktisk innhold konfigureres via `VAULT_STI` i `.env` og er i `.gitignore`.*

---

## Oppgavegruppe 4: Database

- [ ] Skriv `src/intelligence_monitor/db/skjema.sql` med fase A-tabeller:
  - `kilder` — inkl. `hent_fra`, `hent_til`, `aktiv`-flagg
  - `elementer` — inkl. `vault_sti`, `guid`, `dead_letter`-flagg
  - `sammendrag` — inkl. `element_id`, `prompt_versjon`
  - `evalueringstriplets` — inkl. `komponent`, `er_regresjonstest`, `tidsstempel`
- [ ] Skriv `src/intelligence_monitor/db/init.py`:
  - Idempotent tabellopprettelse (`CREATE TABLE IF NOT EXISTS`)
  - Les `konfig/kilder.yaml` og synkroniser til `kilder`-tabellen
  - Ny kilde → insert. Fjernet kilde → sett `aktiv = false`. Eksisterende → oppdater.

---

## Oppgavegruppe 5: Opik og regulatorisk kontekst

- [ ] Konfigurer Opik i `src/intelligence_monitor/db/init.py` eller egen modul: `fail_silently=True`, les nøkkel fra env
- [ ] Verifiser at Opik-kontoen er opprettet og API-nøkkel fungerer
- [ ] Skriv `specs/regulatorisk-kontekst.md` — strukturert utkast med høydepunkter fra:
  - EU AI Act (risikoklassifisering, krav til høyrisiko-systemer, transparens)
  - NIS2 (sikkerhetskrav, varslingsplikter, scope)
  - ISO 42001 (AI Management System, risikovurdering, dokumentasjon)

---

## Oppgavegruppe 6: Enhetstester

- [ ] Skriv `tester/test_db_init.py` — to tester:
  1. **Idempotens**: Kjør `init.py` to ganger mot midlertidig SQLite-fil. Verifiser at alle tabeller finnes og ingen data er slettet.
  2. **YAML→SQLite-synk**: Legg til ny kilde i YAML, kjør `init.py`. Verifiser at kilden dukker opp med korrekt `hent_fra` og `aktiv = true`. Fjern kilden fra YAML, kjør på nytt. Verifiser `aktiv = false`.
- [ ] Kjør `make test` — alle tester grønne

---

## Rekkefølge

Gruppe 1 → 2 → 3 → 4 → 5 → 6. Gruppe 4 avhenger av at konfig/kilder.yaml finnes (gruppe 2).
