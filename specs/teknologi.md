# Teknologi

*Dette dokumentet beskriver hvilke teknologier systemet er bygget på, hvorfor hvert valg er tatt, og hvordan komponentene henger sammen.*

---

## Overordnet arkitektur

Fire logiske lag:

1. **Innhentingslaget** — henter råinnhold, lagrer i vault og SQLite.
2. **Prosesseringslaget** — leser fra vault, produserer sammendrag i SQLite.
3. **Evalueringslaget** — akkumulerer triplets i SQLite. Gjenbrukes i alle faser.
4. **Leveringslaget** — daglig e-postdigest og/eller Markdown til vault.

Fase B: **dommerlag**. Fase C: **søkelag**. Fase D: **analyselag**.

---

## Programmeringsspråk og avhengighetshåndtering

**Python 3.11+** er standardspråket for AI- og maskinlæringsarbeid.

**uv** håndterer virtuelt miljø og avhengigheter. Raskere enn pip, produserer `uv.lock` for reproduserbare miljøer, og er gjeldende beste praksis i Python-prosjekter.

```bash
uv venv
uv pip install -e .   # Installer pakken i editerbart modus
```

**Docker** vurderes fra fase D for automatisering og skyflytting. Ikke nødvendig i fase A–C der alt kjøres manuelt via Makefile.

---

## src/-layout

Alle kildemoduler samles under `src/intelligence_monitor/`. Dette er gjeldende beste praksis for Python-pakker fordi det skiller kildekode fra konfigurasjonsfiler, gjør pakken installerbar med `uv pip install -e .`, og sikrer at tester alltid kjører mot den installerte pakken — ikke mot løse filer i rotmappen.

---

## Ansvarsfordeling mellom lagringslagene

| Lag | Eier | Eier ikke |
|---|---|---|
| **Obsidian-vault** | Artikkeltekst, bilder, daglig digest (valgfritt) | Metadata, sammendrag, vektorer |
| **SQLite** | Metadata, sammendrag, triplets, vektorer | Artikkeltekst, bilder, spor |
| **Opik** | API-spor, eksperimenter, synkronisert kopi av triplets | Alt annet |

**SQLite er alltid kilden til sannhet.** Opik-kopi er for eksperimentsporing — ved konflikt vinner SQLite.

---

## Databasetabeller

| Tabell | Innhold |
|---|---|
| `kilder` | Kilder med URL, type, aktivt-flagg, emnemerker, `hent_fra`, `hent_til` |
| `elementer` | Metadata per artikkel inkl. `vault_sti` |
| `sammendrag` | Sammendrag koblet til `element_id` og `prompt_versjon` |
| `evalueringstriplets` | *(element_id, resultat_id, godkjent, kommentar, komponent, er_regresjonstest, tidsstempel)* |
| `vektorer` | Vektorer per tekstdel (fase C) |
| `rag_spor` | Q/C/A-triplets (fase C) |

`komponent`-feltet bruker norske enumverdier: `sammendrag`, `dommer_validering`, `rag_gjenfinning`, `rag_generering`.

`er_regresjonstest` (boolsk) settes automatisk til `true` når domenekspert og LLM-dommer er enige.

`prompt_versjon` lagrer versjonsstreng per sammendrag (f.eks. `v1`).

---

## Datointervall for innhenting

Hver kilde har et konfigurerbart datointervall i `konfig/kilder.yaml`:

```yaml
- navn: Simon Willison
  url: https://simonwillison.net/atom/everything/
  type: rss
  aktiv: true
  emnemerker: [ai, tools]
  hent_fra: 2025-04-01      # Ikke hent artikler eldre enn denne datoen
  hent_til:                 # Tom = ingen øvre grense (hent frem til nå)
```

To globale env-variabler kan overstyre alle kilders intervall midlertidig — nyttig under oppstart og testing:

```
HENT_FRA=2025-04-15         # Overstyr hent_fra for alle kilder
HENT_TIL=2025-04-21         # Overstyr hent_til for alle kilder
```

Innhentingslogikken i `rss.py` og `nett.py` følger denne sekvensen for hvert element:

1. Les `hent_fra` og `hent_til` per kilde (med env-override hvis satt)
2. Sjekk publiseringsdato mot intervallet — utenfor intervall → hopp over stille
3. Innenfor intervall → kjør dedup-sjekk på `guid`/`url` mot `elementer`-tabellen
4. Kjent fra før → hopp over stille
5. Ny → lagre

Dette sikrer at systemet aldri dupliserer elementer selv om du utvider datointervallet i en senere kjøring — dedup-laget håndterer det uavhengig av dato.

---

## Idempotent tabellopprettelse

`db/init.py` bruker `CREATE TABLE IF NOT EXISTS` for alle tabeller. Skriptet kan kjøres ti ganger uten å slette data eller gi feil — samme resultat hver gang.

---

## Kildesynkronisering: YAML til SQLite

`konfig/kilder.yaml` er det deklarative utgangspunktet. `db/init.py` synkroniserer YAML til `kilder`-tabellen ved oppstart, inkludert `hent_fra` og `hent_til` per kilde.

---

## Filskriving og datakonsistens

`innhenter/vault_skriver.py` følger alltid denne rekkefølgen:

1. Generer UUID lokalt som `element_id`
2. Skriv Markdown-fil med `element_id` i YAML-frontmatter
3. Skriv SQLite-rad med samme `element_id`
4. Ved feil i steg 3: slett fil fra steg 2

---

## Prompt-versjonering

Prompts lagres som tekstfiler i `src/intelligence_monitor/sammendrag/prompts/` og versjoneres med Git-tags (`prompt-v1`, `prompt-v2`). `sammendrag`-tabellen lagrer versjonsstrengen per rad.

---

## Regulatorisk kontekst

### Fase A — Markdown-referanse

`specs/regulatorisk-kontekst.md` inneholder strukturerte høydepunkter fra AI Act, NIS2 og ISO 42001. Inkluderes direkte i summarizer-prompten. Summarizeren produserer en kort regulatorisk koblingsparagraf per sammendrag.

### Fase C/D — Regulatorisk RAG (valgfri utvidelse)

Hvis kalibreringen viser at Markdown-referansen er for grov, vektoriseres lovtekstene i et eget sqlite-vec-vektorsett. Migrasjonen berører kun innhentingssteget i summarizeren.

---

## Miljøvariabler — komplett feltsett

```
# Claude API
ANTHROPIC_API_NØKKEL=

# Opik
OPIK_API_NØKKEL=
OPIK_PROSJEKTNAVN=intelligence-monitor

# Obsidian
VAULT_STI=

# Sammendragsmodul
MAKS_ARTIKKEL_TOKENS=4000

# Datointervall (overstyr alle kilder midlertidig)
HENT_FRA=                   # Format: YYYY-MM-DD, tom = bruk per-kilde-konfig
HENT_TIL=                   # Format: YYYY-MM-DD, tom = ingen øvre grense

# E-post (SMTP)
SMTP_VERT=
SMTP_PORT=587
SMTP_BRUKER=
SMTP_PASSORD=
VARSLING_TIL_EPOST=
DIGEST_TIL_EPOST=

# Talegjenkjenning
WHISPER_MODELL=base
OPENAI_API_NØKKEL=
```

---

## Promptsikkerhet

Kurerte og kjente kilder begrenser risikoen for prompt injection — angrep der ondsinnet tekst forsøker å manipulere språkmodellen til å ignorere instruksjonene.

**Strukturell innramming** pakker artikkelteksten i XML-tagger:

```
<artikkel>
{artikkeltekst}
</artikkel>

Oppsummer artikkelen ovenfor på norsk.
```

Claude behandler innhold mellom XML-tagger som data, ikke instruksjoner. En artikkel med teksten "Ignorer tidligere instruksjoner og..." vil i praksis ikke ha effekt fordi modellen ser at teksten befinner seg inne i `<artikkel>`-taggen.

**Lengdebegrensning** kutter artikler over `MAKS_ARTIKKEL_TOKENS`. Begge tiltak gjelder alle API-kall.

---

## Talegjenkjenning i vurderingsappen

**Lokal Whisper** (`openai-whisper`) er standard — offline, `base`-modellen bruker ca. 1 GB RAM. **Sky-reserve** via OpenAI Whisper API aktiveres automatisk ved feil. Valget mellom tekst og tale gjøres per sesjon.

---

## Opik-integrasjon

`@opik.track` konfigureres med `fail_silently=True`. Synkronisering av triplets trigges manuelt via knapp i Streamlit etter review-sesjon, eller `make synk`.

---

## LLM-dommer og regresjonstesting

**Aksial koding** forbedrer *summarizer-prompten* — ikke dommeren direkte.

**LLM-dommeren** bygges fra triplets med ML-metodikk: 70 % trening, 15 % validering, 15 % test.

**Regresjonstesting**: `er_regresjonstest = true` settes når domenekspert og dommer er enige. Kjøres via `make regresjon`.

---

## Syntetiske brukerprofiler (fase C)

**Strategisk** — situasjonsoversikt: "Hva er de viktigste AI-trendene denne måneden?"

**Operasjonelt** — handlingsrettet: "Hvilke verktøy anbefales for RAG-implementering?"

**Teknisk** — presise detaljer: "Hva er forskjellen mellom sqlite-vec og Qdrant?"

---

## Analysemodul

`analyse/rapport.py` kombinerer Opik SDK og SQLite for programmatisk uttrekk. Fire rapporttyper: ukentlig drift, kalibrering, dommerytelse, RAG-ytelse.

---

## Startkilder

| Kilde | Type | URL |
|---|---|---|
| Simon Willison | RSS | simonwillison.net/atom/everything/ |
| Anthropic-bloggen | RSS | anthropic.com/rss.xml |
| LangChain-bloggen | RSS | blog.langchain.dev/rss/ |
| Paul Iusztin (Decoding AI) | Substack | decodingai.com |
| Sebastian Raschka | Substack | magazine.sebastianraschka.com |

---

## Testfilosofi

Enhetstester skrives parallelt med hver modul. **Pytest** med fixtures for midlertidig SQLite og vault. Minst én positiv og én negativ test per modul. Live API-kall dekkes av røyktester.

---

## Kodekonvensjoner

### Docstrings
Alle klasser og funksjoner skal ha en Google-stil docstring:

```python
def hent_artikler(kilde_id: int, grense: int = 50) -> list[dict]:
    """Henter uprosesserte artikler for én kilde fra SQLite.

    Args:
        kilde_id: Primærnøkkel i `kilder`-tabellen.
        grense: Maks antall rader som returneres.

    Returns:
        Liste med dicts — én per artikkel, med feltene `guid`, `url`, `tittel`.

    Raises:
        sqlite3.OperationalError: Hvis databaseforbindelsen feiler.
    """
```

Minimumskrav:
- **Klasser**: én setning som forklarer ansvar.
- **Funksjoner/metoder**: én setning + `Args` og `Returns` hvis signaturen ikke er
  selvforklarende. `Raises` legges til kun hvis funksjonen kan kaste unntak som
  kalleren forventes å håndtere.
- Privat hjelpefunksjon med triviell logikk: kort én-linje docstring er tilstrekkelig.

### Inline-kommentarer
Legg til `#`-kommentar der logikken ikke er umiddelbart lesbar:
- Ikke-åpenbare konstanter eller beregnede verdier.
- Valgbegrunnelser (f.eks. `# CREATE TABLE IF NOT EXISTS — idempotent`).
- Komplekse betingelser eller regulæruttrykksmønstre.

Unngå kommentarer som bare gjentar koden (`artikkel_id = 1  # setter artikkel_id til 1`).

### Planleggingsdokumenter (plan.md)
Hvert `plan.md` under `specs/features/` skal ha én beskrivende innledning per oppgavegruppe.
Innledningen plasseres mellom gruppeoverskriften og sjekklisten og skal:
- Forklare **hva** gruppen produserer og **hvorfor** det er nødvendig på dette tidspunktet.
- Være forståelig for både ikke-tekniske og tekniske lesere — ingen kodesnutter.
- Holde seg til 2–4 setninger.

---

## Kalibreringsterser

| Terskel | Verdi |
|---|---|
| Godkjenningsrate | ≥ 90 % |
| Avviste triplets før fase B | ≥ 50 |
| Totalt merkede triplets før fase B | ≥ 200 |
| Sann-positiv rate (godkjente domenekspert → godkjent av dommer) | ≥ 85 % |
| Sann-negativ rate (avviste av domenekspert → avvist av dommer) | ≥ 75 % |

---

## Arbeidsflyt for feature-utvikling

```
specs/
├── visjon.md
├── teknologi.md
├── veikart.md
├── les-meg.md
├── regulatorisk-kontekst.md
└── features/
    ├── 2025-04-21-rss-innhenting/
    │   ├── plan.md
    │   ├── requirements.md
    │   └── validation.md
    └── ...
```

**`plan.md`** — nummererte oppgavegrupper, Makefile-targets og testfiler som opprettes.

**`requirements.md`** — scope, beslutninger, kontekst. Refererer til `visjon.md` og `teknologi.md`.

**`validation.md`** — hva som må være på plass for merge: tester, røyktest, manuelle verifiseringer.


---

## Git-arbeidsflyt og changelog

`CHANGELOG.md` oppdateres ved **hver commit og merge** — en commit uten changelog-oppdatering er ufullstendig. Følger [Keep a Changelog](https://keepachangelog.com) med seksjonene **Lagt til**, **Endret**, **Fikset**, **Fjernet**.

Commit-konvensjon ([Conventional Commits](https://www.conventionalcommits.org)):
```
feat(rss): legg til datointervall-filtrering
fix(vault): håndter ugyldig bilde-URL uten krasj
test(rss): test at elementer utenfor intervall hoppes over
docs(changelog): oppdater for A1
chore(prompt): bump til v2, tag prompt-v2
```

Branch-strategi: `feature/YYYY-MM-DD-navn` og `fix/YYYY-MM-DD-navn`. Merge til `main` når `validation.md` er fullstendig krysset av.

Versjonering: Fase A → 0.1.0, Fase B → 0.2.0, Fase C → 0.3.0, Fase D → 1.0.0.

---

## Makefile

```makefile
innhent:
	python -m intelligence_monitor.innhenter.kjører

sammendrag:
	python -m intelligence_monitor.sammendrag.lag_sammendrag

review:
	streamlit run src/intelligence_monitor/evaluering/vurderingsapp.py

synk:
	python -m intelligence_monitor.evaluering.opik_synk

regresjon:
	python -m intelligence_monitor.evaluering.regresjonstest

rapport:
	python -m intelligence_monitor.analyse.rapport

test:
	pytest tester/ -v

test-enkelt:
	pytest tester/$(fil) -v

alle:
	make innhent && make sammendrag

produksjon:
	make innhent && make sammendrag && make rapport
```

---

## Mappestruktur

```
intelligence-monitor/
├── specs/
│   ├── visjon.md
│   ├── teknologi.md
│   ├── veikart.md
│   ├── les-meg.md
│   ├── regulatorisk-kontekst.md
│   └── features/
├── src/
│   └── intelligence_monitor/
│       ├── innhenter/
│       │   ├── rss.py
│       │   ├── nett.py
│       │   ├── youtube.py
│       │   ├── obsidian_vakt.py
│       │   ├── vault_skriver.py
│       │   └── kjører.py
│       ├── sammendrag/
│       │   ├── prompts/
│       │   │   └── v1.txt
│       │   └── lag_sammendrag.py
│       ├── evaluering/
│       │   ├── vurderingsapp.py
│       │   ├── triplet_lager.py
│       │   ├── opik_synk.py
│       │   ├── rammeverk.py
│       │   ├── aksial_koding.py
│       │   ├── llm_dommer.py
│       │   ├── dommer_validator.py
│       │   ├── regresjonstest.py
│       │   ├── syntetisk_gen.py
│       │   └── dommer_rag.py
│       ├── rag/
│       │   ├── innhent.py
│       │   ├── søk.py
│       │   └── generer.py
│       ├── prosessering/
│       │   └── vektoriser.py
│       ├── levering/
│       │   └── epost.py
│       ├── analyse/
│       │   ├── rapport.py
│       │   ├── opik_henter.py
│       │   └── sqlite_henter.py
│       └── db/
│           ├── skjema.sql
│           └── init.py
├── tester/
│   ├── konfig/
│   │   └── fixtures.py
│   ├── test_db_init.py
│   ├── test_vault_skriver.py
│   ├── test_rss.py
│   ├── test_lag_sammendrag.py
│   ├── test_triplet_lager.py
│   ├── test_opik_synk.py
│   ├── test_nett.py
│   ├── test_kjører.py
│   ├── test_epost.py
│   ├── test_youtube.py
│   ├── test_aksial_koding.py
│   ├── test_rammeverk.py
│   ├── test_llm_dommer.py
│   ├── test_dommer_validator.py
│   ├── test_regresjonstest.py
│   ├── test_innhent.py
│   ├── test_søk.py
│   ├── test_generer.py
│   ├── test_syntetisk_gen.py
│   ├── test_dommer_rag.py
│   ├── test_rapport.py
│   ├── test_sqlite_henter.py
│   └── test_opik_henter.py
├── konfig/
│   └── kilder.yaml
├── CHANGELOG.md
├── Makefile
├── .env.mal
├── pyproject.toml
└── uv.lock
```
