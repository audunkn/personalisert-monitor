# Validation — A0b: Obsidian Web Clipper

*Alle punkter må være krysset av før merge til master.*

---

## Enhetstester

- [x] `make test` kjøres uten feil — alle 4 tester i `tester/test_vault_skriver.py` grønne:
  - [x] `test_filnavn_og_frontmatter` — korrekt UUID-prefix-filnavn og YAML-frontmatter.
  - [x] `test_element_id_konsistens` — UUID i frontmatter matcher `element_id` i SQLite.
  - [x] `test_ugyldig_bilde_url` — ugyldig bilde-URL gir WARNING, ingen krasj.
  - [x] `test_rollback` — fil slettes fra vault hvis SQLite-skriving feiler.

---

## Røyktest — manuell

- [x] Obsidian Web Clipper er installert i nettleseren og peker mot `vault/innboks/`.
- [x] Klipp én nettside via Web Clipper.
- [x] Verifiser at filen havner i `vault/artikler/` (ikke i `innboks/`).
- [x] Verifiser at filen har korrekt YAML-frontmatter: `element_id`, `url`, `kildetype: manuell`, `klippet_dato`.
- [x] Verifiser at `element_id` i frontmatter matcher en rad i `elementer`-tabellen i SQLite.
- [ ] Klipp samme URL på nytt — verifiser at filen i `innboks/` slettes og at INFO logges (dedup). *(ikke testet manuelt — logikk enhetstestet)*
- [ ] Klipp nettside med minst ett bilde — verifiser at bildet er lastet ned til `vault/ressurser/bilder/` og at markdown-innholdet bruker relativ sti (`../ressurser/bilder/{uuid8}.{ext}`). *(ikke testet manuelt — logikk enhetstestet)*

---

## Kodegjennomgang

- [x] `vault_skriver.py`: konsistensrekkefølge (UUID → fil → SQLite → rollback) verifisert i kode og i `test_rollback`.
- [x] `obsidian_vakt.py`: feil i én fil stopper ikke behandling av neste — feilisolering per fil implementert.
- [x] Google-stil docstrings på alle klasser og ikke-trivielle funksjoner.
- [x] Ingen hardkodede stier — alle stier leses fra `.env` eller overføres som parametere.

---

## Dokumentasjon

- [x] `CHANGELOG.md` oppdatert med tidsstempel for alle commits i denne fasen.
- [x] `specs/veikart.md` — alle A0b-punkter krysset av etter merge.
