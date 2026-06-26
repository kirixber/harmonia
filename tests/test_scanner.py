import os

from harmonia.core.library import Library


def test_scan_indexes_library(music_root):
    with Library(":memory:") as lib:
        result = lib.scan(music_root)
        assert result.new_files == 3
        assert result.updated_files == 0
        stats = lib.stats()
        assert stats["tracks"] == 3
        assert stats["artists"] == 2   # Artist A, Artist B
        assert stats["albums"] == 2    # Album One, Album Two


def test_incremental_skip_unchanged(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        second = lib.scan(music_root)
        assert second.new_files == 0
        assert second.updated_files == 0
        assert second.scanned_files == 3


def test_modified_file_is_updated(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        target = next(music_root.rglob("*.flac"))
        # Bump mtime forward so the scanner treats it as changed.
        st = target.stat()
        os.utime(target, (st.st_atime, st.st_mtime + 10))
        result = lib.scan(music_root)
        assert result.updated_files == 1
        assert result.new_files == 0


def test_removed_file_is_pruned(music_root):
    with Library(":memory:") as lib:
        lib.scan(music_root)
        target = next(music_root.rglob("*.flac"))
        target.unlink()
        result = lib.scan(music_root)
        assert result.removed_files == 1
        assert lib.stats()["tracks"] == 2
