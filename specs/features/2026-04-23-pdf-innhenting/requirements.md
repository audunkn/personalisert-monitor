# Requirements: PDF-støtte via vault innboks

## Kilde til issue #5
Brukeren ønsker å legge PDF-filer direkte i `vault/innboks/` og få dem behandlet automatisk, konsistent med manuelt klippede nettsider via Obsidian Web Clipper.

## Omfang
PDF-støtte er begrenset til lokale filer lagt i `vault/innboks/`. Behandlingen følger eksisterende mønster for `.md`-filer: dedup → ekstrakt tekst → lagre → flytt til `behandlet/`.

## Utenfor scope
- OCR for skannede PDFer (ingen tekst → advarsel, fil blir liggende)
- Henting av PDFer fra nett
- Datointervall-filtrering (manuell kanal lagres alltid)
- Per-PDF-kilde (én felles `manuell-pdf`-kilde)

## Bibliotekvalg
`pypdf>=4.0.0` — ren Python, aktivt vedlikeholdt, god tekstekstraksjon fra digitale PDFer.

## URL-dedupstrategi
Dedupnøkkel: `pdf://{fil_sti.stem}` — stabil per filnavn, hindrer dobbeltbehandling uavhengig av filinnhold.

## Kildestruktur
Én felles kilde `manuell-pdf` i `konfig/kilder.yaml` uten datointervall.

## Atferd ved kanttilfeller
- Duplikat (samme filnavn): INFO-logg, fil slettes
- Skannet PDF (ingen tekst): WARNING-logg, fil blir liggende i innboks/
- Fil forsvinner før prosessering: WARNING-logg, ingen videre handling
- Kilde ikke funnet i DB: ERROR-logg, ingen videre handling
