"""Pick the file to keep within a duplicate cluster.

Ranking order from ``duplicate_detection.md``: lossless beats lossy, then
bit depth, sample rate, bitrate, duration, metadata completeness, file size.
Returns the keeper plus a short human reason.
"""

from __future__ import annotations

from .detector import DupTrack

_LOSSLESS_EXT = {".flac", ".alac", ".wav", ".aiff", ".ape", ".wv"}

_META_FIELDS = ("title", "artist", "album", "track_number", "genre", "isrc", "mbid")


def is_lossless(track: DupTrack) -> bool:
    if track.extension and track.extension.lower() in _LOSSLESS_EXT:
        return True
    codec = (track.codec or "").lower()
    return any(tag in codec for tag in ("flac", "alac", "wav", "ape"))


def _completeness(track: DupTrack) -> int:
    return sum(1 for f in _META_FIELDS if getattr(track, f))


def quality_key(track: DupTrack) -> tuple:
    """Higher tuple == better keeper."""
    return (
        1 if is_lossless(track) else 0,
        track.bit_depth or 0,
        track.sample_rate or 0,
        track.bitrate or 0,
        track.duration or 0.0,
        _completeness(track),
        track.file_size or 0,
    )


def choose_keeper(tracks: list[DupTrack]) -> tuple[DupTrack, str]:
    keeper = max(tracks, key=quality_key)
    reasons = []
    if is_lossless(keeper):
        reasons.append("lossless")
    if keeper.bit_depth:
        reasons.append(f"{keeper.bit_depth}-bit")
    if keeper.sample_rate:
        reasons.append(f"{keeper.sample_rate} Hz")
    if keeper.bitrate:
        reasons.append(f"{keeper.bitrate // 1000} kbps")
    reason = "highest quality" + (f" ({', '.join(reasons)})" if reasons else "")
    return keeper, reason
