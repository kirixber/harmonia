"""Tests for the audio quality engine.

Uses the ffmpeg-backed ``music_root`` fixture; skips when ffmpeg is absent.
"""

from __future__ import annotations

from harmonia.core.library import Library
from harmonia.core.quality import QualityEngine, QualityMetrics
from harmonia.database import Database


def test_analyze_unknown_track_is_empty():
    with Database(":memory:") as db:
        engine = QualityEngine(db)
        m = engine.analyze_quality(123)
        assert isinstance(m, QualityMetrics)
        assert m.track_id == 123
        assert m.codec == "" and m.bitrate == 0


def test_analyze_reads_real_flac_info(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        track_id = lib.db.iter_tracks()[0]["id"]
        m = lib.analyze_quality(track_id)
        assert m.track_id == track_id
        assert m.sample_rate > 0
        assert m.channels >= 1
        assert m.duration > 0


def test_compare_and_best_quality(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        ids = [r["id"] for r in lib.db.iter_tracks()]
        metrics = lib.compare_quality(ids)
        assert len(metrics) == len(ids)
        best = lib.best_quality(ids)
        assert best in ids


def test_best_quality_empty_returns_none():
    with Database(":memory:") as db:
        engine = QualityEngine(db)
        assert engine.best_quality([]) is None


def test_best_quality_prefers_lossless():
    with Database(":memory:") as db:
        engine = QualityEngine(db)

        def fake_analyze(track_id: int) -> QualityMetrics:
            table = {
                1: QualityMetrics(1, "MP3", 320000, 44100, 0, 2, 200.0),
                2: QualityMetrics(2, "FLAC", 900000, 44100, 16, 2, 200.0),
            }
            return table[track_id]

        engine.analyze_quality = fake_analyze  # type: ignore[assignment]
        assert engine.best_quality([1, 2]) == 2
