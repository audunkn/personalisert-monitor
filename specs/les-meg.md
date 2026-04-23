# Intelligence Monitor

---

## Bakgrunnen

I rollen som business controller hadde jeg aldri mangel på informasjon. Problemet var mengden av den. E-poster, møtereferater, rapporter, regneark og chatmeldinger hopet seg opp fra alle kanter. Noe var kritisk. Det meste var støy. Og det tok altfor lang tid å finne ut av forskjellen.

Resultatet var beslutninger tatt på et tynnere grunnlag enn nødvendig, fordi informasjonsarbeidet i seg selv kostet for mye tid.

Dette systemet er bygget på den samme erfaringen, men brukt i en annen sammenheng. Som AI Solution Engineer er informasjonsbehovet et annet: fagblogger, forskningsartikler, nyhetsbrev og YouTube-kanaler om AI og teknologi. Kildene er åpne og offentlige, tempoet er høyt og volumet vokser hver uke. Problemet er gjenkjennelig.

Intelligence Monitor følger kildene på mine vegne og leverer det som faktisk er relevant.

---

## Hva gjør det?

Tenk deg at du abonnerer på 20 fagblogger og nyhetsbrev. Hver dag publiseres det kanskje 30 nye artikler på tvers av kildene. Du har tid til å lese fem. Hvem velger ut de fem?

Intelligence Monitor gjør det. Den henter artiklene automatisk, leser dem og destillerer innholdet til strukturerte sammendrag tilpasset brukerens preferanser og informasjonsbehov. Sammendragene kobler innholdet til regulatorisk kontekst der det er relevant, som AI Act, NIS2 og ISO 42001. Til slutt leveres alt samlet i en daglig e-post.

Over tid lærer systemet hva du finner nyttig. Det skjer gjennom en innebygd vurderingsmekanisme: du godkjenner eller avviser sammendrag med en kort kommentar, og systemet bruker disse tilbakemeldingene til å stille inn seg selv på akkurat din måte å tenke på.

I denne versjonen følger systemet kurerte AI- og teknologikilder. Det er domenet jeg trenger oversikt over som AI-løsningsleder.

---

## Potensialet

Arkitekturen er ikke låst til ett fagfelt. Det som i dag leser AI-blogger kan like gjerne settes til å følge bransjenyhetsbrev, interne kunnskapskilder, konkurranserapporter eller juridiske endringer. Personaliseringen vokser frem gjennom bruk, ikke gjennom konfigurasjon.

---

## Hva er bygget hittil

| Modul | Hva den gjør | Status |
|---|---|---|
| **RSS-innhenter** | Henter artikler fra RSS- og Atom-strømmer med datointervall og duplikatsjekk | Ferdig |
| **Vault-skriver** | Lagrer artikler som Markdown-filer med bilder i Obsidian-vault og registrerer dem i SQLite | Ferdig |
| **Nettleserklipper** | Lagrer enkeltsider manuelt via Obsidian Web Clipper med ett klikk | Ferdig |
| **Substack og nettskraping** | Henter Substack-nyhetsbrev og nettsider uten RSS-strøm | Planlagt A4 |
| **YouTube og podkast** | Transkriberer video og lyd lokalt med Whisper | Planlagt A6 |
| **Sammendragsmodul** | Norskspråklige sammendrag via Claude med regulatorisk kontekst | Planlagt A2 |
| **Vurderingsapp** | Streamlit-app der du godkjenner eller avviser sammendrag med tekst eller tale | Planlagt A2 |
| **E-postdigest** | Daglig e-post med sammendrag gruppert per kilde | Planlagt A5 |
| **LLM-dommer** | Automatisk kvalitetsvurdering av sammendrag basert på dine egne vurderinger | Planlagt B |
| **Semantisk søk** | Still spørsmål til arkivet og få svar med kildehenvisninger | Planlagt C |
| **Analysemodul** | Rapporter om innhentingskvalitet, kostnader og trender over tid | Planlagt D |

---

## Slik er det bygget

### Spesifikasjoner før kode

Prosjektet startet med tre levende spesifikasjonsdokumenter: `visjon.md`, `teknologi.md` og `veikart.md`. De er skrevet for å være forståelige både for deg uten teknisk bakgrunn og for en utvikler som skal overta eller utvide systemet. Forretningsbegrunnelse og tekniske valg lever i samme dokument.

### Evaluering som arbeidsform

Hvert lag i systemet evalueres systematisk. Tilnærmingen følger Paul Iusztins serie *AI Evals & Observability* fra Decoding AI (2026): start med menneskelig vurdering, bygg et evalueringssett, tren en automatisk dommer på dine egne preferanser.

### Tester underveis

Enhetstester skrives parallelt med hver modul. Regresjonstestsettet vokser automatisk etter hvert som vurderinger akkumuleres.

---

## Teknologi

Python, Claude API fra Anthropic, SQLite, Obsidian-vault, Opik, Streamlit, Whisper, uv, pytest.

---

## Prosjektdokumenter

| Dokument | Formål |
|---|---|
| [`visjon.md`](./visjon.md) | Hva systemet gjør, hvem det er for og hvilke prinsipper som styrer valgene |
| [`teknologi.md`](./teknologi.md) | Teknologivalg, arkitektur og testfilosofi |
| [`veikart.md`](./veikart.md) | Implementasjonssekvens med avkrysning per modul |

---

## Status

**A0 (fundament), A0b (manuell innhenting) og A1 (RSS-innhenting) er fullført.**

Systemet henter i dag artikler automatisk fra RSS-kilder, lagrer dem i Obsidian-vault og SQLite, og deduper mot tidligere innhenting. Neste steg er sammendragsmodulen (A2).

---

## Forfatter

Bygget av [Audun Klarholm Nilsen](https://www.linkedin.com/in/audunklarholm/), finans- og AI-profesjonell med bakgrunn som business controller og dataingeniør, grunnlegger av Prosessflyt.
