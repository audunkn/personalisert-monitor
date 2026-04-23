# Plan: A1 — RSS-innhenting med datointervall

## Gruppe 1 — Skjemaoppdatering og rss.py

- [x] Legg til `sist_feil_tidsstempel TEXT` og `sist_feil_melding TEXT` på `kilder`-tabellen i `db/skjema.sql`
- [x] Oppdater `db/init.py` idempotent (ALTER TABLE-mønster for nye felt)
- [x] Skriv `src/intelligence_monitor/innhenter/rss.py` med full innhentingslogikk

## Gruppe 2 — Kjører-shell og røyktest

- [x] Skriv `src/intelligence_monitor/innhenter/kjører.py` (minimal shell)
- [x] Verifiser `make innhent` kjører uten feil
- [x] Røyktest: `HENT_FRA` satt til 7 dager tilbake mot Simon Willison, HuggingFace og LangChain

## Gruppe 3 — Enhetstester

- [x] Skriv `tester/test_rss.py` med 6 enhetstester
- [x] `pytest tester/ -v` — alle 12 grønne (6 nye + 6 eksisterende)
