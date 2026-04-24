# A2a — Valideringskriterier

*Alle punkter må være krysset av før merge til master.*

---

## Enhetstester

- [x] `tester/test_lag_sammendrag.py` — alle 6 tester grønne ved `make test`.
- [x] Ingen regresjoner i eksisterende testsuite.

---

## Røyktest — 3 artikler

- [x] `make sammendrag` kjører uten feil mot 3 innhentede artikler.
- [x] Alle 3 sammendrag lagret i `sammendrag`-tabellen med korrekt `element_id`.
- [x] `prompt_versjon` er `v1` i alle rader.
- [x] Regulatorisk koblingsparagraf er til stede i hvert sammendrag.
- [x] Spor synlig i Opik UI for alle 3 kall.

---

## Git

- [x] Git-tag `prompt-v1` satt på commit som introduserer `v1.txt`.
- [x] CHANGELOG.md oppdatert ved alle commits i fasen.

---

## Kode

- [x] Alle nye funksjoner og klasser har Google-stil docstring — jf. `teknologi.md`.
- [x] `.env.mal` oppdatert med `OPENAI_MODELL`, `MAKS_SAMMENDRAG_TOKENS` og `TEMPERATURE`.
