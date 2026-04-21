# Endringslogg

Alle merkbare endringer i dette prosjektet dokumenteres her.

Format følger [Keep a Changelog](https://keepachangelog.com/no/1.1.0/).
Versjonering følger [Semantic Versioning](https://semver.org/).

Enumverdier for `komponent`-feltet: `sammendrag`, `dommer_validering`, `rag_gjenfinning`, `rag_generering`.

---

## [Uutgitt]

### Lagt til
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
