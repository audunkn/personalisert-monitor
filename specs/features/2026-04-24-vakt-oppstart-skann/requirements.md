# Requirements: Bugfiks — vakt prosesserer eksisterende innboks-filer ved oppstart

## Bakgrunn

`obsidian_vakt.py` bruker watchdog til å overvåke `vault/innboks/` for nye filer.
Watchdog reagerer kun på `on_created`-hendelser etter at Observer er startet —
filer som allerede lå i innboksen da vakten ble startet, ignoreres helt.

## Krav

**R1** — Ved oppstart skal `start()` prosessere alle `.md`- og `.pdf`-filer
som allerede ligger i `innboks/`, i alfabetisk rekkefølge.

**R2** — Eksisterende dedupliseringslogikk (`_url_finnes()`) skal håndtere
filer som er prosessert i en tidligere kjøring — ingen ny guard er nødvendig.

**R3** — Oppstartsskanningen skjer etter at kataloger er opprettet men før
Observer startes, slik at watchdog ikke sender dobbel hendelse for de samme filene.

## Avgrensninger

- OCR støttes ikke (arvet fra A0c).
- Bare `.md` og `.pdf` prosesseres — andre filtyper ignoreres stille.
