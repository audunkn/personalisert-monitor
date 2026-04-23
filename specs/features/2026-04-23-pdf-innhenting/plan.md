# Plan: PDF-støtte via vault innboks

## Gruppe 1: Avhengigheter og konfigurasjon
- [x] Legg til pypdf>=4.0.0 i pyproject.toml
- [x] Kjør uv pip install pypdf
- [x] Legg til manuell-pdf-kilde i konfig/kilder.yaml
- [ ] Kjør db.init for å synkronisere ny kilde til SQLite

## Gruppe 2: PDF-håndtering i obsidian_vakt.py
- [x] Importer pypdf øverst i filen
- [x] Legg til _PDF_KILDENAVN-konstant
- [x] Refaktorer on_created til å håndtere både .md og .pdf
- [x] Legg til _prosesser_pdf()-metode
- [x] Legg til _trekk_ut_pdf_innhold()-hjelpefunksjon

## Gruppe 3: Enhetstester
- [x] Opprett tester/test_pdf_innhenting.py
- [x] test_pdf_lagres_korrekt
- [x] test_pdf_tittel_fra_metadata
- [x] test_pdf_duplikat_hoppes_over
- [x] test_pdf_uten_tekst_hoppes_over
- [x] Kjør make test — alle grønne
