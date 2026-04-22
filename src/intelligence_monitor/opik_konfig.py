"""Opik-konfigurasjon for Intelligence Monitor.

Konfigurerer Opik-observabilitet ved oppstart. Feiler stille dersom
API-nøkkel mangler eller tilkoblingen mislykkes — Opik er valgfri.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def konfigurer_opik() -> None:
    """Initialiserer Opik med API-nøkkel fra miljøvariabler.

    Raises:
        EnvironmentError: Dersom OPIK_API_NØKKEL ikke er satt.
        Exception: Dersom Opik SDK kaster unntak under konfigurasjon.
    """
    import opik  # noqa: PLC0415

    api_nøkkel = os.getenv("OPIK_API_NØKKEL")
    arbeidsrom = os.getenv("OPIK_ARBEIDSROM")
    prosjektnavn = os.getenv("OPIK_PROSJEKTNAVN", "intelligence-monitor")

    if not api_nøkkel:
        raise EnvironmentError("OPIK_API_NØKKEL er ikke satt — systemet kan ikke starte uten Opik-sporing.")

    opik.configure(api_key=api_nøkkel, workspace=arbeidsrom, project_name=prosjektnavn)
    logger.info("Opik konfigurert for prosjekt '%s'.", prosjektnavn)
