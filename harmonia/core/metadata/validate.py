"""Tag validation.

Produces a list of issues, each with a severity, the field at fault, a
human description and a suggested fix. Per-track checks live here;
library-wide checks (duplicate ISRC across tracks, etc.) live in the
reports module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..models import TrackTags

# ISRC: CC (country) + XXX (registrant) + YY (year) + NNNNN (designation).
_ISRC_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$")

_MIN_YEAR = 1860  # first sound recordings
_MAX_YEAR = datetime.now().year + 1


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(slots=True)
class Issue:
    severity: Severity
    field: str
    message: str
    suggestion: str = ""


def valid_isrc(isrc: str) -> bool:
    return bool(_ISRC_RE.match(isrc.replace("-", "").upper()))


def validate_tags(tags: TrackTags) -> list[Issue]:
    issues: list[Issue] = []

    if not tags.title:
        issues.append(Issue(Severity.ERROR, "title", "Missing title",
                            "Set a title or infer it from the filename."))
    if not tags.artist:
        issues.append(Issue(Severity.ERROR, "artist", "Missing artist",
                            "Set an artist or enrich from a metadata provider."))
    if not tags.album:
        issues.append(Issue(Severity.WARNING, "album", "Missing album",
                            "Set an album, or mark the track as a single."))

    if tags.track_number is not None and tags.track_number <= 0:
        issues.append(Issue(Severity.WARNING, "track_number",
                            f"Invalid track number: {tags.track_number}",
                            "Track numbers start at 1."))

    if tags.disc_number is not None and tags.disc_number <= 0:
        issues.append(Issue(Severity.WARNING, "disc_number",
                            f"Invalid disc number: {tags.disc_number}",
                            "Disc numbers start at 1."))

    if tags.year is not None and not (_MIN_YEAR <= tags.year <= _MAX_YEAR):
        issues.append(Issue(Severity.WARNING, "year",
                            f"Year out of range: {tags.year}",
                            f"Expected between {_MIN_YEAR} and {_MAX_YEAR}."))

    if tags.isrc and not valid_isrc(tags.isrc):
        issues.append(Issue(Severity.WARNING, "isrc",
                            f"Malformed ISRC: {tags.isrc}",
                            "Expected 12 chars: CC + 3 + YY + 5 digits."))

    return issues
