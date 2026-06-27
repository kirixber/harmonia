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

    def get_track(self, track_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM tracks WHERE id = ?", (track_id,)
        ).fetchone()

    def get_track_by_path(self, path: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM tracks WHERE path = ?", (path,)
        ).fetchone()

    def iter_tracks(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM tracks ORDER BY id").fetchall()

    def search_tracks(self, query: str, limit: int = 50) -> list[sqlite3.Row]:
        """Find tracks whose title/artist/album match ``query`` (case-insensitive).

        Returns rows with resolved artist/album names so frontends can show a
        human-friendly picker instead of asking users for internal IDs.
        """
        like = f"%{query.strip()}%"
        return self.conn.execute(
            "SELECT t.id, t.path, t.title, t.duration, t.codec, t.bitrate, "
            "       t.sample_rate, t.bit_depth, "
            "       ar.name AS artist_name, al.name AS album_name "
            "FROM tracks t "
            "LEFT JOIN artists ar ON t.artist_id = ar.id "
            "LEFT JOIN albums  al ON t.album_id = al.id "
            "WHERE t.title LIKE ? COLLATE NOCASE "
            "   OR ar.name LIKE ? COLLATE NOCASE "
            "   OR al.name LIKE ? COLLATE NOCASE "
            "ORDER BY t.title, t.id "
            "LIMIT ?",
            (like, like, like, limit),
        ).fetchall()

    def tracks_with_names(self) -> list[sqlite3.Row]:
        """Tracks joined with resolved artist/album names, for reporting."""
        return self.conn.execute(
            "SELECT t.id, t.path, t.title, t.track_number, t.disc_number, "
            "       t.year, t.genre, t.isrc, t.duration, t.codec, t.bitrate, "
            "       t.sample_rate, t.bit_depth, t.file_size, "
            "       ar.name AS artist_name, al.name AS album_name, "
            "       al.album_artist AS album_artist "
            "FROM tracks t "
            "LEFT JOIN artists ar ON t.artist_id = ar.id "
            "LEFT JOIN albums  al ON t.album_id = al.id "
            "ORDER BY t.id"
        ).fetchall()

    def tracks_for_dedup(self) -> list[sqlite3.Row]:
        """Fields the duplicate engine needs, with resolved artist/album names."""
        return self.conn.execute(
            "SELECT t.id, t.path, t.title, t.musicbrainz_track_id, t.isrc, "
            "       t.duration, t.track_number, t.codec, t.bitrate, "
            "       t.sample_rate, t.bit_depth, t.file_size, t.extension, "
            "       t.genre, "
            "       ar.name AS artist_name, al.name AS album_name "
            "FROM tracks t "
            "LEFT JOIN artists ar ON t.artist_id = ar.id "
            "LEFT JOIN albums  al ON t.album_id = al.id"
        ).fetchall()

    def update_track_path(self, old_path: str, new_path: str) -> None:
        from pathlib import PurePath

        self.conn.execute(
            "UPDATE tracks SET path = ?, filename = ? WHERE path = ?",
            (new_path, PurePath(new_path).name, old_path),
        )

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

    # -- tag history (reversible edits) ------------------------------------

    def record_tag_changes(
        self, track_id: int | None, path: str, changes, source: str
    ) -> None:
        """Persist before/after values so any edit can be explained/reverted.

        ``changes`` is an iterable of objects with ``field``/``old``/``new``.
        """
        when = _now()
        rows = [
            (track_id, path, c.field,
             None if c.old is None else str(c.old),
             None if c.new is None else str(c.new),
             source, when)
            for c in changes
        ]
        if rows:
            self.conn.executemany(
                "INSERT INTO tag_history"
                "(track_id, path, field, old_value, new_value, source, changed_at) "
                "VALUES (?,?,?,?,?,?,?)",
                rows,
            )
            self.conn.commit()

    def tag_history(self, track_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM tag_history WHERE track_id = ? ORDER BY id DESC",
            (track_id,),
        ).fetchall()

    # -- provider cache (metadata responses only; never image bytes) -------

    def provider_cache_get(
        self, provider: str, request_hash: str, max_age_days: int
    ) -> str | None:
        row = self.conn.execute(
            "SELECT response_json, created_at FROM provider_cache "
            "WHERE provider = ? AND request_hash = ?",
            (provider, request_hash),
        ).fetchone()
        if not row or not row["created_at"]:
            return None
        try:
            created = datetime.fromisoformat(row["created_at"])
        except ValueError:
            return None
        age = (datetime.now(timezone.utc) - created).total_seconds()
        if age > max_age_days * 86400:
            self.conn.execute(
                "DELETE FROM provider_cache WHERE provider = ? AND request_hash = ?",
                (provider, request_hash),
            )
            self.conn.commit()
            return None
        return row["response_json"]

    def provider_cache_set(
        self, provider: str, request_hash: str, response_json: str
    ) -> None:
        self.conn.execute(
            "INSERT INTO provider_cache(provider, request_hash, response_json, created_at) "
            "VALUES (?,?,?,?) ON CONFLICT(provider, request_hash) DO UPDATE SET "
            "response_json = excluded.response_json, created_at = excluded.created_at",
            (provider, request_hash, response_json, _now()),
        )
        self.conn.commit()

    # -- artwork (metadata rows only; binaries live on disk) ---------------

    def get_artwork(self, sha256: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM artwork WHERE sha256 = ?", (sha256,)
        ).fetchone()

    def upsert_artwork(
        self, sha256: str, width: int, height: int, mime_type: str,
        file_size: int, local_path: str, source: str,
    ) -> None:
        self.conn.execute(
            "INSERT INTO artwork(sha256, width, height, mime_type, file_size, "
            "local_path, source, downloaded_at) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(sha256) DO UPDATE SET width=excluded.width, "
            "height=excluded.height, mime_type=excluded.mime_type, "
            "file_size=excluded.file_size, local_path=excluded.local_path, "
            "source=excluded.source, downloaded_at=excluded.downloaded_at",
            (sha256, width, height, mime_type, file_size, local_path, source, _now()),
        )
        self.conn.commit()

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
