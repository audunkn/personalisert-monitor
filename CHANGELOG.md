# Endringslogg

Alle merkbare endringer i dette prosjektet dokumenteres her.

Format følger [Keep a Changelog](https://keepachangelog.com/no/1.1.0/).
Versjonering følger [Semantic Versioning](https://semver.org/).

Enumverdier for `komponent`-feltet: `sammendrag`, `dommer_validering`, `rag_gjenfinning`, `rag_generering`.

---

## [Uutgitt]

### Lagt til
- Beslutning om databaseplassering (`data/monitor.db`, `DATABASE_STI` i `.env`) dokumentert i `requirements.md` og `validation.md` *(2026-04-22 12:20)*
- Konvensjon for tidsstempel på CHANGELOG-oppføringer (`*(YYYY-MM-DD HH:MM)*`) dokumentert i `specs/teknologi.md` *(2026-04-22 12:05)*
- Konvensjon for beskrivende kommentarer i konfigurasjonsfiler (`.gitignore`, `Makefile`, YAML, `.env.mal`) dokumentert i `specs/teknologi.md` *(2026-04-22 12:05)*
- Beskrivende kommentarer i `.gitignore` for vault-regler — forklarer hva som ignoreres og hva som bevares *(2026-04-22 11:57)*
- Vault-mappestruktur opprettet: `vault/artikler/`, `vault/ressurser/bilder/`, `vault/innboks/`, `vault/behandlet/` — hver med `.gitkeep` for Git-sporing *(2026-04-22 11:51)*
- `.gitignore` justert: `vault/**` ignorerer innhold, `!vault/*/`, `!vault/*/*/` og `!vault/**/.gitkeep` bevarer mappestruktur *(2026-04-22 11:51)*
- Konvensjon for beskrivende innledning per oppgavegruppe i `plan.md`-dokumenter dokumentert i `specs/teknologi.md` *(2026-04-21 22:16)*
- Beskrivende innledning lagt til alle 6 oppgavegrupper i `specs/features/2026-04-21-a0-fundament/plan.md` *(2026-04-21 22:16)*
- Kodekonvensjon for docstrings (Google-stil) og inline-kommentarer dokumentert i `specs/teknologi.md` *(2026-04-21 22:09)*
- `regresjon`-target i `Makefile` dokumentert som bevisst fase A-placeholder — full implementasjon (LLM-dommer + sammenligning mot domeneekspert-score) er fase B-leverabel *(2026-04-21 22:03)*
- `Makefile` med 10 targets (`innhent`, `sammendrag`, `review`, `synk`, `regresjon`, `rapport`, `test`, `test-enkelt`, `alle`, `produksjon`) + `help`-target, med utfyllende kommentarer per target som forklarer funksjon, systemkonsekvenser og dataflyt *(2026-04-21 21:43)*
- `.env.mal` med komplett feltsett (14 variabler) fra specs/teknologi.md *(2026-04-21 21:43)*
- `konfig/kilder.yaml` med 5 startkilder (simon-willison, anthropic-blogg, langchain-blogg, decoding-ai, sebastian-raschka) *(2026-04-21 21:43)*
- Undermapper `innhenter/`, `sammendrag/`, `evaluering/`, `rag/`, `prosessering/`, `levering/`, `analyse/`, `db/` under `src/intelligence_monitor/` — hver med tom `__init__.py` *(2026-04-21 21:18)*
- `src/intelligence_monitor/sammendrag/prompts/.gitkeep` — bevarer struktur for prompt-tekstfiler *(2026-04-21 21:18)*
- `tester/__init__.py` og `tester/konfig/__init__.py` — pytest-pakkestruktur *(2026-04-21 21:18)*
- `src/intelligence_monitor/__init__.py` — opprettet Python-pakke for kjernemodulen *(2026-04-21 21:09)*
- Feature-spesifikasjon A0 — Fundament: `specs/features/2026-04-21-a0-fundament/` med `plan.md`, `requirements.md`, `validation.md` *(2026-04-21 20:32)*
- `pyproject.toml` med alle fase A–D-avhengigheter og dev-gruppe (pytest, pytest-mock) *(2026-04-21 20:24)*
- Python 3.11 virtuelt miljø via `uv venv` *(2026-04-21 20:24)*
- Alle avhengigheter installert og verifisert med `uv pip install -e ".[dev]"` *(2026-04-21 20:24)*
- `.gitignore` for `.env`, `*.db`, `__pycache__`, `.venv` *(2026-04-21 20:13)*

---

## [0.0.1] — 2026-04-21

### Lagt til
- Spesifikasjonsdokumenter: `specs/visjon.md`, `specs/teknologi.md`, `specs/veikart.md`, `specs/les-meg.md`
