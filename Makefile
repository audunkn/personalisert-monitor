.DEFAULT_GOAL := help

.PHONY: help innhent sammendrag review synk regresjon rapport test test-enkelt alle produksjon

help:
	@echo "Intelligence Monitor — tilgjengelige targets:"
	@echo ""
	@echo "  innhent      Hent nye artikler fra alle kilder"
	@echo "  sammendrag   Lag sammendrag for nye artikler"
	@echo "  review       Start vurderingsapp (Streamlit)"
	@echo "  synk         Synkroniser evalueringer til Opik"
	@echo "  regresjon    Kjør regresjonstester"
	@echo "  rapport      Generer analyserapport"
	@echo "  test         Kjør alle enhetstester"
	@echo "  test-enkelt  Kjør én testfil: make test-enkelt fil=tester/test_foo.py"
	@echo "  alle         Innhent + sammendrag"
	@echo "  produksjon   Innhent + sammendrag + rapport"

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

alle: innhent sammendrag

produksjon: innhent sammendrag rapport
