# Validation: Bugfiks — vakt prosesserer eksisterende innboks-filer ved oppstart

## Merge-kriterier

- [x] `pytest tester/test_obsidian_vakt_oppstart.py -v` — 2 tester grønne
- [x] Pre-eksisterende `.md`-fil i `innboks/` prosesseres ved oppstart — rad i SQLite, fil i `behandlet/`
- [x] Duplikat-URL hoppes over ved restart — ingen ekstra rad i `elementer`
- [x] CHANGELOG oppdatert med tidsstempel
- [x] `specs/veikart.md` oppdatert
- [x] Issue #7 lukket på GitHub
