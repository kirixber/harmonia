from harmonia.core.duplicates import build_report, dedupe_key, similarity
from harmonia.core.duplicates.detector import (
    Confidence,
    DupTrack,
    DuplicateDetector,
    classify,
)
from harmonia.core.duplicates.quality import choose_keeper, is_lossless
from harmonia.core.library import Library


def _t(tid, **kw):
    base = dict(
        id=tid, path=f"/m/{tid}.flac", title=None, artist=None, album=None,
        isrc=None, mbid=None, duration=None, track_number=None, codec=None,
        bitrate=None, sample_rate=None, bit_depth=None, file_size=None,
        extension=".flac", genre=None,
    )
    base.update(kw)
    return DupTrack(**base)


def test_dedupe_key_normalization():
    assert dedupe_key("The Weeknd") == dedupe_key("THE WEEKND")
    assert dedupe_key("Beyoncé") == dedupe_key("Beyonce")
    assert dedupe_key("A & B feat. C") == dedupe_key("a and b feat c")


def test_classify_thresholds():
    assert classify(100) is Confidence.DEFINITE
    assert classify(95) is Confidence.HIGH
    assert classify(80) is Confidence.REVIEW
    assert classify(50) is Confidence.NONE


def test_identical_mbid_is_definite():
    det = DuplicateDetector()
    a = _t(1, title="X", artist="Y", mbid="mb-123")
    b = _t(2, title="Different", artist="Other", mbid="mb-123")
    match = det.score_pair(a, b)
    assert match.score == 100
    assert match.confidence is Confidence.DEFINITE


def test_same_title_artist_duration_high_confidence():
    det = DuplicateDetector()
    a = _t(1, title="Song", artist="Artist", album="A", duration=180.0, track_number=3)
    b = _t(2, title="Song", artist="Artist", album="A", duration=180.4, track_number=3)
    match = det.score_pair(a, b)
    assert match.score >= 90


def test_unrelated_tracks_not_grouped():
    det = DuplicateDetector()
    a = _t(1, title="Alpha", artist="One")
    b = _t(2, title="Beta", artist="Two")
    assert det.candidate_groups([a, b]) == []


def test_quality_keeper_prefers_lossless():
    flac = _t(1, extension=".flac", bit_depth=16, sample_rate=44100, file_size=30_000_000)
    mp3 = _t(2, extension=".mp3", bitrate=320000, file_size=8_000_000)
    assert is_lossless(flac) and not is_lossless(mp3)
    keeper, reason = choose_keeper([mp3, flac])
    assert keeper.id == flac.id
    assert "lossless" in reason


def test_build_report_clusters():
    tracks = [
        _t(1, title="Song", artist="Artist", album="A", duration=200.0),
        _t(2, title="Song", artist="Artist", album="A", duration=200.0),
        _t(3, title="Lonely", artist="Nobody", duration=99.0),
    ]
    report = build_report(tracks)
    assert len(report.clusters) == 1
    assert report.clusters[0].confidence in (Confidence.HIGH, Confidence.DEFINITE)
    assert report.summary()["total_clusters"] == 1


def test_library_duplicate_report_end_to_end(music_root):
    import shutil

    # Duplicate an existing file under a new name in the same library.
    original = next(music_root.rglob("01 - First.flac"))
    shutil.copy2(original, original.parent / "01 - First (copy).flac")

    with Library(":memory:") as lib:
        lib.scan(music_root)
        report = lib.duplicate_report()
        assert len(report.clusters) >= 1
        # The two identical files land in one cluster.
        sizes = [len(c.tracks) for c in report.clusters]
        assert max(sizes) >= 2
