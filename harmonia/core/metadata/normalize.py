"""Tag normalization.

Conservative by design: normalization should make tags *more consistent*
without destroying intentional styling. We fix Unicode form, whitespace and
"feat." spelling always; we only re-case a string when it is entirely upper-
or lower-case (a typical tagging artifact), leaving deliberate mixed case
(e.g. "deadmau5", "will.i.am") untouched.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import fields as dataclass_fields

from ..models import TrackTags
from .common import FieldChange

# Words kept lowercase inside a title unless they are the first word.
_LOWER_PARTICLES = frozenset(
    {"a", "an", "the", "and", "or", "nor", "but", "of", "to", "in", "on",
     "at", "by", "for", "with", "as", "vs", "vs.", "from", "into", "feat."}
)

# Variants of "featuring" → canonical "feat." (consumes any trailing dot so we
# never produce "feat..").
_FEAT_RE = re.compile(r"(?i)(?<![A-Za-z])(?:featuring|feat|ft)\.?(?![A-Za-z])")
_WS_RE = re.compile(r"\s+")

# Text fields that get the full string treatment.
_TEXT_FIELDS = ("title", "artist", "album", "album_artist", "genre", "composer")


def normalize_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def normalize_feat(text: str) -> str:
    return _FEAT_RE.sub("feat.", text)


def _smart_titlecase(text: str) -> str:
    words = text.split(" ")
    out: list[str] = []
    for i, word in enumerate(words):
        if not word:
            continue
        lower = word.lower()
        if i != 0 and lower in _LOWER_PARTICLES:
            out.append(lower)
        else:
            out.append(word[0].upper() + word[1:].lower())
    return " ".join(out)


def normalize_text(text: str) -> str:
    """Normalize a single tag string."""
    result = normalize_unicode(text)
    result = normalize_whitespace(result)
    result = normalize_feat(result)
    # Re-case only multi-word strings that are uniformly upper- or lower-case
    # (a typical tagging artifact). Single words like "ABBA", "deadmau5" or
    # "will.i.am" are left as the user/encoder intended.
    if " " in result and any(c.isalpha() for c in result) and (
        result.isupper() or result.islower()
    ):
        result = _smart_titlecase(result)
    return result


def normalize_tags(tags: TrackTags) -> tuple[TrackTags, list[FieldChange]]:
    """Return a normalized copy of ``tags`` plus the list of changes made."""
    changes: list[FieldChange] = []
    new = TrackTags(**{f.name: getattr(tags, f.name) for f in dataclass_fields(tags)})

    for field in _TEXT_FIELDS:
        value = getattr(tags, field)
        if not isinstance(value, str) or not value:
            continue
        normalized = normalize_text(value)
        if normalized != value:
            setattr(new, field, normalized)
            changes.append(FieldChange(field, value, normalized))

    return new, changes
