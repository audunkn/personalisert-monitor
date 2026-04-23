# Validation: PDF-støtte via vault innboks

## Merge-kriterier

- [ ] `make test` passerer (alle eksisterende + 4 nye tester grønne)
- [ ] Manuell røyktest: PDF dropped i innboks → .md i vault, rad i SQLite, PDF i behandlet/
- [ ] Duplikat PDF → INFO-logg, ingen ny rad, fil slettes
- [ ] Skannet PDF (ingen tekst) → WARNING-logg, filen blir i innboks/
- [ ] CHANGELOG oppdatert med tidsstempel
- [ ] specs/veikart.md oppdatert
