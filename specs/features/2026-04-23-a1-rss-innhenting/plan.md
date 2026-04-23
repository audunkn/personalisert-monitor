# Plan: A1 — RSS-innhenting med datointervall

## Gruppe 1 — Skjemaoppdatering og rss.py

- [ ] Legg til `sist_feil_tidsstempel TEXT` og `sist_feil_melding TEXT` på `kilder`-tabellen i `db/skjema.sql`
- [ ] Oppdater `db/init.py` idempotent (ALTER TABLE-mønster for nye felt)
- [ ] Skriv `src/intelligence_monitor/innhenter/rss.py` med full innhentingslogikk

## Gruppe 2 — Kjører-shell og røyktest

- [ ] Skriv `src/intelligence_monitor/innhenter/kjører.py` (minimal shell)
- [ ] Verifiser `make innhent` kjører uten feil
- [ ] Røyktest: `HENT_FRA` satt til 7 dager tilbake mot Simon Willison, Anthropic og LangChain

## Gruppe 3 — Enhetstester

- [ ] Skriv `tester/test_rss.py` med 6 enhetstester
- [ ] `make test` — alle grønne
