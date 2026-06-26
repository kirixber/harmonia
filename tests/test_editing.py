from harmonia.core.library import Library
from harmonia.core.metadata.reader import MetadataReader


def _first_track_id(lib):
    return lib.db.iter_tracks()[0]["id"]


def test_edit_track_writes_verifies_and_refreshes(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        tid = _first_track_id(lib)
        row = lib.db.get_track(tid)
        path = row["path"]

        outcome = lib.edit_track(tid, {"title": "Renamed Title", "genre": "Jazz"})
        assert outcome.ok
        assert outcome.write.verified

        # File really changed.
        assert MetadataReader().read_tags(path).title == "Renamed Title"
        # DB row refreshed.
        assert lib.db.get_track(tid)["title"] == "Renamed Title"
        # History recorded both fields.
        fields = {h["field"] for h in lib.db.tag_history(tid)}
        assert {"title", "genre"} <= fields


def test_dry_run_does_not_write(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        tid = _first_track_id(lib)
        path = lib.db.get_track(tid)["path"]
        before = MetadataReader().read_tags(path).title

        outcome = lib.edit_track(tid, {"title": "Should Not Persist"}, dry_run=True)
        assert outcome.write.changes  # diff computed
        assert not outcome.write.written
        assert MetadataReader().read_tags(path).title == before


def test_edit_blocked_when_clearing_required_field(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        tid = _first_track_id(lib)
        outcome = lib.edit_track(tid, {"title": ""})
        assert outcome.blocked
        assert outcome.write is None
        assert any(i.field == "title" for i in outcome.issues)


def test_unknown_field_rejected(music_root):
    import pytest

    with Library(":memory:") as lib:
        lib.scan(music_root)
        tid = _first_track_id(lib)
        with pytest.raises(ValueError):
            lib.edit_track(tid, {"bogus": "x"})


def test_normalize_track(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        tid = _first_track_id(lib)
        # Force an ugly value, then normalize.
        lib.edit_track(tid, {"artist": "THE  WEEKND"}, force=True)
        outcome = lib.normalize_track(tid)
        assert outcome.ok
        assert lib.db.get_track(tid)["title"] is not None
        from harmonia.core.metadata.reader import MetadataReader as R
        assert R().read_tags(lib.db.get_track(tid)["path"]).artist == "The Weeknd"
