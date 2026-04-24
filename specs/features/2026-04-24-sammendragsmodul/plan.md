# A2a — Sammendragsmodul med regulatorisk kontekst

*En commit per gruppe. Kryss av etter commit og oppdater `specs/veikart.md` etter fullført gruppe.*

---

## Gruppe 1 — Baseline-prompt og Git-tag

Prompts er versjonerte tekstfiler — dette gjør det mulig å spore nøyaktig hvilken instruksjon som produserte et gitt sammendrag, og sammenligne versjoner mot hverandre. Gruppe 1 etablerer versjon 1 av prompten og tagger den i Git slik at regresjonstesting alltid kan peke tilbake til et kjent utgangspunkt.

- [ ] Opprett `src/intelligence_monitor/sammendrag/prompts/v1.txt` med instruksjon om norskspråklig sammendrag og regulatorisk koblingsparagraf basert på `specs/regulatorisk-kontekst.md`.
- [ ] Tag commit med `prompt-v1`.
- [ ] Oppdater `CHANGELOG.md`.

---

## Gruppe 2 — lag_sammendrag.py

Kjernemodulen leser en artikkels vault-fil, kombinerer innholdet med regulatorisk kontekst og prompt, kaller OpenAI API og lagrer resultatet i SQLite. Alle API-kall spores via Opik slik at hvert sammendrag er sporbart til nøyaktig hvilken prompt-versjon og hvilke input-tokens som ble brukt.

- [ ] Opprett `src/intelligence_monitor/sammendrag/__init__.py` (tom).
- [ ] Skriv `src/intelligence_monitor/sammendrag/lag_sammendrag.py`:
  - Les aktiv prompt fra `sammendrag/prompts/v1.txt`.
  - Les artikkeltekst fra vault-fil via `vault_sti` i `elementer`-tabellen.
  - Les hele `specs/regulatorisk-kontekst.md` og inkluder som kontekst i prompten.
  - Kutt artikkeltekst til `MAKS_ARTIKKEL_TOKENS` (fra `.env`) før innramming.
  - Pakk artikkelteksten i XML-tagger (`<artikkel>…</artikkel>`).
  - Kall OpenAI API med modell, temperature og maks tokens fra `.env`; dekor med `@opik.track`.
  - Lagre sammendrag i `sammendrag`-tabellen med `element_id` og `prompt_versjon`.
- [ ] Oppdater `CHANGELOG.md`.

---

## Gruppe 3 — Makefile-integrasjon

`make sammendrag` er inngangspunktet for daglig bruk. Gruppen sikrer at modulen er kjørbar fra Makefile-targeten definert i A0 og bekrefter integrasjonen med en manuell røyktest mot tre virkelige artikler.

- [ ] Verifiser at `Makefile`-targeten `sammendrag` kaller `lag_sammendrag.py` korrekt.
- [ ] Røyktest: kjør `make sammendrag` mot 3 innhentede artikler. Verifiser:
  - Sammendrag lagret i `sammendrag`-tabellen med korrekt `element_id` og `prompt_versjon`.
  - Regulatorisk koblingsparagraf til stede i sammendraget.
  - Spor synlig i Opik UI.
- [ ] Oppdater `CHANGELOG.md`.

---

## Gruppe 4 — Enhetstester

Testene dekker de kritiske grensetilfellene: korrekt XML-innramming, at lange artikler kuttes riktig, at prompt-versjon lagres, at regulatorisk kontekst er til stede i API-kallet, og at manglende vault-fil gir en meningsfull feilmelding i stedet for et krasj.

- [ ] Skriv `tester/test_lag_sammendrag.py`:
  - XML-innramming korrekt formatert.
  - Tekst over `MAKS_ARTIKKEL_TOKENS` kuttes riktig.
  - `prompt_versjon` lagres korrekt i SQLite.
  - `regulatorisk-kontekst.md` inkluderes i prompten som sendes til API.
  - Manglende vault-fil gir meningsfull feilmelding.
- [ ] Kjør `make test` — alle tester grønne.
- [ ] Oppdater `CHANGELOG.md`.
