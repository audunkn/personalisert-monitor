# A0 — Fundament: Krav og kontekst

## Formål

Etablere det komplette tekniske grunnlaget som alle etterfølgende moduler (A1–D3) bygger på: mappestruktur, pakkeoppsett, databaseskjema, konfigurasjonsfiler og regulatorisk referansedokument.

---

## Scope

**Inkludert i denne featuren:**
- Mappestruktur (`src/intelligence_monitor/`, `tester/`, `konfig/`)
- `Makefile` med alle prosjekt-targets
- `.env.mal` og lokal `.env`
- `konfig/kilder.yaml` med fem startkilder
- Vault-mappestruktur med `.gitkeep`
- `db/skjema.sql` og `db/init.py`
- Opik-konfigurasjon
- `specs/regulatorisk-kontekst.md` (strukturert utkast)
- Enhetstester for `db/init.py`

**Ikke inkludert (egen branch — A0b):**
- `vault_skriver.py` — filskriving med UUID-konsistensrekkefølge
- `obsidian_vakt.py` — watchdog for innboks/
- Obsidian Web Clipper-konfigurasjon

---

## Beslutninger

### DB-skjema: kun fase A-tabeller
Skjemaet definerer fire tabeller: `kilder`, `elementer`, `sammendrag`, `evalueringstriplets`. Tabellene `vektorer` og `rag_spor` (fase C) legges til inkrementelt når fase C starter. Reduserer kompleksitet nå og unngår premature skjemaforpliktelser.

Se `specs/teknologi.md` → Databasetabeller for komplett feltsett per tabell.

### regulatorisk-kontekst.md: strukturert utkast
Innholdet lages som et konsist oppslagsverk summarizer-prompten kan inkludere direkte. Kalibreringsfasen (A3) vil avgjøre om granulariteten er tilstrekkelig, eller om regulatorisk RAG (fase C/D) er nødvendig.

Se `specs/visjon.md` → Regulatorisk kontekst i sammendragene for bakgrunn.

### Idempotent init
`db/init.py` bruker `CREATE TABLE IF NOT EXISTS` og er trygt å kjøre gjentatte ganger uten å slette data. YAML→SQLite-synk følger upsert-logikk: ny kilde → insert, fjernet → `aktiv = false`, eksisterende → oppdater feltene.

Se `specs/teknologi.md` → Idempotent tabellopprettelse og Kildesynkronisering.

### Lagringsprinsipp
Obsidian-vault eier artikkeltekst og bilder. SQLite eier all operasjonell og evalueringsorientert data. Opik eier observabilitet. Ingen av de tre lagrer det de andre eier.

Se `specs/visjon.md` → Lagringsfilosofi.

---

## Konfigurasjonsfelter (.env.mal)

Alle felter fra `specs/teknologi.md` → Miljøvariabler:
- `ANTHROPIC_API_NØKKEL`
- `OPIK_API_NØKKEL`, `OPIK_PROSJEKTNAVN`
- `VAULT_STI`
- `MAKS_ARTIKKEL_TOKENS`
- `HENT_FRA`, `HENT_TIL`
- SMTP-felter (vert, port, bruker, passord, mottakere)
- `WHISPER_MODELL`, `OPENAI_API_NØKKEL`

---

## Avhengigheter

- Ingen andre moduler er avhengige av A0 — det er A0 som er avhengigheten for alle.
- Forutsetter at Python-miljø og pakker er installert (gjort i `chore: sett opp Python-miljø`).
- Forutsetter at Opik-konto er opprettet.
