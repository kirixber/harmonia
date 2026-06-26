"""Walk a directory tree and keep the database index in sync.

Incremental by design: a file whose size and mtime are unchanged since the
last scan is skipped without re-reading tags or re-hashing. New and changed
files are parsed and upserted; files that vanished from disk are removed
from the index.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ...database import Database
from ...jobs.job import Progress, ProgressCallback
from ...utils.hashing import sha256_file
from ...utils.logging import get_logger
from ..metadata import MetadataReader
from ..metadata.reader import AUDIO_EXTENSIONS
from ..models import Track

log = get_logger(__name__)


@dataclass(slots=True)
class ScanResult:
    root: str
    scanned_files: int = 0
    new_files: int = 0
    updated_files: int = 0
    removed_files: int = 0
    warnings: int = 0
    errors: int = 0

    def as_record(self, started: str, finished: str) -> dict:
        return {
            "root": self.root,
            "started_at": started,
            "finished_at": finished,
            "scanned_files": self.scanned_files,
            "new_files": self.new_files,
            "updated_files": self.updated_files,
            "removed_files": self.removed_files,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class Scanner:
    def __init__(self, db: Database, reader: MetadataReader | None = None) -> None:
        self.db = db
        self.reader = reader or MetadataReader()

    def _collect(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for dirpath, _dirs, filenames in os.walk(root):
            for name in filenames:
                if Path(name).suffix.lower() in AUDIO_EXTENSIONS:
                    files.append(Path(dirpath) / name)
        return files

    def scan(
        self, root: str | Path, progress: ProgressCallback | None = None
    ) -> ScanResult:
        root = Path(root).expanduser().resolve()
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result = ScanResult(root=str(root))

        if not root.exists():
            raise FileNotFoundError(f"Scan path does not exist: {root}")

        files = self._collect(root)
        total = len(files)
        seen: set[str] = set()

        for index, file_path in enumerate(files, start=1):
            path_str = str(file_path)
            seen.add(path_str)
            try:
                self._process_file(file_path, path_str, result)
            except OSError as exc:
                result.errors += 1
                log.warning("Scan error on %s: %s", path_str, exc)
            if progress:
                progress(Progress(index, total, file_path.name))

        # Files indexed under this root but no longer on disk → removed.
        gone = self.db.paths_under(str(root)) - seen
        result.removed_files = self.db.delete_tracks(gone)

        finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.db.commit()
        self.db.record_scan(**result.as_record(started, finished))
        log.info(
            "Scan complete: %s new=%d updated=%d removed=%d errors=%d",
            root, result.new_files, result.updated_files,
            result.removed_files, result.errors,
        )
        return result

    def _process_file(self, file_path: Path, path_str: str, result: ScanResult) -> None:
        stat = file_path.stat()
        existing = self.db.get_track_stat(path_str)
        is_new = existing is None

        if not is_new and existing["file_size"] == stat.st_size and \
                _close(existing["modified_time"], stat.st_mtime):
            result.scanned_files += 1  # counted as scanned, but unchanged
            return

        self.index_file(file_path)

        result.scanned_files += 1
        if is_new:
            result.new_files += 1
        else:
            result.updated_files += 1

    def index_file(self, file_path: str | Path) -> int:
        """Read one file and upsert its row, ignoring the incremental check.

        Used by the scan loop for changed files and by the metadata/rename
        engines to refresh the DB after a write or move.
        """
        file_path = Path(file_path)
        stat = file_path.stat()
        tags, info = self.reader.read(file_path)
        artist_id = self.db.get_or_create_artist(
            tags.artist, mbid=tags.musicbrainz_artist_id
        )
        album_artist = tags.album_artist or tags.artist
        album_id = self.db.get_or_create_album(
            tags.album,
            artist_id=artist_id,
            year=tags.year,
            album_artist=album_artist,
            total_tracks=tags.total_tracks,
            mbid=tags.musicbrainz_album_id,
        )
        track = Track(
            path=str(file_path),
            filename=file_path.name,
            extension=file_path.suffix.lower(),
            file_size=stat.st_size,
            modified_time=stat.st_mtime,
            sha256=sha256_file(file_path),
            tags=tags,
            info=info,
            artist_id=artist_id,
            album_id=album_id,
        )
        return self.db.upsert_track(track)


def _close(a: float | None, b: float, eps: float = 1e-4) -> bool:
    if a is None:
        return False
    return abs(a - b) <= eps
