# Validation: A1 — RSS-innhenting med datointervall

## Enhetstester (obligatorisk)
- [ ] `make test` returnerer exit code 0
- [ ] Alle 6 tester i `test_rss.py` grønne
- [ ] Eksisterende tester (`test_db_init.py`, `test_vault_skriver.py`) fortsatt grønne etter skjemaendring

## Røyktest — manuell (obligatorisk)
- [ ] `HENT_FRA` satt til 7 dager tilbake, `HENT_TIL` tom
- [ ] `make innhent` kjøres mot Simon Willison, Anthropic-bloggen og LangChain-bloggen
- [ ] Minst én artikkel per kilde havner i `vault/artikler/` med korrekt YAML-frontmatter
- [ ] `element_id` i frontmatter matcher rad i `elementer`-tabellen
- [ ] Kjør `make innhent` på nytt — ingen duplikater legges til

## Feilhåndtering — manuell (anbefalt)
- [ ] Test én kilde med ugyldig URL — ERROR logges, øvrige kilder fortsetter
- [ ] Verifiser `sist_feil_tidsstempel` satt i `kilder`-tabellen for feilede kilde

## Kode (obligatorisk)
- [ ] `rss.py` og `kjører.py` har Google-stil docstrings
- [ ] Ingen hardkodede stier eller API-nøkler
- [ ] `CHANGELOG.md` oppdatert med tidsstempel
