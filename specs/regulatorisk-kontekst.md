# Regulatorisk kontekst

Dette dokumentet er et oppslagsverk for summarizer-prompten. For hver artikkel skal
summarizeren vurdere hvilke av disse regelverkene som er relevante og produsere en
regulatorisk koblingsparagraf.

---

## EU AI Act

- **Risikoklassifisering i fire nivåer**: uakseptabel risiko (forbud), høy risiko (strenge krav),
  begrenset risiko (transparenskrav), minimal risiko (ingen særskilte krav)
- **Forbudte praksiser** inkluderer bl.a. sosiale poengsystemer, manipulasjon av sårbare grupper
  og biometrisk sanntidsovervåking på offentlig sted (med snevre unntak)
- **Høyrisiko-systemer** (biometri, kritisk infrastruktur, utdanning, ansettelse, kreditt,
  rettshåndhevelse m.fl.) krever risikovurdering, teknisk dokumentasjon og menneskelig kontroll
- **Loggingskrav (art. 12)**: høyrisiko-systemer skal logge hendelser for å identifisere
  risikosituasjoner og støtte post-market monitoring — kravet gjelder ikke generelt for
  alle systemer som håndterer persondata, og omfatter ikke transaksjonslogging av hva som
  lå i konteksten ved hver enkelt modellkjøring
- **Høyrisiko-klassifisering er triggerkriteriet**: AI Act-krav om logging, dokumentasjon og
  risikovurdering slår inn ved høyrisiko-klassifisering, ikke ved persondata-behandling generelt
- **Spenning mot GDPR**: AI Acts krav om lang oppbevaring av systemlogger kan kollidere med
  GDPRs sletteplikt for persondata — dersom logger inneholder personopplysninger, gjelder GDPR
  fullt ut for lagringen, og virksomheten må håndtere denne spenningen eksplisitt
- **Transparenskrav**: brukere skal informeres om at de interagerer med AI; deepfake-innhold
  skal merkes; generelle AI-modeller (GPAI) med systemisk risiko har egne krav
- **Konformitetsvurdering**: høyrisiko-systemer krever enten intern vurdering eller
  tredjepartsvurdering før markedsintroduksjon, samt EU-registrering
- **GPAI og grunnmodeller**: store treningsberegnede modeller (≥10²³ FLOP) regnes som
  systemisk-risiko og pålegges åpenhet om treningsdata, rød-teaming og hendelsesrapportering
- **Håndhevelse**: nasjonale markedsovervåkningsmyndigheter + European AI Office;
  bøter opp til 35 mill. euro eller 7 % av global omsetning

---

## NIS2-direktivet

- **Scope**: skiller mellom «essensielle» (energi, transport, bank, helse, vann,
  digital infrastruktur, offentlig forvaltning) og «viktige» virksomheter (post, avfall,
  kjemikalier, mat, industri, digitale tjenester) — ulike krav og tilsynsintensitet;
  NIS2 er sektorbasert og funksjonell, ikke teknologispesifikk: direktivet regulerer
  organisasjoner og sektorer, ikke enkeltteknologier eller systemarkitekturer
- **Sikkerhetstiltak**: risikobasert tilnærming med krav om policy for informasjonssikkerhet,
  hendelseshåndtering, forretningskontinuitet, leverandørkjede-sikkerhet og kryptering
- **Varslingsplikter**: tidlig varsling innen **24 timer**, fullstendig hendelsesrapport innen
  **72 timer**, sluttrapport innen **1 måned** — til nasjonal CSIRT og tilsynsmyndighet
- **Leverandørkjede**: virksomheter er ansvarlige for å vurdere cybersikkerhetsrisiko hos
  leverandører og tjenesteleverandører — relevant for AI-as-a-service og skybaserte LLM-er
- **Lederansvar**: styret og toppledelse kan holdes personlig ansvarlig for manglende overholdelse
- **Norsk implementering**: NIS2 implementeres i norsk rett; Nasjonal sikkerhetsmyndighet (NSM)
  er sentral koordinator og tilsynsmyndighet for digital infrastruktur
- **Sanksjoner**: essensielle virksomheter opp til 10 mill. euro eller 2 % av global omsetning;
  viktige virksomheter opp til 7 mill. euro eller 1,4 %

---

## ISO 42001

- **AI Management System (AIMS)**: rammeverk for styring av ansvarlig AI — parallell til
  ISO 27001 for informasjonssikkerhet, men spesifikt for AI-systemer og -prosesser
- **Risikovurdering**: identifisere og håndtere risikoer knyttet til AI-systemers innvirkning
  på mennesker, samfunn og miljø — inkludert skjevheter, uriktige resultater og misbruk
- **Dokumentasjonskrav**: policy for ansvarlig AI, roller og ansvar, treningsdata-beskrivelse,
  testresultater, ytelsesovervåking og hendelseslogg
- **Interessentanalyse**: kartlegge og involvere berørte parter (ansatte, kunder, regulatorer,
  sivilsamfunn) i AIMS-prosessen
- **Kontinuerlig forbedring**: regelmessig intern revisjon og ledelsesgjennomgang;
  systemet skal tilpasses etter hvert som AI-teknologi og -regulering utvikler seg
- **Sertifisering**: frivillig tredjeparts-sertifisering mulig; signaliserer modenhet
  overfor kunder og regulatorer
- **Samspill med andre standarder**: ISO 42001 kan integreres med ISO 27001 (informasjonssikkerhet)
  og ISO 9001 (kvalitetsstyring) i et felles ledelsessystem

---

## Datatilsynet og norsk AI-veiledning

- **Personvernkonsekvensvurdering (DPIA)**: obligatorisk etter GDPR art. 35 ved profilering,
  systematisk overvåking eller behandling av sensitive opplysninger i stor skala —
  AI-systemer utløser ofte DPIA-kravet
- **Datatilsynets AI-veiledere**: Datatilsynet har utgitt veiledere om ansvarlig bruk av AI
  i norske organisasjoner, inkl. krav til åpenhet, formålsbegrensning og dataminimering
- **GDPR-krysningspunkter**: automatiserte beslutninger (art. 22) krever særlig hjemmel og
  gir den registrerte rett til menneskelig overprøving — relevant for AI-baserte vedtak
- **Grunnlag for behandling**: AI-systemer som trener på personopplysninger må ha gyldig
  behandlingsgrunnlag (samtykke, legitim interesse o.l.) og overholde formålsbegrensning
- **Behandlingsprotokoll (art. 30)**: GDPR krever protokoll over behandlingsaktiviteter —
  dette er ikke det samme som transaksjonslogging av enkeltmodellkjøringer; GDPR pålegger
  ikke dokumentasjon av hvilke data som lå i konteksten ved hver inferens
- **Ansvarlighetsprinsippet (art. 5 nr. 2)**: virksomheten skal kunne påvise etterlevelse —
  revisjonsspor som knytter input til output er god praksis og støtter dette prinsippet,
  men tilsynsmyndigheter vurderer selv hva som er tilstrekkelig dokumentasjon; et teknisk
  sporingsopplegg er ikke automatisk juridisk tilstrekkelig
- **Dataoverføring**: bruk av utenlandske AI-tjenester (f.eks. USA-baserte LLM-APIer) krever
  overføringsgrunnlag — standard kontraktsklausuler (SCC) eller tilsvarende
- **Åpenhet og forklarbarhet**: GDPR art. 13–14 krever informasjon om automatisert behandling;
  Datatilsynet forventer at AI-systemer kan forklare grunnlaget for sine beslutninger
- **Sandkasse og dialog**: Datatilsynet tilbyr regulatorisk sandkasse for innovative
  tjenester — relevant for norske AI-prosjekter i tidlig fase

---

## NSM grunnprinsipper for sikkerhet

- **Fire hovedkategorier**: NSMs grunnprinsipper dekker Identifisere og kartlegge,
  Beskytte og opprettholde, Oppdage, og Håndtere og gjenopprette — tilpasset norsk kontekst
- **Leverandørkjede-sikkerhet**: vurdering av tredjeparts programvare og tjenester,
  inkludert AI-APIer og skyplattformer — krav om risikovurdering og kontraktuelle garantier
- **Tilgangsstyring og minste privilegium**: AI-systemer bør operere med minste nødvendige
  tilgang til data og infrastruktur; privilegert tilgang skal loggføres og overvåkes
- **Logging og overvåking**: NSM anbefaler sentralisert logging av hendelser;
  AI-basert analyse av logger er et voksende område, men selve AI-systemet må også logges
- **Hendelseshåndtering**: etablerte prosedyrer for varsling internt og til NSM/NCSC-No
  ved alvorlige cyberhendelser — samsvarer med NIS2-varslingsplikter
- **Sikkerhet i utvikling**: «security by design» i AI-systemer — inkludert
  adversarial robustness, prompt-injeksjonsforsvar og sikker håndtering av API-nøkler
- **Nasjonal sikkerhet**: NSM vurderer risiko ved utenlandsk kontroll over kritisk
  AI-infrastruktur — særlig relevant ved bruk av ikke-europeiske modeller og skyplattformer
