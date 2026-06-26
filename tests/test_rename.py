from pathlib import Path

from harmonia.core.library import Library
from harmonia.core.metadata.rename import (
    RenameStatus,
    Renamer,
    resolve_template,
    sanitize_component,
)
from harmonia.core.models import TrackTags


def test_sanitize_strips_illegal():
    assert sanitize_component('AC/DC: Back') == "AC_DC_ Back"
    assert sanitize_component("   ") == "Unknown"
    assert sanitize_component("name...") == "name"


def test_named_template_resolution():
    assert resolve_template("artist-title") == "{artist} - {title}"
    assert resolve_template("{title}") == "{title}"  # passthrough


def test_plan_missing_field():
    plan = Renamer().plan("/m/x.flac", TrackTags(title="T"), "{artist} - {title}")
    assert plan.status is RenameStatus.MISSING_FIELDS


def test_plan_flat_rename(tmp_path):
    f = tmp_path / "old.flac"
    f.write_bytes(b"x")
    tags = TrackTags(title="Song", artist="Artist")
    plan = Renamer().plan(f, tags, "artist-title")
    assert plan.status is RenameStatus.RENAME
    assert Path(plan.new_path).name == "Artist - Song.flac"
    assert Path(plan.new_path).parent == f.parent


def test_conflict_not_overwritten(tmp_path):
    src = tmp_path / "old.flac"
    src.write_bytes(b"x")
    (tmp_path / "Artist - Song.flac").write_bytes(b"y")
    plan = Renamer().plan(src, TrackTags(title="Song", artist="Artist"), "artist-title")
    assert plan.status is RenameStatus.CONFLICT
    assert Renamer().apply(plan) is False


def test_library_rename_moves_and_updates_db(music_root, tmp_path):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        tid = lib.db.iter_tracks()[0]["id"]
        out = tmp_path / "organized"
        plan = lib.rename_track(tid, "artist-album-track-title", base_dir=out)
        assert plan.status is RenameStatus.RENAME
        assert Path(plan.new_path).exists()
        # DB now points at the new path.
        assert lib.db.get_track(tid)["path"] == plan.new_path


def test_library_rename_all_dry_run_moves_nothing(music_root, tmp_path):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        plans = lib.rename_all("artist-album-track-title", base_dir=tmp_path / "x")
        assert all(p.status in (RenameStatus.RENAME, RenameStatus.UNCHANGED) for p in plans)
        # Dry run: no destination created.
        assert not (tmp_path / "x").exists()
