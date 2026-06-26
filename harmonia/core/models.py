"""Unified domain models shared across every layer.

These dataclasses are the format-independent vocabulary of Harmonia. The
metadata engine produces :class:`TrackTags`/:class:`AudioInfo` from any
supported file; the database persists them; frontends render them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AudioInfo:
    """Technical properties read from the audio stream itself."""

    codec: str | None = None
    duration: float | None = None          # seconds
    bitrate: int | None = None             # bits per second
    sample_rate: int | None = None         # Hz
    bit_depth: int | None = None           # bits per sample (lossless)
    channels: int | None = None
    lossless: bool = False


@dataclass(slots=True)
class TrackTags:
    """Editorial metadata, normalized away from format-specific tag names."""

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    album_artist: str | None = None
    genre: str | None = None
    composer: str | None = None
    track_number: int | None = None
    total_tracks: int | None = None
    disc_number: int | None = None
    year: int | None = None
    isrc: str | None = None
    musicbrainz_track_id: str | None = None
    musicbrainz_album_id: str | None = None
    musicbrainz_artist_id: str | None = None


@dataclass(slots=True)
class Track:
    """A persisted audio file: its location, hashes, tags and audio info."""

    path: str
    filename: str
    extension: str
    file_size: int
    modified_time: float
    sha256: str | None = None
    tags: TrackTags = field(default_factory=TrackTags)
    info: AudioInfo = field(default_factory=AudioInfo)
    id: int | None = None
    artist_id: int | None = None
    album_id: int | None = None
    last_scanned: str | None = None
