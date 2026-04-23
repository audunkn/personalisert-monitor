# Vault-mappestruktur

*Dette dokumentet beskriver de fire mappene i Obsidian-vaulten, flyten mellom dem, og hvilket kodeansvar som gjelder for hver mappe.*

---

## Oversikt

Obsidian-vaulten fungerer som filbasert lagring for artikkeltekst og bilder. Alle innhentingskanaler — RSS, nettside, YouTube og manuell klipping — skriver til samme mappestruktur via felles moduler. Strukturen skiller mellom filer som venter på behandling, filer som er i aktiv bruk, og støttefiler som bilder.

---

## Flytdiagram

```
Obsidian Web Clipper / PDF
        |
        v
  vault/innboks/          <-- manuell inngang (.md og .pdf)
        |
        | obsidian_vakt.py prosesserer
        |
        +---> vault/artikler/          <-- endelig lagringssted (.md)
        |          |
        |          | obsidian_vakt.py overvåker sletting
        |          v
        |     vault/ressurser/bilder/  <-- nedlastede bilder
        |
        +---> vault/behandlet/         <-- innboks-fil etter vellykket lagring
```

RSS, nettside og YouTube går direkte til `artikler/` via `vault_skriver.py` — de passerer ikke `innboks/`.

---

## Beskrivelse per mappe

### `innboks/`

**Formål:** Mottakspunkt for manuelt klippede artikler og PDF-er.

**Hvem skriver:** Brukeren, via Obsidian Web Clipper (.md) eller ved å kopiere en PDF-fil inn i mappen.

**Hvem leser:** `obsidian_vakt.py` — overvåker mappen kontinuerlig med watchdog og prosesserer nye filer automatisk.

**Hva skjer:** Ved ny .md-fil leses YAML-frontmatter, URL-en sjekkes mot `elementer`-tabellen for deduplisering, og artikkelen lagres via `vault_skriver.lagre_artikkel()`. PDF-filer får tekst ekstrahert via pypdf og lagres på samme måte. Duplikater slettes stille. Vellykket behandlet fil flyttes til `behandlet/`.

Manuelt klippede artikler omfattes ikke av datointervall-filtrering — de lagres alltid.

---

### `artikler/`

**Formål:** Primærlagring for alle behandlede artikler, uavhengig av kilde.

**Hvem skriver:** `vault_skriver.lagre_artikkel()` — kalles av alle innhentingskanaler.

**Hvem leser:** Sammendragsmodulen (`sammendrag/lag_sammendrag.py`) og brukeren direkte i Obsidian.

**Hva skjer:** Hver artikkel lagres som én `.md`-fil med YAML-frontmatter og Markdown-kropp. Bilder i innholdet lastes ned og erstattes med lokale stier til `ressurser/bilder/`. En tilsvarende rad skrives til `elementer`-tabellen i SQLite. Mislykket SQLite-skriving utløser sletting av `.md`-filen (rollback).

`obsidian_vakt.py` overvåker også denne mappen for sletting — se avsnittet om opprydding nedenfor.

---

### `behandlet/`

**Formål:** Arkiv for innboks-filer som er fullstendig prosessert.

**Hvem skriver:** `obsidian_vakt.py` — flytter filen hit etter vellykket lagring.

**Hvem leser:** Ingen automatikk. Mappen er tilgjengelig for manuell gjennomgang.

**Hva skjer:** Filen flyttes uendret fra `innboks/` til `behandlet/`. Innholdet er ikke det som lagres i `artikler/` — `vault_skriver.py` bygger en ny fil med standardisert frontmatter og struktur.

---

### `ressurser/bilder/`

**Formål:** Lokal lagring av bilder hentet fra artikler.

**Hvem skriver:** `vault_skriver._behandle_bilder()` — laster ned og lagrer bilder under artikkellagring.

**Hvem leser:** Obsidian — `.md`-filer i `artikler/` refererer til disse bildefilene med relative stier (`../ressurser/bilder/{filnavn}`).

**Hva skjer:** Hvert bilde får et UUID8-filnavn med korrekt filendelse (bestemt av Content-Type-header eller URL-suffix). Bildefilnavnene lagres som JSON i `bilder_json`-feltet i `elementer`-tabellen, slik at opprydding kan identifisere hvilke filer som tilhører en gitt artikkel.

---

## Filnavn og identifikatorer

### Artikkelfiler (`artikler/`)

```
{uuid8}-{slug}.md
```

- **`uuid8`** — de første 8 tegnene av artikkelen sin UUID4 (heksadesimal, uten bindestreker). Eksempel: `3f8a1c2b`.
- **`slug`** — NFKD-normalisert, ASCII-konvertert, lowercase tittel med bindestreker. Norske tegn mappes til nærmeste ASCII-ekvivalent der det er mulig. Eksempel: `ai-act-oppdatering-april`.

Eksempel på komplett filnavn: `3f8a1c2b-ai-act-oppdatering-april.md`

### YAML-frontmatter

Alle artikkelfiler starter med følgende frontmatter:

```yaml
---
element_id: <full UUID4>
url: <kilde-URL>
kildetype: <rss | manuell | pdf | nett | youtube>
klippet_dato: <ISO-dato>   # kun for manuelt klippede artikler
publisert: <ISO-dato>      # utelates hvis ukjent
---
```

`element_id` er primærnøkkelen som kobler filen til raden i `elementer`-tabellen.

### Bildefiler (`ressurser/bilder/`)

```
{uuid8}.{ext}
```

Filendelse bestemmes av Content-Type-responsen (`jpg`, `png`, `gif`, `webp`, `svg`). Filer med ukjent type får endelsen `bin`.

---

## Opprydding ved sletting

Når en `.md`-fil slettes fra `artikler/` — enten manuelt i Obsidian eller via et annet verktøy — rydder `obsidian_vakt.py` automatisk opp:

1. Finn raden i `elementer` WHERE `vault_sti` matcher den slettede filen.
2. Les `bilder_json`-feltet og slett hver tilhørende bildefil fra `ressurser/bilder/`.
3. Slett raden fra `elementer`.

Filer i `behandlet/` påvirkes ikke av sletting i `artikler/`.

---

## Kodeansvar

| Modul | Mappe(r) |
|---|---|
| `innhenter/vault_skriver.py` | Skriver til `artikler/` og `ressurser/bilder/` |
| `innhenter/obsidian_vakt.py` | Leser fra `innboks/`, skriver til `behandlet/`, overvåker `artikler/` for sletting |
| `db/init.py` | Oppretter ikke vault-mapper — dette gjøres av `vault_skriver.py` og `obsidian_vakt.py` ved oppstart |

Alle innhentingskanaler (RSS, nett, YouTube) kaller `vault_skriver.lagre_artikkel()` og har dermed ingen direkte kunnskap om mappestrukturen.
