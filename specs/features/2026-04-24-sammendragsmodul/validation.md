# A2a — Valideringskriterier

*Alle punkter må være krysset av før merge til master.*

---

## Enhetstester

- [ ] `tester/test_lag_sammendrag.py` — alle 5 tester grønne ved `make test`.
- [ ] Ingen regresjoner i eksisterende testsuite.

---

## Røyktest — 3 artikler

- [ ] `make sammendrag` kjører uten feil mot 3 innhentede artikler.
- [ ] Alle 3 sammendrag lagret i `sammendrag`-tabellen med korrekt `element_id`.
- [ ] `prompt_versjon` er `v1` i alle rader.
- [ ] Regulatorisk koblingsparagraf er til stede i hvert sammendrag.
- [ ] Spor synlig i Opik UI for alle 3 kall.

---

## Git

- [ ] Git-tag `prompt-v1` satt på commit som introduserer `v1.txt`.
- [ ] CHANGELOG.md oppdatert ved alle commits i fasen.

---

## Kode

- [ ] Alle nye funksjoner og klasser har Google-stil docstring — jf. `teknologi.md`.
- [ ] `.env.mal` oppdatert med `CLAUDE_MODELL`, `MAKS_SAMMENDRAG_TOKENS` og `TEMPERATURE`.
