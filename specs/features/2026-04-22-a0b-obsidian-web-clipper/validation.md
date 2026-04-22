# Validation — A0b: Obsidian Web Clipper

*Alle punkter må være krysset av før merge til master.*

---

## Enhetstester

- [ ] `make test` kjøres uten feil — alle 4 tester i `tester/test_vault_skriver.py` grønne:
  - [ ] `test_filnavn_og_frontmatter` — korrekt UUID-prefix-filnavn og YAML-frontmatter.
  - [ ] `test_element_id_konsistens` — UUID i frontmatter matcher `element_id` i SQLite.
  - [ ] `test_ugyldig_bilde_url` — ugyldig bilde-URL gir WARNING, ingen krasj.
  - [ ] `test_rollback` — fil slettes fra vault hvis SQLite-skriving feiler.

---

## Røyktest — manuell

- [ ] Obsidian Web Clipper er installert i nettleseren og peker mot `vault/innboks/`.
- [ ] Klipp én nettside via Web Clipper.
- [ ] Verifiser at filen havner i `vault/artikler/` (ikke i `innboks/`).
- [ ] Verifiser at filen har korrekt YAML-frontmatter: `element_id`, `url`, `kildetype: manuell`, `klippet_dato`.
- [ ] Verifiser at `element_id` i frontmatter matcher en rad i `elementer`-tabellen i SQLite.
- [ ] Klipp samme URL på nytt — verifiser at filen i `innboks/` slettes og at INFO logges (dedup).
- [ ] Klipp nettside med minst ett bilde — verifiser at bildet er lastet ned til `vault/ressurser/bilder/` og at markdown-innholdet bruker relativ sti (`../ressurser/bilder/{uuid8}.{ext}`).

---

## Kodegjennomgang

- [ ] `vault_skriver.py`: konsistensrekkefølge (UUID → fil → SQLite → rollback) verifisert i kode og i `test_rollback`.
- [ ] `obsidian_vakt.py`: feil i én fil stopper ikke behandling av neste — verifisert manuelt eller med test.
- [ ] Google-stil docstrings på alle klasser og ikke-trivielle funksjoner.
- [ ] Ingen hardkodede stier — alle stier leses fra `.env` eller overføres som parametere.

---

## Dokumentasjon

- [ ] `CHANGELOG.md` oppdatert med tidsstempel for alle commits i denne fasen.
- [ ] `specs/veikart.md` — alle A0b-punkter krysset av etter merge.
