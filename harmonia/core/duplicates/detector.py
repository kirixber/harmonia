"""Candidate grouping and weighted confidence scoring.

Grouping uses strong keys (MusicBrainz Track ID, ISRC) and a normalized
title+artist key so we never do an O(n²) sweep of the whole library — only
tracks that share a key are compared. Scoring then combines the signals
from ``duplicate_detection.md`` into a 0–100 confidence with a low
false-positive bias.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

# Similarity backend: RapidFuzz if present, else stdlib difflib.
try:
    from rapidfuzz.fuzz import ratio as _ratio

    def similarity(a: str, b: str) -> float:
        return _ratio(a, b) / 100.0
except ImportError:  # pragma: no cover - fallback path
    from difflib import SequenceMatcher

    def similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()


# Signal weights (duplicate_detection.md). Fingerprint arrives in v0.5.
WEIGHTS = {
    "musicbrainz_track_id": 100,
    "isrc": 95,
    "fingerprint": 90,
    "title": 35,
    "artist": 30,
    "album": 10,
    "track_number": 5,
    "duration": 20,
}

_DURATION_TOLERANCE = 1.0  # seconds (±1s bucket)
_FUZZ_FLOOR = 0.80         # below this, a text signal counts as a mismatch

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")
_FEAT_RE = re.compile(r"(?i)(?<![A-Za-z])(?:featuring|feat|ft)(?![A-Za-z])")


class Confidence(str, Enum):
    DEFINITE = "definite"   # 99–100
    HIGH = "high"           # 90–98
    REVIEW = "review"       # 75–89
    NONE = "none"           # <75


def classify(score: int) -> Confidence:
    if score >= 99:
        return Confidence.DEFINITE
    if score >= 90:
        return Confidence.HIGH
    if score >= 75:
        return Confidence.REVIEW
    return Confidence.NONE


def dedupe_key(text: str | None) -> str:
    """Aggressive normalization used only for grouping/comparison keys."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold()
    text = _FEAT_RE.sub("feat", text)
    text = text.replace("&", "and")
    text = _PUNCT_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


@dataclass(slots=True)
class DupTrack:
    id: int
    path: str
    title: str | None
    artist: str | None
    album: str | None
    isrc: str | None
    mbid: str | None
    duration: float | None
    track_number: int | None
    codec: str | None
    bitrate: int | None
    sample_rate: int | None
    bit_depth: int | None
    file_size: int | None
    extension: str | None
    genre: str | None

    @classmethod
    def from_row(cls, row) -> "DupTrack":
        return cls(
            id=row["id"], path=row["path"], title=row["title"],
            artist=row["artist_name"], album=row["album_name"],
            isrc=row["isrc"], mbid=row["musicbrainz_track_id"],
            duration=row["duration"], track_number=row["track_number"],
            codec=row["codec"], bitrate=row["bitrate"],
            sample_rate=row["sample_rate"], bit_depth=row["bit_depth"],
            file_size=row["file_size"], extension=row["extension"],
            genre=row["genre"],
        )


@dataclass(slots=True)
class Match:
    a: int
    b: int
    score: int
    signals: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> Confidence:
        return classify(self.score)


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


class DuplicateDetector:
    def __init__(self, review_threshold: int = 75) -> None:
        self.review_threshold = review_threshold

    def candidate_groups(self, tracks: list[DupTrack]) -> list[list[DupTrack]]:
        """Union tracks sharing a strong key or a normalized title+artist."""
        uf = _UnionFind()
        buckets: dict[tuple, list[int]] = {}
        for t in tracks:
            uf.find(t.id)
            keys = []
            if t.mbid:
                keys.append(("mbid", t.mbid.strip().lower()))
            if t.isrc:
                keys.append(("isrc", t.isrc.strip().upper()))
            ta = (dedupe_key(t.title), dedupe_key(t.artist))
            if ta[0] and ta[1]:
                keys.append(("ta", *ta))
            for key in keys:
                buckets.setdefault(key, []).append(t.id)

        for ids in buckets.values():
            first = ids[0]
            for other in ids[1:]:
                uf.union(first, other)

        by_id = {t.id: t for t in tracks}
        components: dict[int, list[DupTrack]] = {}
        for t in tracks:
            components.setdefault(uf.find(t.id), []).append(by_id[t.id])
        return [c for c in components.values() if len(c) > 1]

    def score_pair(self, a: DupTrack, b: DupTrack) -> Match:
        # Verified-ID shortcut: identical MBID is a definite duplicate.
        if a.mbid and b.mbid and a.mbid.strip().lower() == b.mbid.strip().lower():
            return Match(a.id, b.id, 100, ["musicbrainz_track_id"])

        applicable = 0.0
        matched = 0.0
        signals: list[str] = []

        def consider(name: str, both: bool, frac: float) -> None:
            nonlocal applicable, matched
            if not both:
                return
            weight = WEIGHTS[name]
            applicable += weight
            matched += weight * frac
            if frac >= 0.99:
                signals.append(name)

        consider("isrc", bool(a.isrc and b.isrc),
                 1.0 if (a.isrc or "").upper() == (b.isrc or "").upper() else 0.0)
        consider("title", bool(a.title and b.title),
                 _text_frac(a.title, b.title))
        consider("artist", bool(a.artist and b.artist),
                 _text_frac(a.artist, b.artist))
        consider("album", bool(a.album and b.album),
                 _text_frac(a.album, b.album))
        consider("track_number", a.track_number is not None and b.track_number is not None,
                 1.0 if a.track_number == b.track_number else 0.0)
        consider("duration", a.duration is not None and b.duration is not None,
                 _duration_frac(a.duration, b.duration))

        score = round(100 * matched / applicable) if applicable else 0
        return Match(a.id, b.id, score, signals)

    def find_matches(self, tracks: list[DupTrack]) -> list[Match]:
        matches: list[Match] = []
        for group in self.candidate_groups(tracks):
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    match = self.score_pair(group[i], group[j])
                    if match.score >= self.review_threshold:
                        matches.append(match)
        return matches


def _text_frac(a: str, b: str) -> float:
    sim = similarity(dedupe_key(a), dedupe_key(b))
    return sim if sim >= _FUZZ_FLOOR else 0.0


def _duration_frac(a: float, b: float) -> float:
    delta = abs(a - b)
    if delta <= _DURATION_TOLERANCE:
        return 1.0
    if delta <= 2 * _DURATION_TOLERANCE:
        return 0.5
    return 0.0
