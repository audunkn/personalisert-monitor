-- Fase A-tabeller: kilder, elementer, sammendrag, evalueringstriplets
-- Fase C-tabeller (vektorer, rag_spor) legges til inkrementelt når fase C starter

CREATE TABLE IF NOT EXISTS kilder (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    navn                  TEXT    NOT NULL UNIQUE,
    url                   TEXT    NOT NULL,
    type                  TEXT    NOT NULL,               -- 'rss', 'substack', 'nett', 'youtube'
    aktiv                 INTEGER NOT NULL DEFAULT 1,     -- 1 = aktiv, 0 = deaktivert via YAML-synk
    hent_fra              TEXT,                           -- ISO-dato YYYY-MM-DD, null = ingen nedre grense
    hent_til              TEXT,                           -- ISO-dato YYYY-MM-DD, null = ingen øvre grense
    emnemerker            TEXT    NOT NULL DEFAULT '[]',  -- JSON-array med emneord
    sist_feil_tidsstempel TEXT,                           -- ISO-datetime for siste feed-feil, null ved suksess
    sist_feil_melding     TEXT                            -- Feilmelding fra siste mislykkede henting
);

CREATE TABLE IF NOT EXISTS elementer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kilde_id    INTEGER NOT NULL REFERENCES kilder(id),
    guid        TEXT    NOT NULL UNIQUE,        -- Unik identifikator fra kilden (URL eller RSS guid)
    url         TEXT,
    tittel      TEXT,
    publisert   TEXT,                           -- ISO-dato eller datetime fra kilden
    hentet      TEXT    NOT NULL,               -- ISO-datetime for når elementet ble hentet
    vault_sti   TEXT,                           -- Relativ sti til Markdown-fil i Obsidian-vault
    dead_letter INTEGER NOT NULL DEFAULT 0,     -- 1 = feilet permanent, hoppes alltid over
    bilder_json TEXT                            -- JSON-liste med filnavn for nedlastede bilder, f.eks. ["abc123.jpg"]
);

CREATE TABLE IF NOT EXISTS sammendrag (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    element_id      INTEGER NOT NULL REFERENCES elementer(id),
    tekst           TEXT    NOT NULL,
    prompt_versjon  TEXT    NOT NULL,           -- F.eks. 'v1' — korresponderer med Git-tag prompt-v1
    opprettet       TEXT    NOT NULL            -- ISO-datetime
);

CREATE TABLE IF NOT EXISTS evalueringstriplets (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    element_id          INTEGER NOT NULL REFERENCES elementer(id),
    resultat_id         INTEGER REFERENCES sammendrag(id),
    godkjent            INTEGER,                -- 1 = godkjent, 0 = avvist, null = ikke vurdert ennå
    kommentar           TEXT,
    komponent           TEXT    NOT NULL CHECK (komponent IN (
                            'sammendrag',
                            'dommer_validering',
                            'rag_gjenfinning',
                            'rag_generering'
                        )),
    er_regresjonstest   INTEGER NOT NULL DEFAULT 0,  -- 1 når domenekspert og dommer er enige
    tidsstempel         TEXT    NOT NULL             -- ISO-datetime
);
