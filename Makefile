.DEFAULT_GOAL := help

.PHONY: help innhent sammendrag review synk regresjon rapport test test-enkelt alle produksjon

# ─────────────────────────────────────────────────────────────────────────────
# Intelligence Monitor — Makefile
#
# Alle targets forutsetter at:
#   - Python-miljøet er aktivert (.venv via `uv venv`)
#   - .env er fylt ut med ANTHROPIC_API_NØKKEL og VAULT_STI
#   - konfig/kilder.yaml inneholder minst én aktiv kilde
#
# Dataflyt i systemet:
#   innhent → sammendrag → [review/synk] → rapport
#
# Skriverekkefølge ved innhenting:
#   UUID tildeles → artikkeltekst skrives til Obsidian-vault →
#   metadata skrives til SQLite → rollback ved feil i enten steget
# ─────────────────────────────────────────────────────────────────────────────

## help: Vis denne hjelpteksten (standardmål)
help:
	@echo "Intelligence Monitor — tilgjengelige targets:"
	@echo ""
	@echo "  innhent      Hent nye artikler fra alle aktive kilder i konfig/kilder.yaml"
	@echo "  sammendrag   Lag norskspråklige sammendrag for innhentede artikler uten sammendrag"
	@echo "  review       Start Streamlit-vurderingsapp for manuell QA av sammendrag"
	@echo "  synk         Synkroniser evalueringstriplets fra SQLite til Opik"
	@echo "  regresjon    Kjør regresjonstester mot lagrede evalueringstriplets"
	@echo "  rapport      Generer analyserapport over systemtilstand og trender"
	@echo "  test         Kjør alle enhetstester med verbose output"
	@echo "  test-enkelt  Kjør én testfil: make test-enkelt fil=tester/test_foo.py"
	@echo "  alle         Kjør full innhentings- og sammendragssyklus (innhent + sammendrag)"
	@echo "  produksjon   Full produksjonskjøring: innhent + sammendrag + rapport"
	@echo ""
	@echo "Vanlig arbeidsflyt:"
	@echo "  make alle        → daglig innhenting"
	@echo "  make review      → manuell gjennomgang"
	@echo "  make synk        → synkroniser til Opik etter review"
	@echo "  make produksjon  → full kjøring med rapport"

# ─────────────────────────────────────────────────────────────────────────────
# INNHENTING
# Leser konfig/kilder.yaml og henter nye artikler siden siste kjøring.
# Skriver artikkeltekst + bilder til Obsidian-vault (VAULT_STI/.env).
# Skriver metadata (guid, url, tittel, kilde_id, tidsstempel) til SQLite.
# Setter dead_letter=true på elementer som feiler etter 3 forsøk.
# Endrer IKKE eksisterende rader i databasen — kun insert av nye elementer.
# ─────────────────────────────────────────────────────────────────────────────
## innhent: Hent nye artikler fra alle aktive kilder
innhent:
	python -m intelligence_monitor.innhenter.kjører

# ─────────────────────────────────────────────────────────────────────────────
# SAMMENDRAG
# Behandler elementer i SQLite der sammendrag mangler (ingen rad i sammendrag-tabellen).
# Kaller Claude API med prompt fra src/intelligence_monitor/sammendrag/prompts/.
# Skriver ferdig sammendrag til sammendrag-tabellen med prompt_versjon og tidsstempel.
# Artikler over MAKS_ARTIKKEL_TOKENS (standard: 4000) trunkeres før API-kall.
# Endrer IKKE vault-innhold — kun SQLite-tabellen sammendrag.
# ─────────────────────────────────────────────────────────────────────────────
## sammendrag: Lag norskspråklige sammendrag for nye artikler via Claude API
sammendrag:
	python -m intelligence_monitor.sammendrag.lag_sammendrag

# ─────────────────────────────────────────────────────────────────────────────
# VURDERINGSAPP
# Starter en lokal Streamlit-webserver (standard: http://localhost:8501).
# Viser sammendrag med tommelen opp/ned-grensesnitt for manuell QA.
# Lagrer evalueringstriplets (input, output, score) til SQLite.
# Blokkerer terminalen — avslutt med Ctrl+C.
# Krever ingen nettverkstilgang utover lokal Streamlit-server.
# ─────────────────────────────────────────────────────────────────────────────
## review: Start lokal Streamlit-vurderingsapp for manuell QA (blokkerer terminal)
review:
	streamlit run src/intelligence_monitor/evaluering/vurderingsapp.py

# ─────────────────────────────────────────────────────────────────────────────
# OPIK-SYNKRONISERING
# Leser evalueringstriplets fra SQLite og skriver dem til Opik-prosjektet
# definert av OPIK_PROSJEKTNAVN i .env (standard: intelligence-monitor).
# Kjøres typisk etter `make review` for å synkronisere manuelle vurderinger.
# Fail-safe: hvis Opik-API er utilgjengelig, logges feil men programmet avbrytes ikke.
# Duplikater håndteres via unik triplet-ID — trygt å kjøre flere ganger.
# ─────────────────────────────────────────────────────────────────────────────
## synk: Synkroniser evalueringstriplets fra SQLite til Opik (idempotent)
synk:
	python -m intelligence_monitor.evaluering.opik_synk

# ─────────────────────────────────────────────────────────────────────────────
# REGRESJONSTESTING  [FASE B — PLACEHOLDER]
# Full implementasjon tilhører fase B og krever LLM-dommer (intelligence_monitor.evaluering.dommer).
# Flyten: hent artikkel → kjør sammendrag med gjeldende prompt → LLM-dommer scorer →
# sammenlign mot lagret domeneekspert-score i evalueringstriplet.
#
# I fase A finnes targeten kun som skall og vil feile med "No module named
# 'intelligence_monitor.evaluering.regresjonstest'" frem til fase B er levert.
#
# Når implementert (fase B):
#   Kjører evalueringstriplets merket er_regresjonstest=true mot Claude API på nytt.
#   Sammenligner nye svar med lagrede referansesvar og rapporterer avvik.
#   Brukes for å oppdage prompt-regresjoner etter modell- eller promptoppdateringer.
#   Skriver IKKE nye rader — leser kun eksisterende triplets fra SQLite.
# ─────────────────────────────────────────────────────────────────────────────
## regresjon: Kjør regresjonstester mot lagrede evalueringstriplets [krever fase B]
regresjon:
	python -m intelligence_monitor.evaluering.regresjonstest

# ─────────────────────────────────────────────────────────────────────────────
# ANALYSERAPPORT
# Leser aggregerte data fra SQLite og genererer en Markdown-rapport.
# Inneholder: antall artikler per kilde, sammendragskvalitet over tid,
# evalueringstrender og eventuelle dead_letter-elementer som krever manuell handling.
# Skriver rapport til stdout eller til en fil avhengig av konfigurasjon.
# Leser IKKE fra vault — kun SQLite-metadata og sammendrag.
# ─────────────────────────────────────────────────────────────────────────────
## rapport: Generer analyserapport over systemtilstand og evalueringstrender
rapport:
	python -m intelligence_monitor.analyse.rapport

# ─────────────────────────────────────────────────────────────────────────────
# TESTER
# Kjører pytest mot tester/-mappen med verbose output.
# Alle tester bruker midlertidige SQLite-filer og påvirker IKKE produksjonsdata.
# `test-enkelt` kjører én navngitt testfil — bruk `fil=`-parameteren.
# Eksempel: make test-enkelt fil=tester/test_db_init.py
# ─────────────────────────────────────────────────────────────────────────────
## test: Kjør alle enhetstester (påvirker ikke produksjonsdata)
test:
	pytest tester/ -v

## test-enkelt: Kjør én testfil — bruk: make test-enkelt fil=tester/test_foo.py
test-enkelt:
	pytest tester/$(fil) -v

# ─────────────────────────────────────────────────────────────────────────────
# SAMMENSATTE TARGETS
# `alle`      — daglig bruk: henter og behandler nye artikler
# `produksjon` — full kjøring inkl. rapport, egnet for planlagt kjøring (cron)
# Begge targets stopper ved første feil (Make standard-atferd).
# ─────────────────────────────────────────────────────────────────────────────
## alle: Full innhentings- og sammendragssyklus (daglig bruk)
alle: innhent sammendrag

## produksjon: Full kjøring med rapport (egnet for cron/planlagt kjøring)
produksjon: innhent sammendrag rapport
