"""Datalag for evalueringstriplets — menneskelige vurderinger av sammendrag.

Evalueringstriplets er råmaterialet for LLM-dommer i fase B. Hvert triplet
knytter et element (artikkel) til et resultat (sammendrag) og en human-vurdering
(godkjent/avvist med kommentar).

Mønster: sqlite3.connect(db_sti) med PRAGMA foreign_keys = ON.
Datoformat: ISO 8601 via datetime.now(timezone.utc).isoformat().
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def lagre_triplet(
    db_sti: Path,
    element_id: int,
    resultat_id: int | None,
    godkjent: bool,
    kommentar: str | None,
    komponent: str = "sammendrag",
) -> int:
    """Skriver en ny evalueringstriplet til databasen.

    Ingen UNIQUE-constraint på (element_id, komponent) — dette tillater revisjon
    der samme element vurderes på nytt med en ny prompt-versjon.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        element_id: Fremmednøkkel til elementer-tabellen.
        resultat_id: Fremmednøkkel til sammendrag-tabellen, eller None.
        godkjent: True = godkjent, False = avvist.
        kommentar: Valgfri tekstkommentar fra evaluatoren.
        komponent: Enum-verdi for komponenten som vurderes. Standard: "sammendrag".

    Returns:
        Primærnøkkel (id) til det nylig innsatte triplet.
    """
    tidsstempel = datetime.now(timezone.utc).isoformat()
    godkjent_int = 1 if godkjent else 0

    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute("PRAGMA foreign_keys = ON")
        markør = tilkobling.execute(
            """
            INSERT INTO evalueringstriplets
                (element_id, resultat_id, godkjent, kommentar, komponent, tidsstempel)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (element_id, resultat_id, godkjent_int, kommentar, komponent, tidsstempel),
        )
        return markør.lastrowid


def hent_til_vurdering(db_sti: Path) -> list[dict]:
    """Henter elementer med sammendrag som ikke har noen triplet ennå.

    Bruker LEFT JOIN mot evalueringstriplets for å finne elementer der
    vurdering mangler. Returnerer én rad per element — velger nyeste sammendrag
    hvis et element har fått oppdatert sammendrag.

    Args:
        db_sti: Sti til SQLite-databasefilen.

    Returns:
        Liste med dict per element. Nøkler: element_id, tittel, url, kilde_navn,
        vault_sti, sammendrag_id, sammendrag_tekst, prompt_versjon.
    """
    spørring = """
        SELECT
            e.id         AS element_id,
            e.tittel,
            e.url,
            k.navn       AS kilde_navn,
            e.vault_sti,
            s.id         AS sammendrag_id,
            s.tekst      AS sammendrag_tekst,
            s.prompt_versjon
        FROM elementer e
        JOIN kilder k ON k.id = e.kilde_id
        JOIN sammendrag s ON s.element_id = e.id
        LEFT JOIN evalueringstriplets t
            ON t.element_id = e.id
            AND t.komponent = 'sammendrag'
        WHERE t.id IS NULL
          AND e.dead_letter = 0
        ORDER BY s.opprettet DESC
    """
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute("PRAGMA foreign_keys = ON")
        tilkobling.row_factory = sqlite3.Row
        rader = tilkobling.execute(spørring).fetchall()
    return [dict(rad) for rad in rader]


def beregn_statistikk(db_sti: Path, komponent: str = "sammendrag") -> dict:
    """Beregner godkjenningsrate og antall avviste for én komponent.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        komponent: Komponent å filtrere på. Standard: "sammendrag".

    Returns:
        Dict med nøklene:
        - godkjenningsrate (float): andel godkjente, 0.0 hvis ingen triplets.
        - antall_avviste (int): antall rader med godkjent = 0.
        - totalt (int): totalt antall vurderte triplets.
    """
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute("PRAGMA foreign_keys = ON")
        rad = tilkobling.execute(
            """
            SELECT
                COUNT(*)                                        AS totalt,
                SUM(CASE WHEN godkjent = 1 THEN 1 ELSE 0 END) AS godkjente,
                SUM(CASE WHEN godkjent = 0 THEN 1 ELSE 0 END) AS avviste
            FROM evalueringstriplets
            WHERE komponent = ?
              AND godkjent IS NOT NULL
            """,
            (komponent,),
        ).fetchone()

    totalt = rad[0] or 0
    godkjente = rad[1] or 0
    avviste = rad[2] or 0

    godkjenningsrate = godkjente / totalt if totalt > 0 else 0.0

    return {
        "godkjenningsrate": godkjenningsrate,
        "antall_avviste": avviste,
        "totalt": totalt,
    }


def filtrer_pa_komponent(db_sti: Path, komponent: str) -> list[dict]:
    """Henter alle triplets for én komponent, nyeste først.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        komponent: Komponent å filtrere på (f.eks. "sammendrag").

    Returns:
        Liste med dict per triplet. Nøkler: id, element_id, resultat_id,
        godkjent, kommentar, komponent, er_regresjonstest, tidsstempel.
    """
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute("PRAGMA foreign_keys = ON")
        tilkobling.row_factory = sqlite3.Row
        rader = tilkobling.execute(
            """
            SELECT id, element_id, resultat_id, godkjent, kommentar,
                   komponent, er_regresjonstest, tidsstempel
            FROM evalueringstriplets
            WHERE komponent = ?
            ORDER BY tidsstempel DESC
            """,
            (komponent,),
        ).fetchall()
    return [dict(rad) for rad in rader]


def er_duplikat(db_sti: Path, element_id: int, komponent: str) -> bool:
    """Sjekker om element allerede har en triplet for denne komponenten.

    Args:
        db_sti: Sti til SQLite-databasefilen.
        element_id: Fremmednøkkel til elementer-tabellen.
        komponent: Komponent å sjekke mot.

    Returns:
        True hvis det finnes minst én triplet for (element_id, komponent).
    """
    with sqlite3.connect(db_sti) as tilkobling:
        tilkobling.execute("PRAGMA foreign_keys = ON")
        antall = tilkobling.execute(
            """
            SELECT COUNT(*) FROM evalueringstriplets
            WHERE element_id = ? AND komponent = ?
            """,
            (element_id, komponent),
        ).fetchone()[0]
    return antall > 0
