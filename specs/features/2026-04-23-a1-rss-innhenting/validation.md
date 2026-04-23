# Validation: A1 — RSS-innhenting med datointervall

## Enhetstester (obligatorisk)
- [x] `pytest tester/ -v` returnerer exit code 0
- [x] Alle 6 tester i `test_rss.py` grønne
- [x] Eksisterende tester (`test_db_init.py`, `test_vault_skriver.py`) fortsatt grønne etter skjemaendring

## Røyktest — manuell (obligatorisk)
- [x] `HENT_FRA=2026-04-16` (7 dager tilbake), `HENT_TIL` tom
- [x] Kjørt mot Simon Willison, HuggingFace og LangChain (Anthropic RSS 404 — erstattet)
- [x] Minst én artikkel per kilde i vault/artikler/ med korrekt YAML-frontmatter
- [x] `element_id` i frontmatter matcher rad i `elementer`-tabellen
- [x] Andre kjøring returnerer 0 nye artikler (idempotens bekreftet)

## Feilhåndtering — manuell (anbefalt)
- [ ] Test én kilde med ugyldig URL — ERROR logges, øvrige kilder fortsetter
- [ ] Verifiser `sist_feil_tidsstempel` satt i `kilder`-tabellen for feilede kilde

## Kode (obligatorisk)
- [x] `rss.py` og `kjører.py` har Google-stil docstrings
- [x] Ingen hardkodede stier eller API-nøkler
- [x] `CHANGELOG.md` oppdatert med tidsstempel
