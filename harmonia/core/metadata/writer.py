"""Write tags back to files, safely.

Follows the write strategy from ``metadata_engine.md``: compute the diff,
(caller validates first), apply, then re-read to *verify* the write landed.
This module only touches files — it never touches the database. The
:class:`~harmonia.core.library.Library` records the before/after values to
``tag_history`` so every edit is explainable and reversible.

A partial failure leaves the file readable: we set fields one by one,
collect per-field errors, and only ``save()`` once at the end.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen import MutagenError

from ..models import TrackTags
from .common import FieldChange
from .reader import MetadataReader

# Unified field name → Mutagen "easy" tag key. track_number/total_tracks are
# handled specially (they share the "tracknumber" key).
_EASY_KEYS = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "album_artist": "albumartist",
    "genre": "genre",
    "composer": "composer",
    "year": "date",
    "disc_number": "discnumber",
    "isrc": "isrc",
    "musicbrainz_track_id": "musicbrainz_trackid",
    "musicbrainz_album_id": "musicbrainz_albumid",
    "musicbrainz_artist_id": "musicbrainz_artistid",
}


@dataclass(slots=True)
class WriteResult:
    path: str
    changes: list[FieldChange] = dc_field(default_factory=list)
    written: bool = False
    verified: bool = False
    errors: list[str] = dc_field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.written and self.verified and not self.errors


class TagWriter:
    def __init__(self, reader: MetadataReader | None = None) -> None:
        self.reader = reader or MetadataReader()

    def diff(self, current: TrackTags, changes: dict) -> list[FieldChange]:
        """Fields in ``changes`` whose value actually differs from current."""
        out: list[FieldChange] = []
        for field_name, new_value in changes.items():
            old_value = getattr(current, field_name, None)
            if _norm(old_value) != _norm(new_value):
                out.append(FieldChange(field_name, old_value, new_value))
        return out

    def apply(self, path: str | Path, changes: dict, *, dry_run: bool = False) -> WriteResult:
        path = Path(path)
        result = WriteResult(path=str(path))
        current = self.reader.read_tags(path)
        result.changes = self.diff(current, changes)

        if not result.changes or dry_run:
            result.verified = True  # nothing to verify
            return result

        try:
            audio = MutagenFile(path, easy=True)
        except (MutagenError, OSError) as exc:
            result.errors.append(f"open failed: {exc}")
            return result
        if audio is None:
            result.errors.append("unsupported file for tag writing")
            return result
        if audio.tags is None:
            audio.add_tags()

        # Resulting track/disc values (a change may set only one of the pair).
        resulting = {c.field: c.new for c in result.changes}
        track_no = resulting.get("track_number", current.track_number)
        total = resulting.get("total_tracks", current.total_tracks)

        for change in result.changes:
            try:
                self._apply_one(audio, change.field, change.new, track_no, total)
            except (KeyError, ValueError, MutagenError) as exc:
                result.errors.append(f"{change.field}: {exc}")

        try:
            audio.save()
            result.written = True
        except (MutagenError, OSError) as exc:
            result.errors.append(f"save failed: {exc}")
            return result

        result.verified = self._verify(path, result.changes)
        return result

    def _apply_one(self, audio, field_name: str, value, track_no, total) -> None:
        if field_name in ("track_number", "total_tracks"):
            if track_no is None:
                audio.pop("tracknumber", None)
            else:
                audio["tracknumber"] = (
                    f"{track_no}/{total}" if total else str(track_no)
                )
            return

        key = _EASY_KEYS.get(field_name)
        if key is None:
            raise KeyError(f"no tag mapping for {field_name}")
        if value is None or value == "":
            audio.pop(key, None)
        else:
            audio[key] = [str(value)]

    def _verify(self, path: Path, changes: list[FieldChange]) -> bool:
        fresh = self.reader.read_tags(path)
        return all(_norm(getattr(fresh, c.field, None)) == _norm(c.new) for c in changes)


def _norm(value) -> object:
    """Compare values forgiving str/int and empty/None differences."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return value.strip()
    return value
