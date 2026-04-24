# A2b — Valideringskriterier

*Alle punkter ma vare krysset av for merge til master. Punkter merket [ ] gjelder manuelle royktester.*

---

## Enhetstester

- [x] `tester/test_triplet_lager.py` — alle 4 tester gronne ved `make test`.
- [x] Ingen regresjoner i eksisterende testsuite.

---

## Datalag — triplet_lager.py

- [x] `lagre_triplet()` skriver til `evalueringstriplets`-tabellen og returnerer ny id.
- [x] `hent_til_vurdering()` returnerer kun elementer uten triplet (LEFT JOIN).
- [x] `beregn_statistikk()` beregner korrekt rate og avvist-teller.
- [x] `filtrer_pa_komponent()` returnerer kun riktig komponent, nyeste forst.
- [x] `er_duplikat()` returnerer True etter innsending, False for.

---

## Vurderingsapp — vurderingsapp.py

- [x] Syntaks validert.
- [x] Sidebar viser godkjenningsrate, antall avviste og totalt.
- [x] Opik-sync-knapp viser stub-melding ved ImportError.
- [x] Artikkeltekst vises i ekspanderbar seksjon.
- [x] Sammendrag vises med kildenavn og prompt-versjon.
- [x] Godkjenn/avvis-knapper kaller `lagre_triplet()` og inkrementerer indeks.
- [x] Kommentarvalg Tekst/Tale lagres i session_state.
- [x] Tale: `st.audio_input()` + lokal Whisper med sky-fallback ved Exception.
- [x] Whisper-modell lastes en gang via `@st.cache_resource`.
- [ ] Manuell royktest: 5 sammendrag gjennomgatt, triplets synlige i SQLite.

---

## Git

- [x] Implementering pa feature-branch `feature/2026-04-24-a2b-triplet-lager-vurderingsapp`.
- [x] CHANGELOG.md oppdatert ved alle commits i fasen.

---

## Kode

- [x] Alle nye funksjoner har Google-stil docstring.
- [x] PRAGMA foreign_keys = ON ved alle DB-tilkoblinger.
- [x] ISO-datetime via datetime.now(timezone.utc).isoformat().
