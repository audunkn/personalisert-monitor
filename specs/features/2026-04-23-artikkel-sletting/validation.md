# Validering: Automatisk opprydning ved sletting av artikkel

## Sjekkliste

- [x] `make test` passerer — 20 tester grønne etter implementering
- [x] CHANGELOG oppdatert med tidsstempel `*(2026-04-23 18:00)*`
- [x] Manuell røyktest: importer artikkel med bilder via Web Clipper → start `obsidian_vakt.py` → slett `.md`-filen i Obsidian (med System Recycle Bin som slettemål) → verifiser at bildefiler er slettet fra `vault/ressurser/bilder/` og at DB-raden er borte

## Merknader

Den manuelle røyktesten krever et kjørende Obsidian-oppsett med bilder og kan ikke automatiseres. Forutsetning: Obsidian er konfigurert med `Settings → Files and links → Deleted files → System Recycle Bin`.
