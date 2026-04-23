# Krav: Automatisk opprydning ved sletting av artikkel

## Problem

Når en `.md`-artikkel slettes direkte fra `vault/artikler/` i Obsidian, etterlater den seg to ressurser som ikke lenger er i bruk: nedlastede bildefiler i `vault/ressurser/bilder/` og en rad i SQLite-databasen. Disse akkumulerer over tid og er umulige å rydde opp manuelt uten å kjøre mot databasen.

## Løsning

En watchdog-observer overvåker `vault/artikler/` i tillegg til `vault/innboks/`. Når en `.md`-fil slettes, slås `bilder_json`-kolonnen i `elementer`-tabellen opp for å finne tilhørende bildefiler. Bildene slettes fra disk, deretter slettes DB-raden.

Lagringsrekkefølge ved opprettelse: UUID → fil → SQLite (inkl. `bilder_json`) → rollback ved feil. Opprydningsrekkefølge ved sletting: bilder → DB-rad.

## Ut av scope

`on_moved`-hendelsen (Obsidian "Vault trash"-funksjon) dekkes ikke. Obsidian sin innebygde papirkurv-funksjon genererer en `on_moved`-hendelse, ikke `on_deleted`, og er kompleks å håndtere konsistent på tvers av plattformer.

**Anbefalt Obsidian-innstilling:** `Settings → Files and links → Deleted files → System Recycle Bin`. Da utløses `on_deleted` og opprydningen fungerer som forventet.

## Avhengigheter

- `watchdog` — allerede installert (A0b)
- `bilder_json`-kolonne i `elementer` — legges til i denne featuren
