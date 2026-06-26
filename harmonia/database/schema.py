"""Schema definition and forward-only migrations.

Each migration bumps SQLite's ``PRAGMA user_version``. ``v1`` lays down the
full initial schema from ``database.md`` (including tables not yet populated
until later phases — artwork, provider_cache, fingerprints, replaygain,
jobs) so the shape is stable and later migrations only add or alter.
"""

from __future__ import annotations

import sqlite3

# --- v1: initial schema -----------------------------------------------------

_V1 = """
CREATE TABLE artists (
    id                    INTEGER PRIMARY KEY,
    name                  TEXT NOT NULL,
    sort_name             TEXT,
    musicbrainz_artist_id TEXT
);
CREATE UNIQUE INDEX idx_artists_name ON artists(name COLLATE NOCASE);

CREATE TABLE albums (
    id                     INTEGER PRIMARY KEY,
    artist_id              INTEGER REFERENCES artists(id) ON DELETE SET NULL,
    name                   TEXT NOT NULL,
    year                   INTEGER,
    album_artist           TEXT,
    total_tracks           INTEGER,
    musicbrainz_release_id TEXT,
    artwork_id             INTEGER
);
CREATE UNIQUE INDEX idx_albums_identity
    ON albums(name COLLATE NOCASE, IFNULL(album_artist,'') COLLATE NOCASE, IFNULL(year,0));

CREATE TABLE tracks (
    id                   INTEGER PRIMARY KEY,
    path                 TEXT NOT NULL UNIQUE,
    filename             TEXT,
    extension            TEXT,
    file_size            INTEGER,
    modified_time        REAL,
    sha256               TEXT,
    codec                TEXT,
    bitrate              INTEGER,
    sample_rate          INTEGER,
    bit_depth            INTEGER,
    channels             INTEGER,
    duration             REAL,
    artist_id            INTEGER REFERENCES artists(id) ON DELETE SET NULL,
    album_id             INTEGER REFERENCES albums(id) ON DELETE SET NULL,
    title                TEXT,
    track_number         INTEGER,
    disc_number          INTEGER,
    year                 INTEGER,
    genre                TEXT,
    composer             TEXT,
    musicbrainz_track_id TEXT,
    isrc                 TEXT,
    artwork_id           INTEGER,
    last_scanned         TEXT
);
CREATE INDEX idx_tracks_sha256 ON tracks(sha256);
CREATE INDEX idx_tracks_mbid ON tracks(musicbrainz_track_id);
CREATE INDEX idx_tracks_isrc ON tracks(isrc);
CREATE INDEX idx_tracks_title_artist ON tracks(title COLLATE NOCASE, artist_id);
CREATE INDEX idx_tracks_album ON tracks(album_id);

CREATE TABLE artwork (
    id            INTEGER PRIMARY KEY,
    sha256        TEXT UNIQUE,
    width         INTEGER,
    height        INTEGER,
    mime_type     TEXT,
    file_size     INTEGER,
    local_path    TEXT,
    source        TEXT,
    downloaded_at TEXT
);

CREATE TABLE provider_cache (
    id            INTEGER PRIMARY KEY,
    provider      TEXT NOT NULL,
    request_hash  TEXT NOT NULL,
    response_json TEXT,
    expires_at    TEXT,
    created_at    TEXT,
    UNIQUE(provider, request_hash)
);

CREATE TABLE fingerprints (
    track_id    INTEGER PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
    acoustid    TEXT,
    chromaprint TEXT,
    confidence  REAL
);

CREATE TABLE replaygain (
    track_id   INTEGER PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
    track_gain REAL,
    album_gain REAL,
    peak       REAL
);

CREATE TABLE scan_history (
    id            INTEGER PRIMARY KEY,
    root          TEXT,
    started_at    TEXT,
    finished_at   TEXT,
    scanned_files INTEGER DEFAULT 0,
    new_files     INTEGER DEFAULT 0,
    updated_files INTEGER DEFAULT 0,
    removed_files INTEGER DEFAULT 0,
    warnings      INTEGER DEFAULT 0,
    errors        INTEGER DEFAULT 0
);

CREATE TABLE jobs (
    id          INTEGER PRIMARY KEY,
    type        TEXT,
    state       TEXT,
    progress    INTEGER DEFAULT 0,
    started_at  TEXT,
    finished_at TEXT,
    message     TEXT
);

CREATE TABLE config (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def _migration_v1(conn: sqlite3.Connection) -> None:
    conn.executescript(_V1)


# Ordered list of (target_version, apply_fn). Append new migrations; never
# edit a released one.
MIGRATIONS = [
    (1, _migration_v1),
]

LATEST_VERSION = MIGRATIONS[-1][0]


def migrate(conn: sqlite3.Connection) -> int:
    """Apply any pending migrations. Returns the resulting schema version."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version, apply_fn in MIGRATIONS:
        if version > current:
            apply_fn(conn)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()
            current = version
    return current
