"""Metadata health report.

Classifies the whole library in a single pass over rows returned by the
database layer (no SQL here — this module only structures and exports).
Covers the categories from ``metadata_engine.md``: missing title/artist/
album/track-number/genre, invalid years, duplicate ISRCs, and inconsistent
album-artist within an album.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..metadata.validate import _MAX_YEAR, _MIN_YEAR

CATEGORIES = (
    "missing_title",
    "missing_artist",
    "missing_album",
    "missing_track_number",
    "missing_genre",
    "invalid_year",
    "duplicate_isrc",
    "inconsistent_album_artist",
)


@dataclass(slots=True)
class ReportEntry:
    category: str
    track_id: int
    path: str
    detail: str = ""


@dataclass(slots=True)
class Report:
    entries: list[ReportEntry] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        counts = {c: 0 for c in CATEGORIES}
        for entry in self.entries:
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts

    @property
    def total(self) -> int:
        return len(self.entries)

    def to_json(self, path: str | Path) -> None:
        data = {
            "summary": self.summary,
            "total": self.total,
            "entries": [asdict(e) for e in self.entries],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def to_csv(self, path: str | Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["category", "track_id", "detail", "path"])
            for e in self.entries:
                writer.writerow([e.category, e.track_id, e.detail, e.path])


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def generate_metadata_report(rows) -> Report:
    report = Report()
    add = report.entries.append

    by_isrc: dict[str, list] = defaultdict(list)
    by_album: dict[str, set] = defaultdict(set)
    album_tracks: dict[str, list] = defaultdict(list)

    for row in rows:
        tid, path = row["id"], row["path"]

        if _blank(row["title"]):
            add(ReportEntry("missing_title", tid, path))
        if _blank(row["artist_name"]):
            add(ReportEntry("missing_artist", tid, path))
        if _blank(row["album_name"]):
            add(ReportEntry("missing_album", tid, path))
        if row["track_number"] is None:
            add(ReportEntry("missing_track_number", tid, path))
        if _blank(row["genre"]):
            add(ReportEntry("missing_genre", tid, path))

        year = row["year"]
        if year is not None and not (_MIN_YEAR <= year <= _MAX_YEAR):
            add(ReportEntry("invalid_year", tid, path, f"year={year}"))

        if not _blank(row["isrc"]):
            by_isrc[row["isrc"].strip().upper()].append((tid, path))

        if not _blank(row["album_name"]):
            album = row["album_name"].strip()
            album_tracks[album].append((tid, path))
            if not _blank(row["album_artist"]):
                by_album[album].add(row["album_artist"].strip())

    for isrc, items in by_isrc.items():
        if len(items) > 1:
            for tid, path in items:
                add(ReportEntry("duplicate_isrc", tid, path, f"isrc={isrc} ×{len(items)}"))

    for album, artists in by_album.items():
        if len(artists) > 1:
            detail = "album_artist differs: " + " | ".join(sorted(artists))
            for tid, path in album_tracks[album]:
                add(ReportEntry("inconsistent_album_artist", tid, path, detail))

    return report
