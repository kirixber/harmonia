"""SQLite access object. All persistence flows through here."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..core.models import AudioInfo, Track, TrackTags
from ..utils.paths import database_path, ensure_dir
from . import schema


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """Owns one SQLite connection and exposes typed accessors.

    Pass ``":memory:"`` for tests. With no argument the default on-disk
    location from :func:`harmonia.utils.paths.database_path` is used.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            path = database_path()
        self.path = str(path)
        if self.path != ":memory:":
            ensure_dir(Path(self.path).parent)

        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        schema.migrate(self.conn)

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- artists / albums --------------------------------------------------

    def get_or_create_artist(
        self, name: str | None, sort_name: str | None = None, mbid: str | None = None
    ) -> int | None:
        if not name:
            return None
        cur = self.conn.execute(
            "INSERT INTO artists(name, sort_name, musicbrainz_artist_id) "
            "VALUES(?,?,?) ON CONFLICT(name) DO NOTHING",
            (name, sort_name, mbid),
        )
        if cur.lastrowid and cur.rowcount:
            return cur.lastrowid
        row = self.conn.execute(
            "SELECT id FROM artists WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        return row["id"] if row else None

    def get_or_create_album(
        self,
        name: str | None,
        artist_id: int | None = None,
        year: int | None = None,
        album_artist: str | None = None,
        total_tracks: int | None = None,
        mbid: str | None = None,
    ) -> int | None:
        if not name:
            return None
        self.conn.execute(
            "INSERT INTO albums(name, artist_id, year, album_artist, total_tracks, "
            "musicbrainz_release_id) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(name, IFNULL(album_artist,''), IFNULL(year,0)) DO NOTHING",
            (name, artist_id, year, album_artist, total_tracks, mbid),
        )
        row = self.conn.execute(
            "SELECT id FROM albums WHERE name = ? COLLATE NOCASE "
            "AND IFNULL(album_artist,'') = IFNULL(?,'') COLLATE NOCASE "
            "AND IFNULL(year,0) = IFNULL(?,0)",
            (name, album_artist, year),
        ).fetchone()
        return row["id"] if row else None

    # -- tracks ------------------------------------------------------------

    def get_track_stat(self, path: str) -> sqlite3.Row | None:
        """Minimal row used by the scanner to decide if a file changed."""
        return self.conn.execute(
            "SELECT id, file_size, modified_time FROM tracks WHERE path = ?",
            (path,),
        ).fetchone()

    def upsert_track(self, track: Track) -> int:
        """Insert a new track or update the existing row matched by path."""
        t, info, tags = track, track.info, track.tags
        params = {
            "path": t.path,
            "filename": t.filename,
            "extension": t.extension,
            "file_size": t.file_size,
            "modified_time": t.modified_time,
            "sha256": t.sha256,
            "codec": info.codec,
            "bitrate": info.bitrate,
            "sample_rate": info.sample_rate,
            "bit_depth": info.bit_depth,
            "channels": info.channels,
            "duration": info.duration,
            "artist_id": track.artist_id,
            "album_id": track.album_id,
            "title": tags.title,
            "track_number": tags.track_number,
            "disc_number": tags.disc_number,
            "year": tags.year,
            "genre": tags.genre,
            "composer": tags.composer,
            "musicbrainz_track_id": tags.musicbrainz_track_id,
            "isrc": tags.isrc,
            "last_scanned": _now(),
        }
        cols = ", ".join(params)
        placeholders = ", ".join(f":{c}" for c in params)
        updates = ", ".join(f"{c}=excluded.{c}" for c in params if c != "path")
        cur = self.conn.execute(
            f"INSERT INTO tracks ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT(path) DO UPDATE SET {updates}",
            params,
        )
        if cur.lastrowid:
            return cur.lastrowid
        row = self.conn.execute(
            "SELECT id FROM tracks WHERE path = ?", (t.path,)
        ).fetchone()
        return row["id"]

    def paths_under(self, root: str) -> set[str]:
        prefix = root.rstrip("/") + "/"
        rows = self.conn.execute(
            "SELECT path FROM tracks WHERE path = ? OR path LIKE ?",
            (root, prefix + "%"),
        ).fetchall()
        return {r["path"] for r in rows}

    def delete_tracks(self, paths: Iterable[str]) -> int:
        paths = list(paths)
        if not paths:
            return 0
        self.conn.executemany("DELETE FROM tracks WHERE path = ?", ((p,) for p in paths))
        return len(paths)

    # -- scan history ------------------------------------------------------

    def record_scan(self, **fields) -> int:
        cols = ", ".join(fields)
        placeholders = ", ".join(f":{c}" for c in fields)
        cur = self.conn.execute(
            f"INSERT INTO scan_history ({cols}) VALUES ({placeholders})", fields
        )
        self.conn.commit()
        return cur.lastrowid

    def last_scan(self) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM scan_history ORDER BY id DESC LIMIT 1"
        ).fetchone()

    # -- stats / config ----------------------------------------------------

    def stats(self) -> dict:
        c = self.conn.execute
        return {
            "tracks": c("SELECT COUNT(*) FROM tracks").fetchone()[0],
            "artists": c("SELECT COUNT(*) FROM artists").fetchone()[0],
            "albums": c("SELECT COUNT(*) FROM albums").fetchone()[0],
            "total_duration": c("SELECT IFNULL(SUM(duration),0) FROM tracks").fetchone()[0],
            "total_size": c("SELECT IFNULL(SUM(file_size),0) FROM tracks").fetchone()[0],
        }

    def config_get(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def config_set(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO config(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    def commit(self) -> None:
        self.conn.commit()
