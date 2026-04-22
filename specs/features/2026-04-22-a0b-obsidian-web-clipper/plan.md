# Plan — A0b: Obsidian Web Clipper

*Referanse: `specs/veikart.md` § A0b. Denne planen bygger på fundamentet fra A0 og legger til manuell innhentingskanal via Obsidian Web Clipper. Makefile-target: ingen nytt target — `innhent` dekker automatisk innhenting, Web Clipper er manuelt trigget. Testfil: `tester/test_vault_skriver.py`.*

---

## Rekkefølge

Gruppe 1 → 2 → 3 → 4. Gruppe 3 forutsetter ferdig gruppe 2 (vault_skriver.py må eksistere før vakt-modulen kan kalle den). Gruppe 4 kan startes parallelt med gruppe 3.

---

## Gruppe 1 — Web Clipper-installasjon og konfigurasjon

Obsidian Web Clipper er nettleserutvidelsen som gjør det mulig å klippe artikler med ett klikk og sende dem direkte til vaulten. Denne gruppen installerer og konfigurerer utvidelsen slik at klippede artikler havner i riktig mappe med korrekt YAML-frontmatter — klar til å plukkes opp av vakt-modulen i gruppe 3.

- [ ] Installer Obsidian Web Clipper-utvidelse i nettleser.
- [ ] Konfigurer utvidelsen til å skrive til `vault/innboks/` med følgende YAML-frontmatter-felt: `url`, `klippet_dato`, `kildetype: manuell`.
- [ ] Verifiser at ett manuelt klipp produserer en `.md`-fil i `vault/innboks/` med korrekt frontmatter.

---

## Gruppe 2 — vault_skriver.py

Vault-skriveren er hjerte i innhentingslaget — den ene modulen som har ansvar for å atomisk lagre en artikkel til vault og SQLite. Konsistensrekkefølgen sikrer at databasen aldri peker til en fil som ikke finnes, og at ingen fil eksisterer uten en tilhørende SQLite-rad. Denne modulen brukes av alle innhentingskanaler (RSS, nett, YouTube og manuell klipping).

- [ ] Skriv `src/intelligence_monitor/innhenter/vault_skriver.py` med følgende konsistensrekkefølge:
  1. Generer UUID lokalt som `element_id`.
  2. Bygg filnavn: `{uuid_kort}-{tittel-slug}.md` (f.eks. `a3f7c2d1-tittel-pa-artikkelen.md`).
  3. Skriv Markdown-fil med `element_id` i YAML-frontmatter til `vault/artikler/`.
  4. Skriv rad til `elementer`-tabellen i SQLite med samme `element_id` og `vault_sti`.
  5. Ved feil i steg 4: slett filen fra steg 3 (rollback).
- [ ] YAML-frontmatter som minimum: `element_id`, `url`, `tittel`, `kilde_id`, `publisert`, `kildetype`, `klippet_dato` (kun for `kildetype: manuell`).
- [ ] Bilder: last ned og lagre i `vault/ressurser/bilder/` — ugyldig bilde-URL logges som WARNING og hoppes over uten krasj.
- [ ] Legg til Google-stil docstring og relevante inline-kommentarer.

---

## Gruppe 3 — obsidian_vakt.py

Vakt-modulen er broen mellom manuell klipping og resten av systemet. Den overvåker `vault/innboks/` kontinuerlig og prosesserer nye filer umiddelbart — uten at brukeren trenger å gjøre noe utover selve klippet. Manuelt klippede artikler er alltid innenfor datointervallet og lagres uten dato-sjekk.

- [ ] Skriv `src/intelligence_monitor/innhenter/obsidian_vakt.py` med `watchdog`-biblioteket.
- [ ] Overvåk `vault/innboks/` for nye `.md`-filer (hendelse: `on_created`).
- [ ] Per ny fil:
  1. Les YAML-frontmatter fra filen.
  2. Sjekk `url` mot `elementer`-tabellen — finnes URL fra før: slett innboks-filen og logg INFO.
  3. Ny URL: kall `vault_skriver.py` med innholdet fra filen, flytt prosessert fil til `vault/behandlet/`.
- [ ] Manuelt klippede artikler (`kildetype: manuell`) får ingen datointervall-sjekk — de lagres alltid.
- [ ] Feil i én fil stopper ikke behandling av neste.
- [ ] Legg til Google-stil docstring og relevante inline-kommentarer.

---

## Gruppe 4 — Enhetstester

Enhetstestene verifiserer at vault_skriver.py oppfører seg korrekt i grensetilfeller — uten å avhenge av ekstern infrastruktur. Alle tester bruker midlertidige mapper og mocket SQLite slik at de kjøres raskt og deterministisk.

- [ ] `tester/test_vault_skriver.py` — fire tester:
  - `test_filnavn_og_frontmatter`: korrekt filnavn (UUID-prefix + slug), korrekt YAML-frontmatter i midlertidig testmappe.
  - `test_element_id_konsistens`: UUID i frontmatter matcher `element_id` i SQLite-raden.
  - `test_ugyldig_bilde_url`: ugyldig bilde-URL håndteres uten krasj — WARNING logges.
  - `test_rollback`: fil slettes fra vault hvis SQLite-skriving feiler (simulert med mock).
- [ ] Fixtures i `tester/konfig/fixtures.py`: midlertidig vault-mappe, midlertidig SQLite med korrekt skjema.
- [ ] Kjør `make test` — alle fire tester grønne.
