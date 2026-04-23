# Requirements: A1 — RSS-innhenting med datointervall

**Referanser**: `specs/visjon.md § Kildetyper, § Lagringsfilosofi`; `specs/teknologi.md § Datointervall for innhenting, § Filskriving og datakonsistens`

## I scope
- `innhenter/rss.py` — RSS/Atom-innhenting med `feedparser`
- `innhenter/kjører.py` — minimal shell (RSS-only, TODO for A4)
- `db/skjema.sql` og `db/init.py` — utvidet med feilfelt på `kilder`
- Enhetstester (`test_rss.py`)
- Røyktest mot tre RSS-startkilder

## Utenfor scope
- Substack og nettsider — A4
- YouTube — A6
- Full koordinator med varsling og gjenforsøkslogikk — A4
- Element-nivå dead-letter — A4

## Beslutninger

**Feilhåndtering (kilde-nivå):** Utilgjengelig feed → log `ERROR` + oppdater `sist_feil_tidsstempel`/`sist_feil_melding` i `kilder`. Nullstilles ved vellykket henting.

**Skjemaendring:** To nye nullable felter på `kilder`: `sist_feil_tidsstempel TEXT` og `sist_feil_melding TEXT`. `db/init.py` håndterer dette idempotent.

**Minimal kjører.py:** Inneholder én linje funksjonskall og en TODO-kommentar.

**feedparser:** Synkron. `bozo = True` → håndteres som feil med ERROR-logging.

**Dato-parsing:** `feedparser` returnerer `entry.published_parsed` som `time.struct_time`. Konverter til `datetime` for sammenligning med `hent_fra`/`hent_til`.

**Env-override:** Hvis `HENT_FRA` satt i `.env`, overstyres per-kilde `hent_fra` for alle kilder.
