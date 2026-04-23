# Validation: PDF-støtte via vault innboks

## Merge-kriterier

- [x] `make test` passerer (alle eksisterende + 4 nye tester grønne)
- [x] Manuell røyktest: PDF dropped i innboks → rad i SQLite, PDF i behandlet/
- [x] Duplikat PDF → INFO-logg, ingen ny rad, fil slettes (dekket av enhetstest)
- [x] Skannet PDF (ingen tekst) → WARNING-logg, filen blir i innboks/ (dekket av enhetstest)
- [x] CHANGELOG oppdatert med tidsstempel
- [x] specs/veikart.md oppdatert
