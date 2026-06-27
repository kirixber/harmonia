"""Audio quality analysis: fingerprints, replaygain, spectral analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ...database import Database


@dataclass(slots=True)
class Fingerprint:
    """Acoustic fingerprint result."""
    track_id: int
    acoustid: Optional[str] = None
    chromaprint: Optional[str] = None
    confidence: float = 0.0


@dataclass(slots=True)
class ReplayGain:
    """ReplayGain values."""
    track_gain: Optional[float] = None
    track_peak: Optional[float] = None
    album_gain: Optional[float] = None
    album_peak: Optional[float] = None


@dataclass(slots=True)
class QualityMetrics:
    """Comprehensive quality metrics for a track."""
    track_id: int
    codec: str
    bitrate: int
    sample_rate: int
    bit_depth: int
    channels: int
    duration: float
    dynamic_range: Optional[float] = None
    clipping: Optional[float] = None
    true_peak: Optional[float] = None


class QualityEngine:
    """Audio quality analysis engine."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def compute_fingerprint(self, track_id: int) -> Fingerprint:
        """Compute acoustic fingerprint for a track (requires fpcalc/chromaprint)."""
        row = self.db.get_track(track_id)
        if not row:
            return Fingerprint(track_id=track_id)

        path = Path(row["path"])
        if not path.exists():
            return Fingerprint(track_id=track_id)

        # Try to use pyacoustid / fpcalc if available
        try:
            import acoustid
            import chromaprint

            duration, fp = chromaprint.fingerprint_file(str(path))
            matches = acoustid.match(fp, duration)
            if matches:
                best = matches[0]
                return Fingerprint(
                    track_id=track_id,
                    acoustid=best[1],
                    chromaprint=fp,
                    confidence=best[0],
                )
        except ImportError:
            pass
        except Exception:
            pass

        return Fingerprint(track_id=track_id)

    def compute_replaygain(self, track_id: int) -> ReplayGain:
        """Compute ReplayGain for a track (requires audio analysis)."""
        row = self.db.get_track(track_id)
        if not row:
            return ReplayGain()

        path = Path(row["path"])
        if not path.exists():
            return ReplayGain()

        # Try to use mutagen or other library for ReplayGain
        try:
            from mutagen import File
            audio = File(str(path))
            if audio and hasattr(audio, "tags"):
                # This is a simplified placeholder
                pass
        except Exception:
            pass

        return ReplayGain()

    def analyze_quality(self, track_id: int) -> QualityMetrics:
        """Analyze audio quality metrics for a track."""
        row = self.db.get_track(track_id)
        if not row:
            return QualityMetrics(track_id=track_id, codec="", bitrate=0, sample_rate=0,
                                 bit_depth=0, channels=0, duration=0)

        # Try to use mutagen for detailed analysis
        try:
            from mutagen import File
            audio = File(row["path"])
            if audio and audio.info:
                return QualityMetrics(
                    track_id=track_id,
                    codec=audio.info.__class__.__name__,
                    bitrate=getattr(audio.info, "bitrate", 0),
                    sample_rate=getattr(audio.info, "sample_rate", 0),
                    bit_depth=getattr(audio.info, "bits_per_sample", 0),
                    channels=getattr(audio.info, "channels", 0),
                    duration=getattr(audio.info, "length", 0),
                )
        except Exception:
            pass

        return QualityMetrics(
            track_id=track_id,
            codec=row["codec"] or "",
            bitrate=row["bitrate"] or 0,
            sample_rate=row["sample_rate"] or 0,
            bit_depth=row["bit_depth"] or 0,
            channels=row["channels"] or 0,
            duration=row["duration"] or 0,
        )

    def compare_quality(self, track_ids: list[int]) -> list[QualityMetrics]:
        """Compare quality metrics across tracks."""
        return [self.analyze_quality(tid) for tid in track_ids]

    def best_quality(self, track_ids: list[int]) -> Optional[int]:
        """Return the track ID with the best quality (highest bitrate, lossless preferred)."""
        metrics = self.compare_quality(track_ids)
        if not metrics:
            return None

        def quality_score(m: QualityMetrics) -> tuple:
            # Lossless first, then highest bitrate
            is_lossless = m.codec.upper() in ("FLAC", "ALAC", "APE", "WAVPACK", "WAV", "AIFF")
            return (is_lossless, m.bitrate, m.sample_rate, m.bit_depth)

        return max(metrics, key=quality_score).track_id