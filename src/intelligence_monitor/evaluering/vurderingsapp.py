"""Streamlit-app for manuell gjennomgang og vurdering av sammendrag.

Viser én artikkel om gangen med sammendrag og lar brukeren godkjenne eller
avvise med kommentar via tekst eller tale. Triplets lagres til SQLite ved
innsending. Sidebar viser løpende godkjenningsstatistikk.

Kjøres via: make review
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from intelligence_monitor.evaluering.triplet_lager import (
    beregn_statistikk,
    hent_til_vurdering,
    lagre_triplet,
)

load_dotenv()

logger = logging.getLogger(__name__)

_DATABASE_STI = Path(os.getenv("DATABASE_STI", "data/monitor.db"))
_VAULT_ROT = Path(os.getenv("VAULT_ROT", ""))


# ---------------------------------------------------------------------------
# Whisper-modell — lastes én gang og caches
# ---------------------------------------------------------------------------


@st.cache_resource
def _last_whisper():
    """Laster lokal Whisper-modell én gang og returnerer den.

    Returns:
        Lastet whisper-modell, eller None hvis whisper ikke er tilgjengelig.
    """
    try:
        import whisper  # type: ignore

        return whisper.load_model("base")
    except Exception as feil:
        logger.warning("Lokal Whisper ikke tilgjengelig: %s", feil)
        return None


# ---------------------------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------------------------


def _transkriber_lyd(lydbytes: bytes) -> str:
    """Transkriberer lydopptak til tekst.

    Prøver lokal Whisper-modell først. Faller tilbake til OpenAI sky-API
    ved feil.

    Args:
        lydbytes: Rå lydbytes fra st.audio_input().

    Returns:
        Transkribert tekst, eller tom streng ved feil.
    """
    modell = _last_whisper()
    if modell is not None:
        try:
            import tempfile

            import numpy as np

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(lydbytes)
                temp_sti = f.name

            resultat = modell.transcribe(temp_sti, language="no")
            Path(temp_sti).unlink(missing_ok=True)
            return resultat.get("text", "").strip()
        except Exception as feil:
            logger.warning("Lokal Whisper feilet: %s — prøver sky", feil)

    # Sky-fallback via OpenAI Whisper
    try:
        from openai import OpenAI

        klient = OpenAI(api_key=os.getenv("OPENAI_API_NØKKEL"))
        import io

        respons = klient.audio.transcriptions.create(
            model="whisper-1",
            file=("opptak.wav", io.BytesIO(lydbytes), "audio/wav"),
            language="no",
        )
        return respons.text.strip()
    except Exception as feil:
        logger.error("Sky-Whisper feilet: %s", feil)
        st.error(f"Transkripsjon feilet: {feil}")
        return ""


def _les_artikkeltekst(vault_sti: str | None) -> str:
    """Leser artikkeltekst fra vault-fil uten YAML-frontmatter.

    Args:
        vault_sti: Relativ sti fra vault-rot, eller None.

    Returns:
        Artikkeltekst uten frontmatter, eller tom streng.
    """
    if not vault_sti or not _VAULT_ROT:
        return ""
    fil = _VAULT_ROT / Path(vault_sti)
    if not fil.exists():
        return ""
    innhold = fil.read_text(encoding="utf-8")
    if innhold.startswith("---"):
        slutt = innhold.find("\n---", 3)
        if slutt != -1:
            innhold = innhold[slutt + 4:].strip()
    return innhold


def _initialiser_ko() -> None:
    """Fyller session_state med artikkelko fra databasen hvis den ikke finnes."""
    if "ko" not in st.session_state:
        st.session_state["ko"] = hent_til_vurdering(_DATABASE_STI)
        st.session_state["indeks"] = 0
        st.session_state["kommentarvalg"] = "Tekst"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _vis_sidebar() -> None:
    """Viser statistikk og Opik-synkronisering i sidebar."""
    with st.sidebar:
        st.subheader("Statistikk")
        stats = beregn_statistikk(_DATABASE_STI, "sammendrag")
        totalt = stats["totalt"]
        avviste = stats["antall_avviste"]
        rate = stats["godkjenningsrate"]

        st.metric("Godkjenningsrate", f"{rate:.0%}")
        col1, col2 = st.columns(2)
        col1.metric("Avviste", avviste)
        col2.metric("Totalt", totalt)

        st.divider()

        if st.button("Synkroniser til Opik"):
            try:
                from intelligence_monitor.evaluering import opik_synk  # type: ignore

                opik_synk.synkroniser(_DATABASE_STI)
                st.success("Synkronisert.")
            except (ImportError, NotImplementedError):
                st.info("Opik-synkronisering implementeres i A2c.")


# ---------------------------------------------------------------------------
# Hoved-layout
# ---------------------------------------------------------------------------


def _vis_artikkel(element: dict) -> None:
    """Viser én artikkel med sammendrag og vurderingsskjema.

    Args:
        element: Dict fra hent_til_vurdering() med artikkeldata.
    """
    st.subheader(element.get("tittel") or "(uten tittel)")

    kilde = element.get("kilde_navn", "")
    prompt = element.get("prompt_versjon", "")
    url = element.get("url", "")

    meta_col1, meta_col2 = st.columns(2)
    meta_col1.caption(f"Kilde: {kilde} | prompt: {prompt}")
    if url:
        meta_col2.markdown(f"[Åpne artikkel]({url})")

    # Artikkeltekst — ekspanderbar
    artikkeltekst = _les_artikkeltekst(element.get("vault_sti"))
    if artikkeltekst:
        with st.expander("Artikkeltekst"):
            st.markdown(artikkeltekst)
    else:
        st.caption("_(artikkeltekst ikke tilgjengelig)_")

    # Sammendrag
    st.markdown("**Sammendrag**")
    st.markdown(element.get("sammendrag_tekst") or "_(ingen sammendragstekst)_")

    st.divider()

    # Kommentarinngang
    st.markdown("**Kommentar**")
    kommentarvalg = st.radio(
        "Inndatamodus",
        ["Tekst", "Tale"],
        key="kommentarvalg",
        horizontal=True,
        label_visibility="collapsed",
    )

    kommentar = ""
    if kommentarvalg == "Tekst":
        kommentar = st.text_area(
            "Kommentar",
            label_visibility="collapsed",
            placeholder="Valgfri kommentar ...",
            key=f"kommentar_tekst_{element['element_id']}",
        )
    else:
        lyd = st.audio_input("Ta opp kommentar", key=f"lyd_{element['element_id']}")
        if lyd is not None:
            with st.spinner("Transkriberer ..."):
                kommentar = _transkriber_lyd(lyd.read())
            if kommentar:
                st.caption(f"Transkripsjon: {kommentar}")

    # Vurderingsknapper
    col_godkjenn, col_avvis = st.columns(2)
    godkjent_klikk = col_godkjenn.button(
        "Godkjenn",
        use_container_width=True,
        key=f"godkjenn_{element['element_id']}",
    )
    avvis_klikk = col_avvis.button(
        "Avvis",
        use_container_width=True,
        key=f"avvis_{element['element_id']}",
    )

    if godkjent_klikk or avvis_klikk:
        lagre_triplet(
            db_sti=_DATABASE_STI,
            element_id=element["element_id"],
            resultat_id=element.get("sammendrag_id"),
            godkjent=godkjent_klikk,
            kommentar=kommentar or None,
            komponent="sammendrag",
        )
        st.session_state["indeks"] += 1
        st.rerun()


# ---------------------------------------------------------------------------
# App-inngangspunkt
# ---------------------------------------------------------------------------


def main() -> None:
    """Starter vurderingsappen."""
    st.set_page_config(
        page_title="Intelligence Monitor — vurdering",
        page_icon=None,
        layout="wide",
    )
    st.title("Vurdering av sammendrag")

    _initialiser_ko()
    _vis_sidebar()

    ko = st.session_state["ko"]
    indeks = st.session_state["indeks"]

    if not ko:
        st.info("Ingen elementer i koen. Kjor `make sammendrag` for a generere nye sammendrag.")
        return

    if indeks >= len(ko):
        stats = beregn_statistikk(_DATABASE_STI, "sammendrag")
        st.success(
            f"Alle {len(ko)} elementer er vurdert i denne sesjonen. "
            f"Godkjenningsrate: {stats['godkjenningsrate']:.0%} "
            f"({stats['antall_avviste']} avviste av {stats['totalt']} totalt)."
        )
        if st.button("Start ny sesjon"):
            del st.session_state["ko"]
            st.rerun()
        return

    _vis_artikkel(ko[indeks])

    fremgang = f"{indeks + 1} av {len(kø)}"
    st.caption(fremgang)
    st.progress((indeks) / len(kø))


if __name__ == "__main__":
    main()
