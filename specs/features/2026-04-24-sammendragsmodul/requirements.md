# A2a — Krav og beslutninger

*Refererer til `specs/visjon.md` og `specs/teknologi.md`.*

---

## Scope

A2a implementerer kjernen i prosesseringslaget (jf. `teknologi.md` — fire logiske lag): en artikkel leses fra Obsidian-vault, kombineres med regulatorisk kontekst og en versjonert prompt, og sendes til OpenAI (gpt-4.1) for å produsere et norskspråklig sammendrag med en regulatorisk koblingsparagraf. Resultatet lagres i SQLite.

Utenfor scope for A2a:
- Vurderingsapp og triplet-lager (A2b).
- Opik-synkronisering av triplets (A2c).
- Kalibreringsfase (A3).
- Nettskraping og koordinator (A4).

---

## Funksjonelle krav

1. Modulen leser `vault_sti` fra `elementer`-tabellen for hvert element uten eksisterende sammendrag.
2. Artikkelteksten kuttes til `MAKS_ARTIKKEL_TOKENS` tokens før innramming — jf. promptsikkerhet i `teknologi.md`.
3. Artikkelteksten pakkes i XML-tagger (`<artikkel>…</artikkel>`) — standard strukturell innramming for alle API-kall.
4. Hele `specs/regulatorisk-kontekst.md` inkluderes i prompten som oppslagsverk for den regulatoriske koblingsparagrafen.
5. Hvert API-kall dekoreres med `@opik.track` og konfigureres med `fail_silently=True` — jf. Opik-integrasjon i `teknologi.md`.
6. Sammendrag lagres i `sammendrag`-tabellen med `element_id` og `prompt_versjon` (f.eks. `v1`).
7. Manglende vault-fil gir en meningsfull feilmelding — ikke et krasj.

---

## Beslutninger

### OpenAI API-konfigurasjon via .env

Modell, temperature og maks antall output-tokens styres av `.env`-variabler. Dette gjør det mulig å bytte modell eller justere parametere uten kodeendring — nyttig under kalibreringsfasen (A3).

Nye felter som legges til `.env.mal`:

```
# OpenAI
OPENAI_API_NØKKEL=          # API-nøkkel fra platform.openai.com — brukes til sammendrag og Whisper sky-reserve
OPENAI_MODELL=gpt-4.1
MAKS_SAMMENDRAG_TOKENS=1024
TEMPERATURE=0.3
```

`OPENAI_API_NØKKEL` dekker både sammendragsmodulen og Whisper sky-reserve — én nøkkel for begge.

`MAKS_ARTIKKEL_TOKENS` er allerede definert i `.env.mal` fra A0.

### Regulatorisk kontekst — hele filen

Hele `specs/regulatorisk-kontekst.md` inkluderes som råtekst i prompten. Tilnærmingen er enkel å vedlikeholde og gir funksjonaliteten umiddelbart uten ny infrastruktur. Kalibreringsfasen (A3) avgjør om granularitet er nødvendig — i så fall vurderes regulatorisk RAG i fase C/D (jf. `visjon.md` — Fase C/D regulatorisk RAG).

### Prompt-versjonering

`v1.txt` er baseline-prompten. Versjonsstrengen `v1` lagres i `sammendrag`-tabellen per rad. Git-tag `prompt-v1` settes ved commit. Ny versjon ved endring: `v2.txt`, Git-tag `prompt-v2`, oppdatert CHANGELOG — jf. `teknologi.md` — Prompt-versjonering.

### Prosesseringsrekkefølge

Modulen behandler alle elementer uten eksisterende sammendrag i `sammendrag`-tabellen. Ingen prioritering i A2a — alle ubehandlede artikler kjøres i rekkefølge.

---

## Kontekst

- Lagringsfilosofi: Obsidian eier artikkeltekst, SQLite eier sammendrag og metadata — jf. `visjon.md` og `teknologi.md`.
- Evalueringstriplets akkumuleres fra A2b; A2a produserer kun råsammendrag.
- Systemet er ment for manuell kjøring via `make sammendrag` frem til A5 (automatisering).
