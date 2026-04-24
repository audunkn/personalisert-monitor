# Requirements: A2b — Triplet-lager og vurderingsapp

**Referanser**: `specs/visjon.md § Menneskelig evaluering`; `specs/teknologi.md § Evalueringsinfrastruktur`; `specs/veikart.md § A2b`

## I scope

- `evaluering/triplet_lager.py` — datalag for `evalueringstriplets`-tabellen
- `evaluering/vurderingsapp.py` — Streamlit-app for manuell QA
- `tester/test_triplet_lager.py` — 4 enhetstester

## Utenfor scope

- Opik-synkronisering — A2c
- LLM-dommer — fase B
- RAG-evalueringstriplets — fase C

## Beslutninger

**Ingen UNIQUE-constraint på (element_id, komponent):** Tillater revisjon der samme element vurderes på nytt etter prompt-endring. `er_duplikat()` er en praktisk sjekk i appen, ikke en databasebegrensning.

**Taleinngang via st.audio_input():** Tilgjengelig i Streamlit 1.46+. Transkribering med lokal Whisper (base-modell), sky-fallback via OpenAI whisper-1 ved Exception.

**Whisper-modell caches:** `@st.cache_resource` sikrer at modellen kun lastes en gang per Streamlit-sesjon.

**Opik-sync stub:** Knappen i appen prover å importere `opik_synk`-modulen. ImportError eller NotImplementedError gir informasjonsmelding — ingen krasj. Full implementasjon i A2c.

**session_state nokler:** Bruker ASCII-nokler (`ko`, `indeks`) for a unnga encoding-problemer med norske bokstaver i Streamlit.
