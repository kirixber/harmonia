"""Read tags and audio info from any supported file via Mutagen.

Mutagen's ``easy`` mode normalizes most tag names across FLAC/Vorbis,
ID3 (MP3), MP4/M4A/AAC/ALAC and Opus, so the per-format differences are
hidden here behind one :class:`TrackTags` shape.
"""

from __future__ import annotations

from pathlib import Path

from mutagen import File as MutagenFile
from mutagen import MutagenError

from ..models import AudioInfo, TrackTags

# Extensions Harmonia treats as audio. Kept here so the scanner and reader
# agree on what "an audio file" is.
AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".flac", ".opus", ".mp3", ".m4a", ".aac", ".alac", ".ogg", ".oga", ".wav"}
)

_LOSSLESS_EXT = frozenset({".flac", ".alac", ".wav"})


def is_audio_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def _first(value) -> str | None:
    """Mutagen easy tags are lists; take the first non-empty value."""
    if value is None:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_int(value) -> int | None:
    text = _first(value)
    if text is None:
        return None
    # Handles "3", "3/12", "03".
    head = text.split("/", 1)[0].strip()
    try:
        return int(head)
    except ValueError:
        return None


def _parse_total(value) -> int | None:
    text = _first(value)
    if text is None or "/" not in text:
        return None
    try:
        return int(text.split("/", 1)[1].strip())
    except (ValueError, IndexError):
        return None


def _parse_year(value) -> int | None:
    text = _first(value)
    if text is None:
        return None
    for token in (text[:4], text):
        try:
            year = int(token)
        except ValueError:
            continue
        if 1000 <= year <= 9999:
            return year
    return None


class MetadataReader:
    """Stateless reader. One instance is reused across a whole scan."""

    def read_tags(self, path: str | Path) -> TrackTags:
        try:
            audio = MutagenFile(path, easy=True)
        except (MutagenError, OSError):
            audio = None
        if audio is None or audio.tags is None:
            return TrackTags()

        get = audio.tags.get
        return TrackTags(
            title=_first(get("title")),
            artist=_first(get("artist")),
            album=_first(get("album")),
            album_artist=_first(get("albumartist")),
            genre=_first(get("genre")),
            composer=_first(get("composer")),
            track_number=_parse_int(get("tracknumber")),
            total_tracks=_parse_total(get("tracknumber")),
            disc_number=_parse_int(get("discnumber")),
            year=_parse_year(get("date") or get("year") or get("originaldate")),
            isrc=_first(get("isrc")),
            musicbrainz_track_id=_first(get("musicbrainz_trackid")),
            musicbrainz_album_id=_first(get("musicbrainz_albumid")),
            musicbrainz_artist_id=_first(get("musicbrainz_artistid")),
        )

    def read_info(self, path: str | Path) -> AudioInfo:
        ext = Path(path).suffix.lower()
        try:
            audio = MutagenFile(path)
        except (MutagenError, OSError):
            audio = None
        if audio is None or audio.info is None:
            return AudioInfo(codec=ext.lstrip(".") or None,
                             lossless=ext in _LOSSLESS_EXT)

        info = audio.info
        codec = type(audio).__name__.replace("MutagenFile", "") or ext.lstrip(".")
        bit_depth = getattr(info, "bits_per_sample", None)
        return AudioInfo(
            codec=codec,
            duration=getattr(info, "length", None),
            bitrate=getattr(info, "bitrate", None),
            sample_rate=getattr(info, "sample_rate", None),
            bit_depth=bit_depth if bit_depth else None,
            channels=getattr(info, "channels", None),
            lossless=ext in _LOSSLESS_EXT,
        )

    def read(self, path: str | Path) -> tuple[TrackTags, AudioInfo]:
        return self.read_tags(path), self.read_info(path)
