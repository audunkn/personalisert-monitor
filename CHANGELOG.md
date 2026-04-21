# Endringslogg

Alle merkbare endringer i dette prosjektet dokumenteres her.

Format følger [Keep a Changelog](https://keepachangelog.com/no/1.1.0/).
Versjonering følger [Semantic Versioning](https://semver.org/).

Enumverdier for `komponent`-feltet: `sammendrag`, `dommer_validering`, `rag_gjenfinning`, `rag_generering`.

---

## [Uutgitt]

### Lagt til
- Konvensjon for beskrivende innledning per oppgavegruppe i `plan.md`-dokumenter dokumentert i `specs/teknologi.md`
- Beskrivende innledning lagt til alle 6 oppgavegrupper i `specs/features/2026-04-21-a0-fundament/plan.md`
- Kodekonvensjon for docstrings (Google-stil) og inline-kommentarer dokumentert i `specs/teknologi.md`
- `Makefile` med 10 targets (`innhent`, `sammendrag`, `review`, `synk`, `regresjon`, `rapport`, `test`, `test-enkelt`, `alle`, `produksjon`) + `help`-target, med utfyllende kommentarer per target som forklarer funksjon, systemkonsekvenser og dataflyt
- `regresjon`-target i `Makefile` dokumentert som bevisst fase A-placeholder — full implementasjon (LLM-dommer + sammenligning mot domeneekspert-score) er fase B-leverabel
- `.env.mal` med komplett feltsett (14 variabler) fra specs/teknologi.md
- `konfig/kilder.yaml` med 5 startkilder (simon-willison, anthropic-blogg, langchain-blogg, decoding-ai, sebastian-raschka)
- Undermapper `innhenter/`, `sammendrag/`, `evaluering/`, `rag/`, `prosessering/`, `levering/`, `analyse/`, `db/` under `src/intelligence_monitor/` — hver med tom `__init__.py`
- `src/intelligence_monitor/sammendrag/prompts/.gitkeep` — bevarerstruktur for prompt-tekstfiler
- `tester/__init__.py` og `tester/konfig/__init__.py` — pytest-pakkestruktur
- `src/intelligence_monitor/__init__.py` — opprettet Python-pakke for kjernemodulen
- `pyproject.toml` med alle fase A–D-avhengigheter og dev-gruppe (pytest, pytest-mock)
- `.gitignore` for `.env`, `*.db`, `__pycache__`, `.venv`
- Python 3.11 virtuelt miljø via `uv venv`
- Alle avhengigheter installert og verifisert med `uv pip install -e ".[dev]"`
- Feature-spesifikasjon A0 — Fundament: `specs/features/2026-04-21-a0-fundament/` med `plan.md`, `requirements.md`, `validation.md`

---

## [0.0.1] — 2026-04-21

### Lagt til
- Spesifikasjonsdokumenter: `specs/visjon.md`, `specs/teknologi.md`, `specs/veikart.md`, `specs/les-meg.md`
