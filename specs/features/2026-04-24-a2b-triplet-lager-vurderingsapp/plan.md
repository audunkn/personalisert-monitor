# Plan: A2b — Triplet-lager og vurderingsapp

*En commit per gruppe. Kryss av etter commit og oppdater `specs/veikart.md` etter fullfort gruppe.*

---

## Gruppe 1 — triplet_lager.py og enhetstester

- [x] Skriv `src/intelligence_monitor/evaluering/triplet_lager.py` med fem funksjoner: `lagre_triplet`, `hent_til_vurdering`, `beregn_statistikk`, `filtrer_pa_komponent`, `er_duplikat`.
- [x] Skriv `tester/test_triplet_lager.py` med 4 enhetstester — alle gronne.
- [x] Oppdater `CHANGELOG.md`.

---

## Gruppe 2 — vurderingsapp.py

- [x] Bygg `src/intelligence_monitor/evaluering/vurderingsapp.py` i Streamlit:
  - Sidebar med godkjenningsrate, antall avviste og Opik-sync-stub.
  - Artikkeltekst (ekspanderbar), sammendrag med kildenavn og prompt-versjon.
  - Godkjenn/avvis-knapper som lagrer triplet til SQLite og inkrementerer indeks.
  - Kommentarvalg Tekst/Tale i session_state.
  - Tale via `st.audio_input()` + lokal Whisper (base) med sky-fallback (OpenAI whisper-1).
  - Whisper-modell lastes en gang via `@st.cache_resource`.
- [x] Oppdater `CHANGELOG.md`.

---

## Gruppe 3 — docs og validation

- [x] Opprett `specs/features/2026-04-24-a2b-triplet-lager-vurderingsapp/` med plan.md, requirements.md, validation.md.
- [x] Kryss av A2b-oppgaver i `specs/veikart.md`.
- [x] Kryss av validation.md.
- [x] Oppdater `CHANGELOG.md`.
