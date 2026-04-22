# A0 — Fundament: Valideringskriterier

Alle punkter under **Obligatorisk** må være krysset av før merge til `main`.

---

## Obligatorisk: Enhetstester

- [x] `tester/test_db_init.py` — idempotens: kjør `init.py` to ganger mot midlertidig SQLite-fil, verifiser at alle fire tabeller finnes og ingen rader er slettet
- [x] `tester/test_db_init.py` — YAML→SQLite-synk: ny kilde med `hent_fra` dukker opp korrekt; fjernet kilde merkes `aktiv = false`
- [x] `make test` returnerer exit code 0 (alle tester grønne)

---

## Obligatorisk: Røyktester

- [ ] `uv pip install -e ".[dev]"` kjører uten feil i friskt miljø
- [ ] `python -m intelligence_monitor.db.init` oppretter databasen uten feil
- [ ] Kjør `python -m intelligence_monitor.db.init` på nytt — ingen feil, ingen data slettet (idempotens manuelt verifisert)
- [ ] `konfig/kilder.yaml` med fem startkilder synkroniserer korrekt: alle fem kilders rader finnes i `kilder`-tabellen med riktig `hent_fra`

---

## Obligatorisk: Struktur

- [ ] `src/intelligence_monitor/` eksisterer med `__init__.py` i rotmappen og alle undermapper
- [ ] `Makefile` har alle targets: `innhent`, `sammendrag`, `review`, `synk`, `regresjon`, `test`, `test-enkelt`, `rapport`, `alle`, `produksjon`
- [ ] `.env.mal` inneholder alle felter fra `specs/teknologi.md` → Miljøvariabler, inkl. `DATABASE_STI=data/monitor.db`
- [ ] `.env` er i `.gitignore` og ikke committet
- [ ] `specs/regulatorisk-kontekst.md` eksisterer med innhold om AI Act, NIS2, ISO 42001, Datatilsynet og NSM grunnprinsipper

---

## Anbefalt: Manuell gjennomgang

- [ ] Les gjennom `db/skjema.sql` og verifiser at alle fire fase A-tabeller har feltene fra `specs/teknologi.md` → Databasetabeller
- [ ] Les gjennom `specs/regulatorisk-kontekst.md` og vurder om innholdet er presist nok til å inngå i summarizer-prompten

---

## Ikke krav for merge

- Opik-konto verifisert (kan gjøres i A2c)
- Vault-sti konfigurert i `.env` (settes av bruker lokalt)
