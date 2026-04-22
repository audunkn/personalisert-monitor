# Requirements — A0b: Obsidian Web Clipper

*Referanser: `specs/visjon.md` § Kildetyper, § Lagringsfilosofi; `specs/teknologi.md` § Filskriving og datakonsistens, § Datointervall for innhenting.*

---

## Scope

### I scope
- Obsidian Web Clipper installert og konfigurert mot `vault/innboks/`.
- `vault_skriver.py` — atomisk lagring til vault og SQLite med rollback.
- `obsidian_vakt.py` — `watchdog`-basert vakt på `vault/innboks/`.
- Enhetstester for `vault_skriver.py` (4 tester).
- Røyktest: 1 manuelt klipp verifisert i vault og SQLite.

### Utenfor scope
- Automatisk innhenting (RSS, nett, YouTube) — implementeres i A1, A4, A6.
- Sammendragsgenerering — implementeres i A2a.
- Samtalebasert innhenting (f.eks. API-inngang) — ikke planlagt i gjeldende versjon.

---

## Beslutninger og begrunnelser

### Filnavnkonvensjon: UUID-prefix + tittel-slug
`vault_skriver.py` navngir filer som `{uuid_kort}-{tittel-slug}.md`, f.eks. `a3f7c2d1-tittel-pa-artikkelen.md`.

**Begrunnelse:** UUID-prefixet gjør filnavnet globalt unikt og kobler filen direkte til `element_id` i YAML-frontmatter uten ekstra oppslag. Tittel-sluggen beholder lesbarhet i Obsidian-navigatoren. `uuid_kort` = de første 8 tegnene av UUID4, nok til å unngå kollisjoner i praksis.

### Dedup-håndtering: hopp over stille
Hvis `obsidian_vakt.py` oppdager en fil i `innboks/` med en URL som allerede finnes i `elementer`-tabellen, slettes innboks-filen og hendelsen logges som INFO.

**Begrunnelse:** Konsistent med innhentingslogikken i `rss.py` og `nett.py` (jf. `specs/teknologi.md` § Datointervall for innhenting, steg 4). Manuell klipping kan skje ved uhell — stillhet er bedre enn feilmelding for et duplikat som ikke er et problem.

### Ingen datointervall-sjekk for manuell klipping
Manuelt klippede artikler (`kildetype: manuell`) lagres alltid, uavhengig av `hent_fra`/`hent_til` per kilde.

**Begrunnelse:** Brukeren har tatt et aktivt valg ved å klippe artikkelen. Å filtrere bort denne artikkelen basert på publiseringsdato ville motarbeide intensjonen. Jf. `specs/veikart.md` § A0b: "Manuelt klippede artikler får ingen datointervall-sjekk — de lagres alltid."

### obsidian_vakt.py er en foreldre-prosess, ikke en systemtjeneste
`obsidian_vakt.py` kjøres manuelt (f.eks. i en dedikert terminal) og avhenger ikke av systemd, cron eller Windows-tjenester.

**Begrunnelse:** Fase A kjøres manuelt via Makefile. Automatisering (cron, Docker) er fase D-leverabel.

### vault_skriver.py er et delt datalag
Samme modul brukes av alle innhentingskanaler (RSS, nett, YouTube, manuell). Den er ikke bundet til `kildetype: manuell`.

**Begrunnelse:** Én enkelt modul med ansvar for atomic vault+SQLite-skriving reduserer risikoen for inkonsistens på tvers av kanaler. Jf. `specs/visjon.md` § Lagringsfilosofi og `specs/teknologi.md` § Filskriving og datakonsistens.

---

## Kontekst og avhengigheter

| Avhengighet | Status |
|---|---|
| `vault/innboks/`, `vault/artikler/`, `vault/ressurser/bilder/`, `vault/behandlet/` | Opprettet i A0 |
| `db/skjema.sql` og `db/init.py` (`elementer`-tabellen) | Opprettet i A0 |
| `watchdog`-pakken | Deklarert i `pyproject.toml` (fase A-avhengigheter) |
| `konfig/kilder.yaml` med `kilde_id` for manuell kanal | Krever at en kilde med `type: manuell` finnes — legges til som del av denne fasen |

---

## Åpne spørsmål

*Ingen — alle beslutninger er avklart.*
