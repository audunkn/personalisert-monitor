# Plan: Automatisk opprydning ved sletting av artikkel

## Mål

Når en `.md`-fil slettes fra `vault/artikler/`, skal tilhørende bilder og SQLite-rad fjernes automatisk av bakgrunnsvakten.

## Implementeringsgrupper

- [x] **Gruppe 1 — DB**: Legg til `bilder_json TEXT`-kolonne i `elementer`-tabellen. Idempotent migrering i `db/init.py`.
- [x] **Gruppe 2 — vault_skriver.py**: `_behandle_bilder()` returnerer `(innhold, bildefilnavn_liste)`. `lagre_artikkel()` lagrer listen som JSON i `bilder_json`. `_skriv_til_db()` tar ny `bilder_json`-parameter.
- [x] **Gruppe 3 — obsidian_vakt.py**: Ny `_ArtikkelHandler` med `on_deleted` for `.md`-filer i `vault/artikler/`. Hjelpefunksjon `_rydd_etter_slettet_artikkel()` sletter bilder og DB-rad. Observer overvåker nå både `innboks/` og `artikler/`.
- [x] **Gruppe 4 — Tester**: 4 enhetstester i `tester/test_artikkel_sletting.py`. Alle grønne.
