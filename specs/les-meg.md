# Intelligence Monitor

*Et AI-drevet beslutningsstøttesystem for kunnskapsarbeidere — bygget av noen som selv har kjent problemet fra innsiden.*

---

## Bakgrunnen

Som business controller i flere år erfarte jeg på kroppen hvor krevende det er å holde oversikt over beslutningsrelevant informasjon. Ikke fordi informasjonen mangler — men fordi den er spredt over for mange kilder, kommer inn i for mange kanaler, og aldri stopper. Resultatet er at beslutningstakere enten bruker uforholdsmessig mye tid på å orientere seg, eller tar beslutninger på et tynnere informasjonsgrunnlag enn de burde.

Intelligence Monitor er bygget for å løse det problemet.

---

## Hva gjør det?

Systemet overvåker kontinuerlig et sett definerte informasjonskilder og destillerer innholdet til strukturerte sammendrag tilpasset brukerens preferanser. Du bestemmer kildene. Du bestemmer hva som er relevant. Systemet lærer seg over tid hva du faktisk finner nyttig — gjennom en innebygd evalueringsmekanisme der dine egne vurderinger former hvordan systemet oppsummerer.

I denne versjonen er kildene kurerte AI- og teknologiblogger, nyhetsbrev og YouTube-kanaler. Det er det domenet jeg trenger oversikt over i min rolle som AI-løsningsleder, og det gjør dette til et fungerende arbeidsverktøy, ikke bare en demonstrasjon.

---

## Potensialet

Arkitekturen er domeneuavhengig. Det som overvåker AI-blogger i dag kan like gjerne overvåke en innboks, et dokumentarkiv, bransjenyhetsbrev, interne kunnskapskilder eller konkurranseintelligens. Personaliseringen vokser frem gjennom kalibreringsprosessen — ikke gjennom et konfigurasjonspanel.

---

## Planlagte moduler

| Modul | Hva den gjør | Fase |
|---|---|---|
| **Innhenter** | Henter artikler fra RSS, Substack, nettsider og YouTube/podkaster | A |
| **Velthenter** | Lagrer artikler som Markdown-filer med bilder i Obsidian-vault | A |
| **Nettleserutvidelse** | Manuell artikkellagring via Obsidian Web Clipper | A |
| **Sammendragsmodul** | Norskspråklige sammendrag via Claude API med promptsikkerhet og regulatorisk kontekst | A |
| **Regulatorisk referanse** | Markdown-fil med høydepunkter fra AI Act, NIS2 og ISO 42001 — inkluderes i summarizer-prompten | A |
| **Vurderingsapp** | Streamlit-app med tekst- og taleinput: godkjenn/avvis + kommentar | A |
| **E-postdigest** | Daglig digest per e-post, gruppert per kilde | A |
| **Sporingsmodul** | Observabilitet av alle LLM-kall via Opik | A |
| **Aksial koding** | LLM identifiserer feilmønstre i kommentarer — brukes til å forbedre summarizer-prompten | B |
| **LLM-dommer** | Bygget fra triplets, validert med ML-metodikk (trenings/validerings/testsett) | B |
| **Regresjonstesting** | Automatisk testsett som vokser organisk når domenekspert og LLM-dommer er i sync | B |
| **RAG-innhenting** | Chunker og vektoriserer artikler i lokal vektordatabase | C |
| **Syntetisk datagenerator** | Genererer spørringer for tre brukerprofiler: strategisk, operasjonelt, teknisk | C |
| **Semantisk søk** | Aktiveres etter validert evalueringsdatasett | C |
| **RAG-generator** | Forankrede svar fra hentet kontekst via Claude API | C |
| **RAG-evaluatorer** | Evaluerer gjenfinning og generering separat | C |
| **Regulatorisk RAG** | Lovtekster (AI Act, NIS2, ISO 42001) vektorisert for presis semantisk matching — utvider Markdown-referansen | C/D |
| **Analysemodul** | Programmatisk uttrekk fra Opik SDK og SQLite — kostnad, modell, feil, trender | D |

---

## Hvordan er det bygget?

### Spesifikasjonsdrevet utvikling

Prosjektet starter fra tre levende spesifikasjonsdokumenter — `visjon.md`, `teknologi.md` og `veikart.md` — før én linje kode er skrevet. Dokumentene er bevisst skrevet for å være forståelige for både tekniske og ikke-tekniske lesere. Forretningsbegrunnelse og tekniske beslutninger lever i samme dokument — ikke i hvert sitt siloerte univers. Å holde begge målgrupper i samme dokument reduserer misforståelser og gjør prosjektet enklere å overta, gjennomgå eller utvide.

### Evaluering som gjennomgående arbeidsform

Evalueringsrammeverket gjentas for hvert nytt lag. Tilnærmingen følger Paul Iusztins *AI Evals & Observability*-serie (Decoding AI, 2026).

### Testing underveis

Enhetstester skrives parallelt med hver modul. Regresjonstestsett bygges organisk fra godkjente evalueringer.

---

## Teknologi

Python · Claude API (Anthropic) · SQLite + sqlite-vec · Obsidian-vault · Opik (administrert skytjeneste) · Streamlit · Whisper (lokalt) · uv · pytest

---

## Prosjektdokumenter

| Dokument | Formål |
|---|---|
| [`visjon.md`](./visjon.md) | Hva systemet gjør, hvem det er for, prinsipper |
| [`teknologi.md`](./teknologi.md) | Teknologivalg, arkitektur, feature-arbeidsflyt, testfilosofi |
| [`veikart.md`](./veikart.md) | Implementasjonssekvens med testoppgaver per modul |

---

## Status

**Spesifikasjonsfase fullført.** Implementering starter med fase A.

---

## Forfatter

Bygget av [Audun Klarholm Nilsen](https://www.linkedin.com/in/audunklarholm/) — finans- og AI-profesjonell med bakgrunn som business controller og dataingeniør, grunnlegger av Prosessflyt. Spesialisert på å bygge AI-løsninger som er forankret i reelle forretningsbehov og som kan måles, valideres og forbedres systematisk.
