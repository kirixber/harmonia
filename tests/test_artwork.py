"""Tests for artwork caching and embedding.

The embed tests synthesize real FLAC files with ffmpeg and skip cleanly
when ffmpeg is unavailable (see ``conftest.music_root``).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mutagen.flac import FLAC

from harmonia.core.artwork import ArtworkEngine, EmbedResult
from harmonia.core.library import Library
from harmonia.database import Database
from harmonia.providers import ProviderManager
from harmonia.providers.dummy import DummyArtworkProvider, get_dummy_providers


def _jpeg_bytes() -> bytes:
    async def run() -> bytes:
        with Database(":memory:") as db:
            pm = ProviderManager(db)
            for p in get_dummy_providers():
                pm.register(p)
            await pm.initialize_all()
            candidates = await pm.search_artwork("A", "B")
            data = await pm.download_artwork(candidates[0])
            await pm.shutdown_all()
            return data

    return asyncio.run(run())


def test_embed_missing_track_returns_error():
    with Database(":memory:") as db:
        pm = ProviderManager(db)
        engine = ArtworkEngine(db, pm)
        result = engine.embed_artwork("/no/such/file.flac", b"\xff\xd8\xff")
        assert not result.ok
        assert result.error == "track not found"


def test_embed_empty_data_returns_error(tmp_path):
    track = tmp_path / "x.flac"
    track.write_bytes(b"not really flac")
    with Database(":memory:") as db:
        engine = ArtworkEngine(db, ProviderManager(db))
        result = engine.embed_artwork(track, b"")
        assert not result.ok
        assert result.error == "empty image data"


def test_embed_flac_writes_picture_and_backs_up(music_root):
    flac_path = next(music_root.rglob("*.flac"))
    data = _jpeg_bytes()

    with Database(":memory:") as db:
        engine = ArtworkEngine(db, ProviderManager(db))

        # No cover to start with.
        assert FLAC(str(flac_path)).pictures == []

        result = engine.embed_artwork(flac_path, data, backup=True)
        assert result.ok and result.embedded
        assert result.backup_path and Path(result.backup_path).exists()

        pics = FLAC(str(flac_path)).pictures
        assert len(pics) == 1
        assert pics[0].data == data
        assert pics[0].type == 3  # front cover


def test_embed_dry_run_does_not_write(music_root):
    flac_path = next(music_root.rglob("*.flac"))
    data = _jpeg_bytes()
    with Database(":memory:") as db:
        engine = ArtworkEngine(db, ProviderManager(db))
        result = engine.embed_artwork(flac_path, data, dry_run=True, backup=True)
        assert result.embedded and result.backup_path is None
        assert FLAC(str(flac_path)).pictures == []


def test_embed_only_if_missing_skips_existing(music_root):
    flac_path = next(music_root.rglob("*.flac"))
    data = _jpeg_bytes()
    with Database(":memory:") as db:
        engine = ArtworkEngine(db, ProviderManager(db))
        first = engine.embed_artwork(flac_path, data, backup=False)
        assert first.embedded
        second = engine.embed_artwork(
            flac_path, data, backup=False, only_if_missing=True
        )
        assert second.skipped and not second.embedded


def test_library_embed_for_indexed_track(music_root):
    data = _jpeg_bytes()
    with Library(":memory:") as lib:
        lib.scan(music_root)
        track_id = lib.db.iter_tracks()[0]["id"]
        result = lib.embed_artwork(track_id, data, backup=False)
        assert result.ok and result.embedded
        path = lib.db.get_track(track_id)["path"]
        assert FLAC(path).pictures


def test_library_embed_unknown_track_id():
    with Library(":memory:") as lib:
        result = lib.embed_artwork(999, b"\xff\xd8\xff", backup=False)
        assert not result.ok
        assert "no track" in result.error
