# Plan: Bugfiks — vakt prosesserer eksisterende innboks-filer ved oppstart (issue #7)

## Gruppe 1: Kodeendring

- [x] Legg til oppstartsskanning i `start()` etter at kataloger er opprettet og
  før `observer.start()` — itererer over `sorted(innboks.iterdir())` og kaller
  `_prosesser()` for `.md` og `_prosesser_pdf()` for `.pdf`

## Gruppe 2: Tester

- [x] Opprett `tester/test_obsidian_vakt_oppstart.py`
- [x] `test_oppstart_prosesserer_eksisterende_md` — pre-eksisterende fil prosesseres
- [x] `test_oppstart_dedup_hopper_over_kjent_url` — kjent URL hoppes over ved restart
- [x] Kjør tester — begge grønne

## Gruppe 3: Dokumentasjon

- [x] CHANGELOG oppdatert med tidsstempel
- [x] Feature-mappe opprettet
- [x] `specs/veikart.md` oppdatert
