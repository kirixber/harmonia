import asyncio

from harmonia.core.artwork import ArtworkEngine
from harmonia.database import Database
from harmonia.providers import ProviderCategory, ProviderManager
from harmonia.providers.dummy import get_dummy_providers


def test_provider_cache_roundtrip_and_expiry():
    with Database(":memory:") as db:
        assert db.provider_cache_get("artwork", "h1", 90) is None
        db.provider_cache_set("artwork", "h1", '{"x":1}')
        assert db.provider_cache_get("artwork", "h1", 90) == '{"x":1}'
        # Zero-day max age expires immediately and prunes the row.
        assert db.provider_cache_get("artwork", "h1", 0) is None
        assert db.provider_cache_get("artwork", "h1", 90) is None


def test_manager_search_merges_and_caches():
    async def run():
        with Database(":memory:") as db:
            pm = ProviderManager(db)
            for p in get_dummy_providers():
                pm.register(p)
            await pm.initialize_all()

            results = await pm.search_artwork("Artist", "Album")
            assert results and results[0].provider == "dummy"

            # Second call is served from the SQLite metadata cache.
            cached = await pm.search_artwork("Artist", "Album")
            assert [c.url for c in cached] == [c.url for c in results]
            await pm.shutdown_all()

    asyncio.run(run())


def test_download_returns_validated_bytes():
    async def run():
        with Database(":memory:") as db:
            pm = ProviderManager(db)
            for p in get_dummy_providers():
                pm.register(p)
            await pm.initialize_all()
            candidates = await pm.search_artwork("A", "B")
            data = await pm.download_artwork(candidates[0])
            assert data and data.startswith(b"\xff\xd8\xff")  # JPEG magic
            # No image bytes leaked into the provider cache table.
            count = db.conn.execute(
                "SELECT COUNT(*) FROM provider_cache WHERE response_json LIKE '%\xff%'"
            ).fetchone()[0]
            assert count == 0

    asyncio.run(run())


def test_artwork_engine_stores_to_disk_by_content_hash(tmp_path, monkeypatch):
    import hashlib

    async def run():
        with Database(":memory:") as db:
            pm = ProviderManager(db)
            for p in get_dummy_providers():
                pm.register(p)
            await pm.initialize_all()
            engine = ArtworkEngine(db, pm)
            results = await engine.fetch_and_store("Artist", "Album", limit=1)
            assert results and results[0].sha256
            r = results[0]
            # Stored on disk, keyed by content hash, recorded in DB.
            from pathlib import Path
            assert Path(r.local_path).exists()
            assert engine.get_cached_artwork(r.sha256) == Path(r.local_path)
            # Hash actually matches file bytes.
            data = Path(r.local_path).read_bytes()
            assert hashlib.sha256(data).hexdigest() == r.sha256

    asyncio.run(run())
