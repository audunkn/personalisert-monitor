# Veikart

*Implementasjonssekvensen med forklaringer. Alle moduler kjøres manuelt via Makefile frem til A5. Enhetstester skrives parallelt med hver modul. Changelog oppdateres ved hver commit og merge.*

*Enumverdier for `komponent`-feltet: `sammendrag`, `dommer_validering`, `rag_gjenfinning`, `rag_generering`.*

---

# FASE A — Produksjonsklar sammendragsmodul med menneskelig evaluering

*Fase A bygger systemet fra bunnen av — fra tomt repo til en fungerende, daglig pipeline som henter artikler, genererer norskspråklige sammendrag med regulatorisk kontekst og lar deg vurdere kvaliteten manuelt. Fasen avsluttes når summarizeren er kalibrert godt nok til at en automatisert dommer kan ta over i fase B. Alt kjøres manuelt via Makefile; ingen automatisering skrus på før systemet er bevist stabilt.*

*Mål: innhenting med konfigurerbart datointervall, sammendrag med regulatorisk kontekst, daglig digest og akkumulering av evalueringstriplets. Kalibrering avsluttes ved ≥ 90 % godkjenningsrate OG ≥ 50 avviste triplets.*

---

## A0 — Fundament

*Fundamentet er prosjektets ryggrad: mappestruktur, versjonskontroll, databaseskjema, konfigurasjonsfiler og utviklingsmiljø legges på plass. Alt videre arbeid bygger på dette laget. Etter A0 kan en utvikler klone repoet og ha et kjørbart, tomt system klart til bruk — ingen funksjonalitet ennå, men all infrastruktur på plass.*

**Implementering:**
- [x] Opprett `src/intelligence_monitor/`-struktur, `tester/`, `specs/` og `specs/features/`.
- [x] Initialiser Git-repo med `.gitignore` (`.env`, `*.db`, `__pycache__`, `.venv`).
- [x] Opprett `CHANGELOG.md` med [Keep a Changelog](https://keepachangelog.com)-format.
- [x] Sett opp Python-miljø: `uv venv` og `pyproject.toml`. Installer med `uv pip install -e .`.
- [x] Lag `Makefile` med targets: `innhent`, `sammendrag`, `review`, `synk`, `regresjon`, `test`, `rapport`, `alle`, `produksjon`.
- [x] Lag `.env` fra `.env.mal` med alle felter, inkl. `HENT_FRA` og `HENT_TIL`.
- [x] Definer `konfig/kilder.yaml` med startkilder og `hent_fra`/`hent_til` per kilde.
- [x] Opprett vault-mapper: `artikler/`, `ressurser/bilder/`, `innboks/`, `behandlet/`.
- [x] Skriv `db/skjema.sql` med alle tabeller inkl. `hent_fra`/`hent_til` i `kilder`, `prompt_versjon` og `er_regresjonstest`.
- [x] Skriv `db/init.py` — idempotent tabellopprettelse og YAML→SQLite-synk inkl. datointervall-felt.
- [x] Konfigurer Opik med `fail_silently=True`. Verifiser konto og API-nøkkel.
- [x] Opprett `specs/regulatorisk-kontekst.md` med høydepunkter fra AI Act, NIS2 og ISO 42001.

**Tester:**
- [x] `test_db_init.py`: idempotens — kjør to ganger, tabeller finnes, ingen data slettet.
- [x] `test_db_init.py`: YAML→SQLite-synk — ny kilde med `hent_fra` dukker opp korrekt, fjernet merkes inaktiv.

---

## A0b — Obsidian Web Clipper

*Manuell innhenting via nettleseren gjør det mulig å klippe artikler man støter på underveis — uten å vente på neste automatiske kjøring. En bakgrunnsprosess (vakt) oppdager nye filer i Obsidian-mappen og registrerer dem i databasen konsistent og atomisk. Dette sikrer at unike enkeltfunn ikke går tapt mellom de automatiserte kildekjøringene.*

**Implementering:**
- [x] Installer og konfigurer Web Clipper mot `innboks/` med YAML-frontmatter: `url`, `klippet_dato`, `kildetype: manuell`.
- [x] Skriv `vault_skriver.py` med konsistensrekkefølge: UUID → fil → SQLite → rollback ved feil.
- [x] Skriv `obsidian_vakt.py` med `watchdog`. Manuelt klippede artikler får ingen datointervall-sjekk — de lagres alltid.
- [x] Røyktest: klipp nettside, verifiser i Obsidian og SQLite.

**Tester:**
- [x] `test_vault_skriver.py`: korrekt filnavn, YAML-frontmatter og UUID mot midlertidig testmappe.
- [x] `test_vault_skriver.py`: UUID i frontmatter matcher `element_id` i SQLite.
- [x] `test_vault_skriver.py`: ugyldig bilde-URL håndteres uten krasj.
- [x] `test_vault_skriver.py`: rollback — fil slettes hvis SQLite-skriving feiler.

**Bugfikser:**
- [x] Issue #7: `start()` skannar nå eksisterende filer i `innboks/` ved oppstart — filer lagt inn før vakten startes prosesseres i alfabetisk rekkefølge. *(2026-04-24)*

---

## A0c — PDF-innhenting via vault innboks

*PDFer lastet ned eller mottatt lokalt kan legges direkte i `vault/innboks/` og behandles automatisk av bakgrunnsvakten. Mønsteret er identisk med Obsidian Web Clipper: dedup → ekstrakt tekst → lagre i vault og SQLite → flytt til `behandlet/`. OCR støttes ikke; skannede PDFer uten digitalt tekstlag hoppes over med advarsel.*

**Implementering:**
- [x] Legg til `pypdf>=4.0.0` i `pyproject.toml`.
- [x] Legg til `manuell-pdf`-kilde i `konfig/kilder.yaml`.
- [x] Utvid `obsidian_vakt.py` med `_prosesser_pdf()` og `_trekk_ut_pdf_innhold()`.

**Tester:**
- [x] `test_pdf_innhenting.py`: gyldig PDF lagres korrekt.
- [x] `test_pdf_innhenting.py`: tittel hentes fra PDF-metadata hvis tilgjengelig.
- [x] `test_pdf_innhenting.py`: duplikat PDF hoppes over.
- [x] `test_pdf_innhenting.py`: PDF uten tekst hoppes over med advarsel.

---

## A0d — Automatisk opprydning ved sletting av artikkel

*Når en `.md`-fil slettes fra `vault/artikler/`, fjerner bakgrunnsvakten automatisk tilhørende bildefiler og SQLite-rad. Løsningen utvider watchdog-observeren fra A0b med en ny `_ArtikkelHandler` og legger til `bilder_json`-kolonne i `elementer`-tabellen for å holde styr på hvilke bilder en artikkel eier.*

**Implementering:**
- [x] `db/skjema.sql` og `db/init.py` — ny `bilder_json TEXT`-kolonne, idempotent migrering.
- [x] `vault_skriver.py` — `_behandle_bilder()` returnerer bildeliste; `lagre_artikkel()` lagrer som JSON i `bilder_json`.
- [x] `obsidian_vakt.py` — `_ArtikkelHandler` med `on_deleted`; `_rydd_etter_slettet_artikkel()` sletter bilder og DB-rad; observer overvåker nå `innboks/` og `artikler/`.

**Tester:**
- [x] `test_artikkel_sletting.py`: slett artikkel med bilder.
- [x] `test_artikkel_sletting.py`: slett artikkel uten bilder.
- [x] `test_artikkel_sletting.py`: ukjent fil ignoreres.
- [x] `test_artikkel_sletting.py`: bilder_json lagres ved opprettelse.

---

## A1 — RSS-innhenting med datointervall

*RSS er den viktigste automatiserte innhentingskanalen: feeder leses, publiseringsdato sjekkes mot konfigurerbart datointervall, og kun nye artikler innenfor intervallet skrives til vault og database. Duplikatsjekk sikrer at samme artikkel aldri lagres to ganger uansett hvor mange ganger kilden hentes.*

**Implementering:**
- [x] Skriv `rss.py` med `feedparser` og følgende logikk per element:
  1. Les `hent_fra` og `hent_til` per kilde fra `kilder`-tabellen (env-override hvis `HENT_FRA`/`HENT_TIL` er satt)
  2. Sjekk publiseringsdato — utenfor intervall → hopp over stille, ingen logging
  3. Innenfor intervall → sjekk `url` mot `elementer`-tabellen (URL-basert dedup)
  4. Kjent fra før → hopp over stille
  5. Ny → kall `vault_skriver.py`, lagre `vault_sti` i SQLite
- [x] Kjørbar via `make innhent`.
- [x] Røyktest: tre startkilder med smalt `HENT_FRA`-intervall, verifiser at kun artikler i intervallet lagres.

**Tester:**
- [x] `test_rss.py`: artikkel innenfor intervall lagres korrekt.
- [x] `test_rss.py`: artikkel utenfor `hent_fra` hoppes over stille.
- [x] `test_rss.py`: artikkel utenfor `hent_til` hoppes over stille.
- [x] `test_rss.py`: kjent URL lagres ikke på nytt selv om den er innenfor intervallet.
- [x] `test_rss.py`: env-override `HENT_FRA` overstyrer per-kilde-konfig korrekt.
- [x] `test_rss.py`: tom feed håndteres uten feil.

---

## A2a — Sammendragsmodul med regulatorisk kontekst

*Kjernen i systemet: en artikkel leses fra Obsidian-vault, pakkes inn med regulatorisk kontekst (AI Act, NIS2, ISO 42001) og sendes til OpenAI (gpt-4.1) for å produsere et norskspråklig sammendrag med en koblingsparagraf som peker på relevante regulatoriske implikasjoner. Hvert sammendrag knyttes til en spesifikk prompt-versjon slik at man alltid kan spore tilbake hvilken prompt som produserte et gitt resultat — og sammenligne versjoner mot hverandre.*

**Implementering:**
- [x] Opprett `sammendrag/prompts/v1.txt` som baseline-prompt. Inkluder instruksjon om å produsere en regulatorisk koblingsparagraf basert på `specs/regulatorisk-kontekst.md`. Tag `prompt-v1`. Oppdater `CHANGELOG.md`.
- [x] Skriv `lag_sammendrag.py`: les aktiv prompt, les artikkeltekst fra vault-fil, les `regulatorisk-kontekst.md` og inkluder som kontekst, kutt til `MAKS_ARTIKKEL_TOKENS`, pakk i XML-tagger, kall OpenAI API med `@opik.track`, lagre i `sammendrag`-tabellen med `prompt_versjon`.
- [x] Kjørbar via `make sammendrag`.
- [x] Røyktest: 3 artikler, verifiser sammendrag med regulatorisk paragraf i SQLite og spor i Opik.

**Tester:**
- [x] `test_lag_sammendrag.py`: XML-innramming korrekt formatert.
- [x] `test_lag_sammendrag.py`: tekst over `MAKS_ARTIKKEL_TOKENS` kuttes riktig.
- [x] `test_lag_sammendrag.py`: `prompt_versjon` lagres korrekt.
- [x] `test_lag_sammendrag.py`: `regulatorisk-kontekst.md` inkluderes i prompten.
- [x] `test_lag_sammendrag.py`: manglende vault-fil gir meningsfull feilmelding.

---

## A2b — Triplet-lager og vurderingsapp

*Menneskelig vurdering er det primære kvalitetssignalet i systemet. En enkel Streamlit-app viser artikkel og sammendrag side om side og lar deg godkjenne eller avvise med kommentar — via tekst eller tale. Vurderingene lagres som evalueringstriplets (input, output, vurdering) og er råmaterialet for all videre automatisert kvalitetsmåling i fase B.*

**Implementering:**
- [x] Skriv `triplet_lager.py` — datalag for `evalueringstriplets`.
- [x] Bygg `vurderingsapp.py` i Streamlit med:
  - Kildenavn, URL, artikkeltekst (komprimert/ekspanderbar), bilder, sammendrag og `prompt_versjon`
  - Godkjent/avvist-knapper
  - Kommentarfelt med valg mellom **tekst** og **tale** (Whisper lokalt, sky som reserve)
  - Løpende godkjenningsrate og antall avviste triplets
  - "Synkroniser til Opik"-knapp etter sesjon
  - Skriv triplet til SQLite med `komponent: sammendrag` ved innsending
- [ ] Røyktest: review 5 sammendrag inkl. vurdering av regulatorisk paragraf.

**Tester:**
- [x] `test_triplet_lager.py`: triplet skrives og leses korrekt.
- [x] `test_triplet_lager.py`: godkjenningsrate og antall avviste beregnes korrekt.
- [x] `test_triplet_lager.py`: filtrering på `komponent` fungerer.
- [x] `test_triplet_lager.py`: duplikate innsendinger håndteres.

---

## A2c — Opik-synkronisering

*Triplets synkroniseres inkrementelt til Opik — skybasert observabilitetsplattform — som gir ekstra backup, historikk på tvers av eksperimenter og mulighet for Opik-native visualisering og rapportering. SQLite forblir primærkilde; Opik er synkronisert kopi.*

**Implementering:**
- [ ] Skriv `opik_synk.py` — push nye triplets siden siste synkronisering fra SQLite til Opik.
- [ ] Røyktest: synkroniser, verifiser i Opik UI.

**Tester:**
- [ ] `test_opik_synk.py`: kun nye triplets sendes — mot mock av Opik-klienten.
- [ ] `test_opik_synk.py`: Opik utilgjengelig → advarsel logges, ingen krasj, SQLite urørt.

---

## A3 — Kalibreringsfase

*Kalibreringsfasen er ikke en teknisk implementeringsfase, men en kvalitetssikringsloop: man kjører, vurderer og justerer prompten gjentatte ganger til to terskler er nådd. Hvert iterasjonssyklus registreres som et eget eksperiment i Opik slik at forbedringen er sporbar. Dette er den formelle godkjenningsporten for sammendragsmodulen — fasen er ferdig først når systemet dokumentert er godt nok.*

*Avsluttes når: godkjenningsrate ≥ 90 % OG ≥ 50 avviste triplets. Regulatorisk paragraf evalueres som del av hvert sammendrag.*

**Implementering:**
- [ ] Frys kalibreringsdatasett på 20–30 artikler innenfor et definert datointervall.
- [ ] `make sammendrag`. Registrer som Eksperiment 1 i Opik.
- [ ] `make review`: vurder alle, inkl. regulatorisk kobling. Skriv konkrete kommentarer.
- [ ] Juster prompt → `prompts/v2.txt` → Git-tag `prompt-v2` → oppdater `CHANGELOG.md`.
- [ ] Gjenta til terskler er nådd.
- [ ] Dokumenter: vinnende prompt-versjon, mønstre i avvisningene, funn om regulatorisk kobling.

*Ingen nye enhetstester.*

---

## A4 — Nettskraping, Substack og koordinator

*Mange relevante kilder publiserer ikke RSS-feed og krever direkte skraping av nettsider eller Substack-nyhetsbrev. En koordinatorprosess orkestrerer alle kildetyper under ett: feil i én kilde stopper ikke de andre, og feilede elementer merkes for oppfølging. Dette gjør innhentingslaget robust nok for daglig drift.*

**Implementering:**
- [ ] Skriv `nett.py` med `httpx`/`BeautifulSoup4` og Substack-tolker. Samme datointervall-logikk som `rss.py`: sjekk publiseringsdato → dedup → lagre.
- [ ] Skriv `kjører.py` — koordinator med kildetype-ruting, feilmeldingsvarsling per e-post og gjenforsøkslogikk. Feil i én kilde stopper ikke de andre.
- [ ] Dead-letter-markering i `elementer`-tabellen.
- [ ] Røyktest: to Substack-kilder og én nettside med smalt datointervall.

**Tester:**
- [ ] `test_nett.py`: CSS-velger trekker ut riktig innhold fra lagret HTML-eksempel.
- [ ] `test_nett.py`: artikkel utenfor datointervall hoppes over.
- [ ] `test_nett.py`: HTTP 404 håndteres uten krasj, merkes som feilet.
- [ ] `test_kjører.py`: feil i én kilde stopper ikke de andre.
- [ ] `test_kjører.py`: exception sender e-post — mot mock av SMTP.

---

## A5 — Daglig digest og automatisering

*Det daglige arbeidet skal skje uten manuelle terminalkommandoer. En cron-jobb kjører hele pipelinen hver morgen og sender en samlet e-post med dagens sammendrag gruppert per kilde. Dette markerer overgangen fra utviklermodus til faktisk daglig bruk — fra noe man kjører til noe som bare kjører.*

**Implementering:**
- [ ] Skriv `epost.py`: hent dagens sammendrag, grupper per kilde, bygg HTML-e-post. Valgfritt: skriv Markdown til Obsidian-vault.
- [ ] Test SMTP manuelt.
- [ ] Sett opp cron-jobb kl. 07:00 via `make alle` når manuell kjøring er stabil.

**Tester:**
- [ ] `test_epost.py`: HTML-struktur korrekt for kjent sett sammendrag.
- [ ] `test_epost.py`: tom liste sender ikke e-post.

---

## A6 — YouTube og podkast

*Video og podkast er rike informasjonskilder som ikke lar seg fange med RSS eller skraping alene. En transkripsjonspipeline henter tekst fra YouTube — via eksisterende undertekster eller Whisper som reserve — og integrerer resultatet i den eksisterende flyten via vault_skriver. Lange videoer deles i overlappende tekstdeler for å unngå kontekstbegrensninger i sammendragsmodellen.*

**Implementering:**
- [ ] Skriv `youtube.py` med `youtube-transcript-api` og `yt-dlp` + `Whisper` som reserve. Datointervall-sjekk på videodato før transkripsjon — unngår unødvendig prosessering av videoer utenfor intervallet.
- [ ] Oppdeling av lange transkripsjoner i overlappende deler.
- [ ] Lagre via `vault_skriver.py`.
- [ ] Røyktest: én YouTube-kanal med smalt datointervall.

**Tester:**
- [ ] `test_youtube.py`: oppdeling gir korrekt antall deler med riktig overlapp.
- [ ] `test_youtube.py`: video utenfor datointervall hoppes over.
- [ ] `test_youtube.py`: kanal uten transkripsjon håndteres uten krasj.

---

# FASE B — LLM-dommer og regresjonstesting

*Fase B erstatter den manuelle vurderingssløyfen med en automatisert "dommer" — et LLM kalibrert mot domenekspertens egne vurderinger fra fase A. Målet er å kunne kjøre `make regresjon` og få en objektiv kvalitetsrapport uten å lese hvert enkelt sammendrag. Dommeren er ikke en erstatning for menneskelig skjønn, men en skala­bar proxy som fanger opp systematiske forverringer raskt.*

*Forutsetter: stabil fase A, ≥ 50 avviste triplets, ≥ 200 merkede triplets.*

---

## B1 — Aksial koding og prompt-forbedring

*Aksial koding er en semi-automatisert analyse av hva som systematisk går galt: avvisningskommentarene fra fase A sendes til et LLM som grupperer dem i navngitte feilkategorier med eksempler. Kategoriene brukes til å forbedre summarizer-prompten — og de informerer rubrikken LLM-dommeren i B3 skal vurdere mot. Aksial koding forbedrer altså *summarizer-prompten*, ikke dommeren direkte.*

**Implementering:**
- [ ] Skriv `aksial_koding.py`: hent avvisningskommentarer med `komponent: sammendrag` fra SQLite, send til LLM, returner feilkategorier med eksempler.
- [ ] Bruk funnene til ny prompt-versjon. Tag og oppdater `CHANGELOG.md`.
- [ ] Dokumenter feilkategoriene — de informerer rubrikken til LLM-dommeren i B2.

**Tester:**
- [ ] `test_aksial_koding.py`: tomt kommentarsett håndteres uten feil.
- [ ] `test_aksial_koding.py`: output har forventet struktur — mot mock av LLM-kall.

---

## B2 — Evalueringsrammeverk

*Evalueringsrammeverket er infrastrukturen som gjør det mulig å kjøre reproduserbare kvalitetsmålinger: det laster et datasett, kjører komponenten, sjekker regelbaserte krav (er output på norsk? er lengden riktig?) og aggregerer alt til en strukturert rapport registrert som Opik-eksperiment. Uten dette rammeverket er det umulig å sammenligne to prompt-versjoner objektivt — med det tar det ett kommando. Rammeverket automatiserer det du ellers ville gjort manuelt steg for steg i terminalen.*

**Implementering:**
- [ ] Skriv `rammeverk.py` som i sekvens:
  1. Laster spesifisert datasett fra Opik
  2. Kjører aktuell komponent på hvert element
  3. Kjører regelbaserte sjekker: norsk output? Innenfor lengdeintervall?
  4. Kjører LLM-dommer på hvert element
  5. Aggregerer poengsum per element og totalt
  6. Registrerer som Opik-eksperiment
- [ ] Regelbaserte sjekker implementeres og testes isolert.

**Tester:**
- [ ] `test_rammeverk.py`: norsk-sjekk korrekt for norsk og ikke-norsk tekst.
- [ ] `test_rammeverk.py`: lengdesjekk på grensetilfeller.
- [ ] `test_rammeverk.py`: elementer under terskel flagges korrekt.

---

## B3 — Bygg og valider LLM-dommer

*LLM-dommeren er systemets automatiserte kvalitetsvokter: den bruker few-shot prompt kalibrert mot domenekspertens vurderinger og måles statistisk på om den er enig med eksperten. Utviklings- og valideringssett brukes til iterasjon; testsettet røres ikke før sluttevaluering. Dommeren deployes kun hvis sann-positiv rate ≥ 85 % og sann-negativ rate ≥ 75 % — dette er den formelle godkjenningsporten.*

**Implementering:**
- [ ] Del `evalueringstriplets`: 70 % trening, 15 % validering, 15 % test (røres ikke under trening).
- [ ] Skriv `llm_dommer.py` med few-shot prompt fra stratifisert utvalg av treningssettet.
- [ ] Skriv `dommer_validator.py`: mål presisjon, gjenkalling, F1 og Cohens kappa.
- [ ] Iterer mot valideringssettet til sann-positiv rate ≥ 85 % og sann-negativ rate ≥ 75 %. Evaluer mot testsettet én gang. Dokumenter og ta deploy-beslutning.
- [ ] Bygg side-by-side visning i Streamlit: domenekspertens vurdering vs. LLM-dommerens vurdering, differanser uthevet.
- [ ] Implementer `er_regresjonstest`-logikk: sett flagget automatisk ved enighet.
- [ ] Kjørbar via `make regresjon`.

**Tester:**
- [ ] `test_llm_dommer.py`: few-shot prompt inneholder eksempler fra alle feilkategorier — mot mock.
- [ ] `test_llm_dommer.py`: XML-innramming brukes i API-kall.
- [ ] `test_dommer_validator.py`: presisjon, gjenkalling og kappa beregnes korrekt for kjent fasit.
- [ ] `test_dommer_validator.py`: datasettdeling gir riktig fordeling uten overlapping.
- [ ] `test_regresjonstest.py`: `er_regresjonstest` settes ved enighet, ikke ved uenighet.

---

## B4 — Produksjon med kontinuerlig evaluering

*Når dommeren er godkjent kobles den inn i den daglige produksjonsflyten. Sammendrag med lav poengsum flagges automatisk i Streamlit-appen for manuell oppfølging — systemet ber selv om hjelp når det er usikkert. Ukentlige rapporter via `make rapport` gir oversikt over kvalitetsutviklingen over tid.*

**Implementering:**
- [ ] Koble dommer inn i rammeverket. Lav poengsum flagges i Streamlit.
- [ ] Ukentlig rapport via `make rapport`.

---

# FASE C — Semantisk søk

*Fase C gjør arkivet søkbart på naturlig språk: i stedet for å bla gjennom innhentede artikler kan du stille spørsmål og få et sammenstilt svar med kildehenvisninger. Teknisk bygges en RAG-pipeline (Retrieval-Augmented Generation) der artikler vektoriseres, relevante tekstdeler hentes frem ved søk, og OpenAI genererer et svar basert på disse. Evalueringsinfrastrukturen fra fase B gjenbrukes og utvides til å dekke søkekvalitet.*

*Forutsetter: stabil fase B, ≥ 500 elementer.*

---

## C1 — Grunnlag: indeksering og teknisk søk

*Grunnlaget for semantisk søk er vektorisering: artikkeltekster deles i overlappende tekstdeler (chunks), hver del omgjøres til en tallvektor (embedding) og lagres i sqlite-vec lokalt. Søk gjøres ved å finne de tekstdelene hvis vektor er nærmest spørringens vektor — cosine-similaritet. I C1 implementeres og testes dette teknisk, men det aktiveres ikke for reell bruk før evalueringsinfrastrukturen er på plass i C5.*

**Implementering:**
- [ ] Installer sqlite-vec.
- [ ] Skriv `vektoriser.py` og `innhent.py`: les vault-filer, del opp (300–500 tokens, 50 tokens overlapp), lagre vektorer.
- [ ] Skriv `søk.py` — teknisk implementasjon, ikke aktivert for reell bruk ennå.
- [ ] Legg til `rag_spor`-tabell.
- [ ] Røyktest: indekser 10 artikler.

**Tester:**
- [ ] `test_innhent.py`: oppdeling gir korrekt antall deler med riktig overlapp.
- [ ] `test_innhent.py`: vektorer har forventet dimensjon.
- [ ] `test_søk.py`: cosine-similaritet returnerer nærmeste nabo for kjent vektorsett.

---

## C2 — Generering

*Gjenfinning alene er ikke nok — brukeren trenger et sammenhengende svar, ikke en liste med tekstfragmenter. De hentede tekstdelene sendes til OpenAI som kontekst, og systemet genererer et norsk svar på spørringen. Hvert trinn i pipelinen (gjenfinning og generering) spores separat i Opik slik at man kan isolere feil til riktig komponent.*

**Implementering:**
- [ ] Skriv `generer.py` med XML-innramming og `@opik.track` med separate spenn.
- [ ] Intern test: 10 spørringer manuelt.

**Tester:**
- [ ] `test_generer.py`: kontekst pakkes korrekt i XML-tagger.
- [ ] `test_generer.py`: tom kontekstliste håndteres uten krasj.

---

## C3 — Syntetisk datagenerering

*For å evaluere søkekvalitet trenger man realistiske testspørringer — men å skrive dem manuelt er tidkrevende. Syntetisk generering lager dem automatisk ved å transformere innhentede artikler til spørsmål fra tre perspektiver: strategisk (implikasjoner for virksomheten), operasjonelt (hva bør gjøres?) og teknisk (hvordan virker det?). Kanttilfeller utenfor scope inkluderes for å teste at systemet vet hva det ikke vet. Tre profiler sikrer dekning av ulike informasjonsbehov.*

**Implementering:**
- [ ] Skriv `syntetisk_gen.py`: generer spørringer fra oppsummerte artikler for alle tre profiler, inkl. kanttilfeller utenfor scope.
- [ ] Kjør gjennom søkepipeline, spor i Opik, legg i vurderingskø.

**Tester:**
- [ ] `test_syntetisk_gen.py`: alle tre profiler produserer output med forventet struktur — mot mock.
- [ ] `test_syntetisk_gen.py`: kanttilfeller er representert.

---

## C4 — Menneskelig evaluering av søk

*Menneskelig evaluering av søk følger samme metodikk som fase A, men er mer kompleks: gjenfinning og generering vurderes separat fordi de kan feile uavhengig av hverandre (feil chunks gir riktig nok svar, eller gode chunks gir dårlig syntese). Streamlit-appen utvides med søkemodus. Error analysis danner grunnlaget for aksial koding og videre justering.*

**Implementering:**
- [ ] Utvid Streamlit med søkemodus: vis spørring, retrieved chunks med kildenavn og dato, generert svar. Separate vurderinger for gjenfinning og generering. Tale støttes.
- [ ] Frys søkekalibreringsdatasett på 20–30 spørringer og gjennomfør error analysis.
- [ ] Aksial koding separat for gjenfinning og generering.

**Tester:**
- [ ] `test_triplet_lager.py` (utvid): RAG-triplets lagres og filtreres korrekt.

---

## C5 — Søkeevaluatorer

*Søkeevaluatorene automatiserer det manuelle evalueringsarbeidet fra C4, på samme måte som B3 automatiserte A-fase-evalueringen. RAG-evaluering er mer sammensatt enn sammendragsevaluering: alle seks relasjoner mellom spørring (Q), kontekst (C) og svar (A) sjekkes — er konteksten relevant for spørringen? Er svaret støttet av konteksten? Valideringsmetodikken fra B3 gjenbrukes separat for gjenfinning og generering.*

**Implementering:**
- [ ] Skriv `dommer_rag.py` med alle seks Q/C/A-relasjoner. Regelbaserte sjekker + LLM-dommer per komponent.
- [ ] Valider med B3-metodikken — separat for gjenfinning og generering.
- [ ] Side-by-side visning i Streamlit for RAG-komponentene.

**Tester:**
- [ ] `test_dommer_rag.py`: regelbaserte sjekker mot kjente eksempler.
- [ ] `test_dommer_validator.py` (gjenbruk): valideringslogikken er identisk.

---

## C6 — Aktiver søk, integrer dommer og valgfri regulatorisk RAG

*Søket aktiveres for reell bruk først etter at evalueringsinfrastrukturen er på plass og validert — dette er en bevisst sekvens for å unngå å ta i bruk et system man ikke kan måle kvaliteten på. Daglig kjøring av søkerammeverket overvåker driften. Den valgfrie regulatoriske RAG-utvidelsen erstatter den statiske Markdown-filen med dynamisk gjenfinning fra vektorisert regulatorisk kildemateriale, dersom den statiske tilnærmingen viser seg for grov.*

**Implementering:**
- [ ] Aktiver `søk.py` for reell bruk etter validert evalueringsinfrastruktur.
- [ ] Kjør søkerammeverket daglig. Ukentlig rapport via `make rapport`.
- [ ] **Valgfri:** Hvis Markdown-referansen gir for grove regulatoriske koblinger: vektoriser AI Act, NIS2 og ISO 42001 i eget sqlite-vec-vektorsett. Integrer i summarizer som erstatning for statisk Markdown. Evalueringsinfrastrukturen er upåvirket.

---

# FASE D — Observabilitet, analyse og vedlikehold

*Fase D gjør systemet driftsklart for langtidsbruk: analyserappporter gir innsikt i kvalitetsutvikling over tid, kildehelseovervåkning varsler om brutte feeds, og Docker-pakking gjør det mulig å flytte systemet til en server uten manuell konfigurasjon. Fasen er også stedet for dokumentasjon og arkivstrategi.*

---

## D1 — Analysemodul

*Analysemodulen samler data fra SQLite og Opik og produserer fire rapporttyper: ukentlig driftsrapport (hva ble hentet og oppsummert), kalibreringsstatus (promptversjon og godkjenningsrate), dommerytelse (presisjon/gjenkalling over tid) og RAG-ytelse (søkekvalitetsutvikling). Rapportene leveres per e-post og/eller skrives til Obsidian-vault for arkivering.*

**Implementering:**
- [ ] Skriv `opik_henter.py`, `sqlite_henter.py` og `rapport.py`.
- [ ] Fire rapporttyper: ukentlig drift, kalibrering, dommerytelse, RAG-ytelse.
- [ ] Levering per e-post og/eller Markdown til vault. Kjørbar via `make rapport`.

**Tester:**
- [ ] `test_rapport.py`: aggregeringsberegninger korrekte, tom periode håndteres.
- [ ] `test_sqlite_henter.py` og `test_opik_henter.py`: mot mock av Opik SDK.

---

## D2 — Kildehelse-monitor

*Kildehelseovervåkning er en enkel men kritisk sikkerhetsmekanisme: hvis en kilde ikke har levert innhold på N dager (konfigurerbart per kilde i `kilder.yaml`), sendes e-postvarsling. Dette fanger opp brutte RSS-feeder, endrede URL-er og nedetid hos kilden — uten at man manuelt må sjekke om systemet faktisk henter noe.*

**Implementering:**
- [ ] E-postvarsling hvis kilde ikke har levert på N dager (konfigurerbart per kilde i `kilder.yaml`).

**Tester:**
- [ ] `test_kildehelse.py`: kilde uten innhold på N+1 dager flagges korrekt.

---

## D3 — Infrastruktur

*Den avsluttende fasen pakker systemet i Docker slik at det kan startes med ett kommando på en hvilken som helst maskin. Fullstendig dokumentasjon i `les-meg.md` gjør det mulig å sette opp systemet på nytt uten å huske konfigurasjonssteg. Arkivstrategien definerer hva som lagres permanent og hva som roteres bort over tid.*

- [ ] Docker og automatisert oppstart.
- [ ] Eventuell skyflytting til GCP.
- [ ] Fullstendig dokumentasjon i `les-meg.md`.
- [ ] Arkivstrategi defineres.

---

## Utenfor rekkevidde

**Flerbrukerstøtte** er ikke planlagt.

**Obsidian-digest-integrasjon** — implementeres som valgfritt flagg i A5, aktiveres i D3.

**Automatisk promptoptimering via Opik Optimizer** er en mulig fase E.
