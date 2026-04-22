# Visjon

*Dette dokumentet beskriver hva systemet er, hvorfor det bygges, og hvilke prinsipper som styrer alle valg underveis.*

---

## Bakgrunnen for dette prosjektet

Som business controller i flere år erfarte jeg på kroppen et problem jeg tror mange kjenner seg igjen i: informasjonen du trenger for å ta gode beslutninger finnes — men den er spredt over for mange kilder, kommer inn i for mange kanaler, og stopper aldri. Du kan ikke følge alt. Så du velger, bevisst eller ubevisst, å ikke følge nok.

Resultatet er ikke nødvendigvis feil beslutninger. Men det er beslutninger tatt på et tynnere grunnlag enn nødvendig, fordi informasjonsarbeidet koster for mye tid.

Intelligence Monitor er et forsøk på å løse det problemet med moderne AI-verktøy — bygget av noen som kjenner behovet fra innsiden.

---

## Hva er dette systemet?

Intelligence Monitor er et personlig overvåkningssystem som kontinuerlig følger definerte informasjonskilder og destillerer innholdet til strukturerte sammendrag tilpasset brukerens preferanser og informasjonsbehov.

I denne versjonen overvåker systemet kurerte AI- og teknologikilder. Det er det domenet som er relevant i rollen som AI-løsningsleder, og det gjør dette til et fungerende arbeidsverktøy som løser et reelt daglig behov.

---

## Potensialet — et generisk rammeverk for beslutningsstøtte

Arkitekturen er domeneuavhengig. Det som overvåker AI-blogger i dag kan like gjerne overvåke en innboks, et dokumentarkiv, bransjenyhetsbrev, interne kunnskapskilder eller konkurranseintelligens fra definerte eksterne kilder.

Personaliseringen skjer ikke gjennom et konfigurasjonspanel. Den vokser frem gjennom kalibreringsprosessen der brukeren godkjenner og avviser sammendrag med egne kommentarer. En generisk startprompt blir over tid til et presist instrument innstilt på akkurat den brukerens informasjonsbehov og kommunikasjonsstil.

---

## Kildetyper (denne versjonen)

**RSS- og Atom-strømmer** — maskinlesbare lister over nye artikler fra fagblogger og publiseringsplattformer.

**Substack-nyhetsbrev** — nettskraping av offentlige nettsider.

**Nettsider uten strøm** — periodisk skraping med endringsdeteksjon.

**YouTube-kanaler og podkaster** — automatisk transkripsjon lokalt.

**Manuell nettklipper** via Obsidian Web Clipper — ett klikk fra nettleseren.

---

## Lagringsfilosofi

**Obsidian-vaulten** eier innholdet. Alle innhentede artikler lagres som Markdown-filer med bilder inline — lesbare og navigerbare direkte i Obsidian, uavhengig av systemet forøvrig.

**SQLite** eier operasjonell og evalueringsorientert data. Metadata, relasjoner, sammendrag, evalueringstriplets og vektorer. Inneholder filpeker til artikkelen i vaulten, ikke teksten selv.

**Opik** eier observabilitet og eksperimentsporing. Evalueringstriplets synkroniseres hit som en avledet kopi — SQLite er alltid primærkilden.

Ingen av de tre lagrer det de andre eier.

---

## Utdata

Én daglig digest per e-post og/eller som Markdown-fil i Obsidian-vaulten, gruppert per kilde, med norskspråklige sammendrag av alt nytt innhold siden forrige kjøring.

*Obsidian-digest-integrasjon* betyr at digesten skrives direkte som en Markdown-fil til vaulten i tillegg til e-post. Den blir søkbar, lenkerbar og historisk tilgjengelig på samme måte som alle andre innhentede artikler.

---

## Regulatorisk kontekst i sammendragene

Hvert sammendrag inneholder en kort paragraf som beskriver hvordan artikkelen relaterer seg til gjeldende AI-regulering — AI Act, NIS2, ISO 42001 og relevante norske standarder.

### Fase A — Markdown-referanse

En strukturert fil `specs/regulatorisk-kontekst.md` med høydepunkter fra sentrale regelverk inkluderes direkte i summarizer-prompten. Summarizeren bruker denne som oppslagsverk og produserer en regulatorisk koblingsparagraf per sammendrag. Enkel å vedlikeholde og gir funksjonaliteten umiddelbart — uten ny infrastruktur.

Kalibreringsfasen avgjør om koblingene er presise nok, eller om mer granulær tilnærming er nødvendig.

### Fase C/D — Regulatorisk RAG (valgfri utvidelse)

Hvis kalibreringen viser at Markdown-referansen er for grov, vektoriseres lovtekstene og legges i et eget sqlite-vec-vektorsett. For hver artikkel hentes da de semantisk mest relevante regulatoriske delene frem og inkluderes i prompten. Migrasjonen fra Markdown til RAG endrer ikke evalueringsinfrastrukturen — kun innhentingssteget i summarizeren.

---

## Evalueringsmodellen — en gjennomgående arbeidsform

For hvert resultat registreres kildereferansen, resultatet og brukerens vurdering som en **evalueringstriplet**: *(referanse, resultat, menneskelig vurdering)*. Vurderingen består av godkjent/avvist og en fritekstkommentar fra domenekspert via tekst eller tale. Ingen forhåndsdefinerte kategorier.

Rammeverket følger Paul Iusztins *AI Evals & Observability*-serie (Decoding AI, 2026). Kjerneprinsippet: forstå hva som faktisk feiler i dine data, før du bygger evaluatorer. Og gjenta dette for hver ny komponent.

### Aksial koding og prompt-forbedring

Aksial koding leser domenekspertens kommentarer og identifiserer feilmønstre. Disse funnene brukes til å forbedre *summarizer-prompten* — ikke til å bygge dommeren direkte.

### LLM-dommer

LLM-dommeren bygges fra evalueringstriplets som few-shot eksempler og valideres med standard ML-metodikk: trenings-, validerings- og testsett.

### Regresjonstesting

Når domenekspert og LLM-dommer er enige om en vurdering, kategoriseres datapunktet automatisk som et regresjonstestpunkt. Regresjonssettet vokser organisk og verifiserer at systemet ikke forringes ved endringer.

### De tre systemfasene

**Fase A** — Produksjonsklar sammendragsmodul med menneskelig evaluering og regulatorisk kontekst fra Markdown-referanse. Kalibrering avsluttes ved ≥ 90 % godkjenningsrate og ≥ 50 avviste triplets.

**Fase B** — LLM-dommer bygget fra triplets, validert med ML-metodikk. Aksial koding forbedrer summarizer-prompten. Regresjonstestsett etableres.

**Fase C** — Semantisk søk med syntetiske testprofiler (strategisk, operasjonelt, teknisk) og samme evalueringsmetodikk som fase A og B. Valgfri regulatorisk RAG-utvidelse.

---

## Prinsipper

**Enkelthet først.** Ny kompleksitet legges til når eksisterende er stabil og testet.

**Lokal kontroll.** All databehandling skjer på din maskin.

**Klar ansvarsfordeling.** Obsidian eier innhold. SQLite eier operasjonell data. Opik eier observabilitet. Ingen overlapping.

**SQLite er alltid primærkilden.**

**Data fra dag én.** Triplets samles fra første kjøring.

**Evaluering er en arbeidsform.** Samme metodikk for alle komponenter.

**Regulatorisk kontekst er innebygd.** Starter enkelt med Markdown, skalerer til RAG ved behov.

**Dommeren bygges fra data.** Few-shot fra triplets, ikke fra aksial koding direkte.

**Evaluer evaluatoren.** Validering med ML-metodikk før deploy.

**Regresjon er innebygd.** Synkroniserte triplets blir automatisk regresjonstestpunkter.

**Arkitektur kan justeres.** Grensene mellom lagringslagene er bevisste valg, ikke permanente beslutninger.

**Arkivstrategi** defineres ved behov.
