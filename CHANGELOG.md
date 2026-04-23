# Endringslogg

Alle merkbare endringer i dette prosjektet dokumenteres her.

Format følger [Keep a Changelog](https://keepachangelog.com/no/1.1.0/).
Versjonering følger [Semantic Versioning](https://semver.org/).

Enumverdier for `komponent`-feltet: `sammendrag`, `dommer_validering`, `rag_gjenfinning`, `rag_generering`.

---

## [Uutgitt]

### Planlagte implementeringer

#### A1 RSS-innhenting — FULLFØRT

##### Lagt til
- `src/intelligence_monitor/innhenter/rss.py` — RSS/Atom-innhenting med feedparser, datointervall-filtrering, URL-basert dedup og kilde-nivå feilhåndtering *(2026-04-23 11:40)*
- `src/intelligence_monitor/innhenter/kjører.py` — minimal innhentings-shell; kaller rss.innhent_alle() med logging; `make innhent` fungerer fra dag én *(2026-04-23 11:40)*
- `tester/test_rss.py` — 6 enhetstester for intervall- og dedup-logikk *(2026-04-23 11:40)*
- `specs/features/2026-04-23-a1-rss-innhenting/` — plan.md, requirements.md, validation.md *(2026-04-23 11:40)*

##### Endret
- `src/intelligence_monitor/db/skjema.sql` — ny `sist_feil_tidsstempel TEXT` og `sist_feil_melding TEXT` på `kilder`-tabellen *(2026-04-23 11:40)*
- `src/intelligence_monitor/db/init.py` — idempotent ALTER TABLE for de nye feilfeltene *(2026-04-23 11:40)*
- `konfig/kilder.yaml` — erstatter utdaterte anthropic/langchain-URL-er med huggingface-blogg og langchain.com/blog/rss.xml *(2026-04-23 11:40)*

---

#### Veikart — kvalitative beskrivelser

##### Endret
- `specs/veikart.md` — lagt til innledende kvalitativ beskrivelse for alle faser (A–D) og alle steg (A0–D3); gir ikke-tekniske og tekniske lesere raskt innsikt i hva som implementeres og hvorfor *(2026-04-23 10:30)*

---

#### A0b Obsidian Web Clipper — FULLFØRT

##### Lagt til
- `notebooks/datakontroll.ipynb` — Jupyter-notebook for sanity-sjekk av siste N artikler fra SQLite og vault *(2026-04-23 00:21)*
- `specs/features/2026-04-22-a0b-obsidian-web-clipper/VERIFICATION.md` — verifikasjonsrapport, 6/6 tester grønne, røyktest bestått med 3 artikler *(2026-04-23 00:44)*

##### Endret
- `specs/features/2026-04-22-a0b-obsidian-web-clipper/plan.md` — justert frontmatter-spec: tittel som H1 (ikke frontmatter-felt), kilde_id kun i SQLite *(2026-04-23 00:44)*
- `specs/veikart.md` — røyktest krysset av under A0b *(2026-04-23 00:44)*

---

### Ad hoc-endringer

#### Røyktesting: Web Clipper frontmatter og vault-sti

##### Endret
- `src/intelligence_monitor/innhenter/obsidian_vakt.py` — aksepterer `source`-felt som fallback for `url` i frontmatter (Web Clipper bruker `source`) *(2026-04-23 00:22)*
- `.env` — `VAULT_ROT` oppdatert til `OBSIDIAN\monitor-evals` (faktisk vault-mappe) *(2026-04-23 00:19)*

---

#### Røyktest-klargjøring: env var-mismatch

##### Endret
- `.env.mal` — omdøpte `VAULT_STI=` → `VAULT_ROT=` for å matche `os.getenv("VAULT_ROT")` i `obsidian_vakt.py` *(2026-04-22 23:59)*
- `.env` — omdøpte `VAULT_STI=` → `VAULT_ROT=` (behold eksisterende verdi) *(2026-04-22 23:59)*

---

### Planlagte implementeringer

#### A0b Obsidian Web Clipper — Gruppe 3 og 4: obsidian_vakt.py og enhetstester
*Plan: `specs/features/2026-04-22-a0b-obsidian-web-clipper/plan.md`*

##### Lagt til
- `src/intelligence_monitor/innhenter/obsidian_vakt.py` — watchdog-vakt på `vault/innboks/`: frontmatter-parsing, dedup-sjekk, kall til `vault_skriver`, flytting til `vault/behandlet/`, feilisolering per fil *(2026-04-22 23:55)*
- `tester/test_vault_skriver.py` — fire enhetstester: filnavn/frontmatter, UUID-konsistens, ugyldig bilde-URL, rollback *(2026-04-22 23:55)*
- `tester/konfig/fixtures.py` — delte pytest-fixtures: midlertidig vault-mappe og SQLite-database med fase A-skjema *(2026-04-22 23:55)*

##### Endret
- `specs/features/2026-04-22-a0b-obsidian-web-clipper/plan.md` — alle fire grupper krysset av *(2026-04-22 23:55)*
- `specs/veikart.md` — obsidian_vakt.py og alle fire enhetstester krysset av under A0b *(2026-04-22 23:55)*

---

#### A0b Obsidian Web Clipper — Gruppe 2: vault_skriver.py
*Plan: `specs/features/2026-04-22-a0b-obsidian-web-clipper/plan.md`*

##### Lagt til
- `src/intelligence_monitor/innhenter/vault_skriver.py` — atomisk lagring til vault og SQLite: UUID-generering, bildehåndtering (httpx), YAML-frontmatter, rollback ved SQLite-feil *(2026-04-22 23:30)*
- `konfig/kilder.yaml`: `manuell-klipp`-kilde med `url: lokal` som plassholder *(2026-04-22 23:30)*

##### Endret
- `specs/features/2026-04-22-a0b-obsidian-web-clipper/requirements.md` — to nye beslutninger: bildehåndtering i A0b og `manuell-klipp`-kilde med plassholder-URL *(2026-04-22 23:30)*
- `specs/features/2026-04-22-a0b-obsidian-web-clipper/validation.md` — røyktest utvidet med bildeverifisering (nedlasting til `vault/ressurser/bilder/` + relativ sti i markdown) *(2026-04-22 23:30)*

---

#### A0b Obsidian Web Clipper — Feature-spesifikasjon
*Plan: `specs/features/2026-04-22-a0b-obsidian-web-clipper/plan.md`*

##### Lagt til
- `specs/features/2026-04-22-a0b-obsidian-web-clipper/plan.md` — 4 oppgavegrupper: Web Clipper-konfig, vault_skriver.py, obsidian_vakt.py, enhetstester *(2026-04-22 23:12)*
- `specs/features/2026-04-22-a0b-obsidian-web-clipper/requirements.md` — scope, beslutninger (UUID-prefix filnavn, stille dedup, ingen datointervall-sjekk for manuell klipping), kontekst og avhengigheter *(2026-04-22 23:12)*
- `specs/features/2026-04-22-a0b-obsidian-web-clipper/validation.md` — merge-kriterier: 4 enhetstester + røyktest (1 klipp, SQLite-verifisering, dedup-verifisering) *(2026-04-22 23:12)*

---

### Ad hoc-endringer

#### Ad hoc: A0b Gruppe 1 — Obsidian Web Clipper installert manuelt
*Manuell brukeroppgave fullført*

##### Endret
- `specs/veikart.md`: Web Clipper-installasjons- og vault_skriver.py-punktene krysset av under A0b *(2026-04-22 23:45)*

---

#### Ad hoc: veikart.md — kryss av alle A0-punkter
*Forespørsel utenom plan — konsistens etter merge*

##### Endret
- `specs/veikart.md`: alle 14 implementerings- og testpunkter under A0 krysset av *(2026-04-22 17:30)*

---

#### Ad hoc: A0 Fundament — validering og klargjøring for merge
*Forespørsel utenom plan — kvalitetssikring*

##### Endret
- `specs/features/2026-04-21-a0-fundament/validation.md`: alle obligatoriske punkter krysset av — røyktester, struktur og manuell gjennomgang verifisert *(2026-04-22 17:00)*

---

#### Ad hoc: plan.md — del opp gruppe 5 i to grupper
*Forespørsel utenom plan — strukturforbedring*

##### Endret
- `specs/features/2026-04-21-a0-fundament/plan.md`: Gruppe 5 delt i to — Opik-konfigurasjon (gruppe 5) og Regulatorisk kontekst (ny gruppe 6). Gammel gruppe 6 (Enhetstester) renummerert til 7. Rekkefølgeseksjon oppdatert. *(2026-04-22 15:34)*

---

#### Ad hoc: Kodekonvensjoner og plan.md-forbedringer
*Forespørsler utenom plan — konvensjoner og dokumentasjonsrydding*

##### Lagt til
- `regresjon`-target i `Makefile` dokumentert som bevisst fase A-placeholder — full implementasjon (LLM-dommer + sammenligning mot domeneekspert-score) er fase B-leverabel *(2026-04-21 22:03)*
- Kodekonvensjon for docstrings (Google-stil) og inline-kommentarer dokumentert i `specs/teknologi.md` *(2026-04-21 22:09)*
- Konvensjon for beskrivende innledning per oppgavegruppe i `plan.md`-dokumenter dokumentert i `specs/teknologi.md` *(2026-04-21 22:16)*
- Beskrivende innledning lagt til alle 6 oppgavegrupper i `specs/features/2026-04-21-a0-fundament/plan.md` *(2026-04-21 22:16)*
- Beskrivende kommentarer i `.gitignore` for vault-regler — forklarer hva som ignoreres og hva som bevares *(2026-04-22 11:57)*
- Konvensjon for tidsstempel på CHANGELOG-oppføringer (`*(YYYY-MM-DD HH:MM)*`) dokumentert i `specs/teknologi.md` *(2026-04-22 12:05)*
- Konvensjon for beskrivende kommentarer i konfigurasjonsfiler (`.gitignore`, `Makefile`, YAML, `.env.mal`) dokumentert i `specs/teknologi.md` *(2026-04-22 12:05)*
- Overskrifter per oppdateringsgruppe lagt til i `CHANGELOG.md` — sporbar tilbake til plan eller ad hoc-forespørsel *(2026-04-22 12:25)*

---

### Planlagte implementeringer

#### A0 Fundament — Opik-konfigurasjon
*Plan: `specs/features/2026-04-21-a0-fundament/plan.md` — oppgavegruppe 5*

##### Lagt til
- `src/intelligence_monitor/opik_konfig.py` — `konfigurer_opik()` henter `OPIK_API_NØKKEL` og `OPIK_PROSJEKTNAVN` fra miljø og kaller `opik.configure()`. Manglende nøkkel eller SDK-feil propagerer og stopper oppstart — Opik er obligatorisk *(2026-04-22 15:45)*
- `src/intelligence_monitor/db/init.py` utvidet: importerer og kaller `konfigurer_opik()` øverst i `initialiser()` — Opik konfigureres før databasetilkobling *(2026-04-22 15:45)*
- `load_dotenv()` lagt til i `db/init.py` slik at `.env`-fil leses ved kjøring som modul *(2026-04-22 16:22)*
- `OPIK_ARBEIDSROM`-variabel lagt til `.env` og sendt som `workspace`-parameter til `opik.configure()` — unngår interaktivt arbeidsrom-spørsmål ved oppstart *(2026-04-22 16:22)*
- Opik API-nøkkel verifisert: `python -m intelligence_monitor.db.init` returnerer exit code 0 og logger konfigurasjon mot `intelligence-monitor`-prosjektet *(2026-04-22 16:22)*

---

#### A0 Fundament — Regulatorisk kontekst
*Plan: `specs/features/2026-04-21-a0-fundament/plan.md` — oppgavegruppe 6*

##### Lagt til
- `specs/regulatorisk-kontekst.md` — strukturert oppslagsverk for summarizer-prompten med fem seksjoner: EU AI Act (risikoklassifisering, GPAI, håndhevelse), NIS2 (scope, varslingsplikter 24t/72t/1mnd, leverandørkjede), ISO 42001 (AIMS, risikovurdering, sertifisering), Datatilsynet (DPIA, GDPR-krysningspunkter, dataoverføring), NSM grunnprinsipper (leverandørkjede-sikkerhet, tilgangsstyring, hendelseshåndtering) *(2026-04-22 15:57)*
- `specs/features/2026-04-21-a0-fundament/validation.md` oppdatert: valideringsbullet for `regulatorisk-kontekst.md` inkluderer nå Datatilsynet og NSM grunnprinsipper *(2026-04-22 15:57)*
- `specs/features/2026-04-21-a0-fundament/plan.md` oppdatert: oppgavegruppe 6 nevner Datatilsynet og NSM eksplisitt *(2026-04-22 16:12)*

---

#### A0 Fundament — Enhetstester
*Plan: `specs/features/2026-04-21-a0-fundament/plan.md` — oppgavegruppe 7*

##### Lagt til
- `tester/test_db_init.py` — to enhetstester for `db/init.py`: `test_idempotens` (kjør `initialiser()` to ganger, verifiser alle fire tabeller og at radantall ikke dobbles) og `test_yaml_synk` (legg til/fjern kilde via YAML, verifiser `aktiv`-flagg). Opik og `_YAML_STI` mocket for å kjøre uten ekstern infrastruktur *(2026-04-22 16:11)*

---

#### A0 Fundament — Databasefundament
*Plan: `specs/features/2026-04-21-a0-fundament/plan.md` — oppgavegruppe 4*

##### Lagt til
- `src/intelligence_monitor/db/skjema.sql` — fire fase A-tabeller (`kilder`, `elementer`, `sammendrag`, `evalueringstriplets`) med CHECK-constraint på `komponent`-feltet *(2026-04-22 12:30)*
- `src/intelligence_monitor/db/init.py` — idempotent tabellopprettelse og YAML→SQLite-synk for `kilder`-tabellen *(2026-04-22 12:30)*
- `data/.gitkeep` — sporer `data/`-mappe for databasefil *(2026-04-22 12:30)*
- `DATABASE_STI=data/monitor.db` lagt til `.env.mal`, `.env` og `specs/teknologi.md` *(2026-04-22 12:30)*
- Beslutning om databaseplassering (`data/monitor.db`, `DATABASE_STI` i `.env`) dokumentert i `requirements.md` og `validation.md` *(2026-04-22 12:20)*

---

#### A0 Fundament — Vault-mappestruktur
*Plan: `specs/features/2026-04-21-a0-fundament/plan.md` — oppgavegruppe 3*

##### Lagt til
- Vault-mappestruktur opprettet: `vault/artikler/`, `vault/ressurser/bilder/`, `vault/innboks/`, `vault/behandlet/` — hver med `.gitkeep` for Git-sporing *(2026-04-22 11:51)*
- `.gitignore` justert: `vault/**` ignorerer innhold, `!vault/*/`, `!vault/*/*/` og `!vault/**/.gitkeep` bevarer mappestruktur *(2026-04-22 11:51)*

---

#### A0 Fundament — Oppsett og konfigurasjon
*Plan: `specs/features/2026-04-21-a0-fundament/plan.md` — oppgavegruppe 1 og 2*

##### Lagt til
- `.gitignore` for `.env`, `*.db`, `__pycache__`, `.venv` *(2026-04-21 20:13)*
- `pyproject.toml` med alle fase A–D-avhengigheter og dev-gruppe (pytest, pytest-mock) *(2026-04-21 20:24)*
- Python 3.11 virtuelt miljø via `uv venv`, avhengigheter installert og verifisert med `uv pip install -e ".[dev]"` *(2026-04-21 20:24)*
- Feature-spesifikasjon A0 — Fundament: `specs/features/2026-04-21-a0-fundament/` med `plan.md`, `requirements.md`, `validation.md` *(2026-04-21 20:32)*
- `src/intelligence_monitor/__init__.py` — opprettet Python-pakke for kjernemodulen *(2026-04-21 21:09)*
- Undermapper `innhenter/`, `sammendrag/`, `evaluering/`, `rag/`, `prosessering/`, `levering/`, `analyse/`, `db/` under `src/intelligence_monitor/` — hver med tom `__init__.py` *(2026-04-21 21:18)*
- `src/intelligence_monitor/sammendrag/prompts/.gitkeep` — bevarer struktur for prompt-tekstfiler *(2026-04-21 21:18)*
- `tester/__init__.py` og `tester/konfig/__init__.py` — pytest-pakkestruktur *(2026-04-21 21:18)*
- `Makefile` med 10 targets (`innhent`, `sammendrag`, `review`, `synk`, `regresjon`, `rapport`, `test`, `test-enkelt`, `alle`, `produksjon`) + `help`-target, med utfyllende kommentarer per target som forklarer funksjon, systemkonsekvenser og dataflyt *(2026-04-21 21:43)*
- `.env.mal` med komplett feltsett (14 variabler) fra specs/teknologi.md *(2026-04-21 21:43)*
- `konfig/kilder.yaml` med 5 startkilder (simon-willison, anthropic-blogg, langchain-blogg, decoding-ai, sebastian-raschka) *(2026-04-21 21:43)*

---

## [0.0.1] — 2026-04-21

### Lagt til
- Spesifikasjonsdokumenter: `specs/visjon.md`, `specs/teknologi.md`, `specs/veikart.md`, `specs/les-meg.md`
