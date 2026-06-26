"""The core API facade.

Frontends construct one :class:`Library` and call its methods. They never
import :mod:`harmonia.database` or build a :class:`Scanner` themselves — this
is the seam that guarantees CLI, TUI and GUI behave identically.
"""

from __future__ import annotations

from pathlib import Path

from ..database import Database
from ..jobs.job import ProgressCallback
from .scanner import ScanResult, Scanner


class Library:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db = Database(db_path)
        self.scanner = Scanner(self.db)

    def scan(
        self, path: str | Path, progress: ProgressCallback | None = None
    ) -> ScanResult:
        """Index (or re-index) every audio file under ``path``."""
        return self.scanner.scan(path, progress)

    def stats(self) -> dict:
        return self.db.stats()

    def last_scan(self) -> dict | None:
        row = self.db.last_scan()
        return dict(row) if row else None

    def config_get(self, key: str, default: str | None = None) -> str | None:
        return self.db.config_get(key, default)

    def config_set(self, key: str, value: str) -> None:
        self.db.config_set(key, value)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "Library":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
