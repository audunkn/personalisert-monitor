"""Innhentings-shell for Intelligence Monitor.

Koordinerer alle aktive innhentingskanaler. I A1 støttes kun RSS.
Øvrige kanaler (nett, YouTube, Substack) legges til i A4 og A6.

Bruk:
    python -m intelligence_monitor.innhenter.kjører
    make innhent
"""

from __future__ import annotations

import logging

from dotenv import load_dotenv

load_dotenv()

from intelligence_monitor.innhenter import rss  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def kjør() -> None:
    """Kjører alle aktive innhentingskanaler og rapporterer resultat."""
    logger.info("=== Innhenting starter ===")

    nye_rss = rss.innhent_alle()
    # TODO A4: legg til nett.innhent_alle() og substack.innhent_alle()
    # TODO A6: legg til youtube.innhent_alle()

    totalt = nye_rss
    logger.info("=== Innhenting ferdig — %d nye artikler totalt ===", totalt)


if __name__ == "__main__":
    kjør()
