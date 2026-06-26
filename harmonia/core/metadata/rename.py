"""Rename files (and create folder structures) from metadata templates.

Templates use Python-style fields: ``{artist}``, ``{album_artist}``,
``{album}``, ``{title}``, ``{track}``, ``{disc}``, ``{year}``, ``{genre}``
(e.g. ``{track:02}`` to zero-pad). A ``/`` in the template creates folders.

Safety first (``metadata_engine.md``): values are sanitized of illegal
filename characters, a template needing a tag the file lacks is skipped, and
an existing destination is reported as a conflict — never overwritten. This
module moves files only; the DB path update happens in the library layer.
"""

from __future__ import annotations

import re
import shutil
import string
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..models import TrackTags

# Friendly preset names → template patterns.
NAMED_TEMPLATES = {
    "title-artist": "{title} - {artist}",
    "artist-title": "{artist} - {title}",
    "artist-album-track-title": "{artist}/{album}/{track:02} - {title}",
    "disc-track-title": "{disc}/{track:02} - {title}",
}

_FIELD_TO_ATTR = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "album_artist": "album_artist",
    "track": "track_number",
    "disc": "disc_number",
    "year": "year",
    "genre": "genre",
}

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_STRING_FIELDS = {"title", "artist", "album", "album_artist", "genre"}


class RenameStatus(str, Enum):
    RENAME = "rename"
    UNCHANGED = "unchanged"
    CONFLICT = "conflict"        # destination already exists
    MISSING_FIELDS = "missing"   # template needs a tag the file lacks


@dataclass(slots=True)
class RenamePlan:
    old_path: str
    new_path: str | None
    status: RenameStatus
    reason: str = ""


def sanitize_component(text: str) -> str:
    """Make a string safe as a single path component."""
    cleaned = _ILLEGAL.sub("_", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned or "Unknown"


def resolve_template(name_or_pattern: str) -> str:
    return NAMED_TEMPLATES.get(name_or_pattern, name_or_pattern)


def _used_fields(pattern: str) -> list[str]:
    return [
        fname for _lit, fname, _spec, _conv in string.Formatter().parse(pattern)
        if fname
    ]


class Renamer:
    def plan(
        self,
        path: str | Path,
        tags: TrackTags,
        template: str,
        base_dir: str | Path | None = None,
    ) -> RenamePlan:
        path = Path(path)
        pattern = resolve_template(template)

        values: dict[str, object] = {}
        for field_name in _used_fields(pattern):
            attr = _FIELD_TO_ATTR.get(field_name)
            value = getattr(tags, attr, None) if attr else None
            if field_name == "album_artist" and not value:
                value = tags.artist
            if value is None or (isinstance(value, str) and not value.strip()):
                return RenamePlan(str(path), None, RenameStatus.MISSING_FIELDS,
                                  f"missing tag: {field_name}")
            values[field_name] = (
                sanitize_component(str(value)) if field_name in _STRING_FIELDS else value
            )

        try:
            rel = pattern.format(**values)
        except (KeyError, ValueError) as exc:
            return RenamePlan(str(path), None, RenameStatus.MISSING_FIELDS, str(exc))

        base = Path(base_dir) if base_dir else path.parent
        target = (base / (rel + path.suffix)).resolve()

        if target == path.resolve():
            return RenamePlan(str(path), str(target), RenameStatus.UNCHANGED)
        if target.exists():
            return RenamePlan(str(path), str(target), RenameStatus.CONFLICT,
                              "destination already exists")
        return RenamePlan(str(path), str(target), RenameStatus.RENAME)

    def apply(self, plan: RenamePlan) -> bool:
        """Move the file. Returns True if moved. Never overwrites."""
        if plan.status is not RenameStatus.RENAME or not plan.new_path:
            return False
        target = Path(plan.new_path)
        if target.exists():
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(plan.old_path, str(target))
        return True
