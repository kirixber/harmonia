import json

from harmonia.core.library import Library


def test_metadata_report_flags_issues(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        report = lib.metadata_report()
        summary = report.summary
        # Fixtures have genres on only one track and no ISRCs → some missing.
        assert summary["missing_genre"] >= 1
        # All fixtures have title/artist/album set.
        assert summary["missing_title"] == 0
        assert summary["missing_artist"] == 0


def test_duplicate_isrc_detected(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        ids = [t["id"] for t in lib.db.iter_tracks()]
        # Give two tracks the same ISRC.
        lib.edit_track(ids[0], {"isrc": "USRC17607839"}, force=True)
        lib.edit_track(ids[1], {"isrc": "USRC17607839"}, force=True)
        report = lib.metadata_report()
        assert report.summary["duplicate_isrc"] == 2


def test_report_exports(music_root, tmp_path):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        report = lib.metadata_report()

        jpath = tmp_path / "r.json"
        cpath = tmp_path / "r.csv"
        report.to_json(jpath)
        report.to_csv(cpath)

        data = json.loads(jpath.read_text())
        assert data["total"] == report.total
        assert "summary" in data
        assert cpath.read_text().splitlines()[0] == "category,track_id,detail,path"
