from harmonia.core.models import Track
from harmonia.database import Database
from harmonia.database.schema import LATEST_VERSION


def test_migration_sets_version():
    with Database(":memory:") as db:
        version = db.conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == LATEST_VERSION


def test_artist_album_dedup():
    with Database(":memory:") as db:
        a1 = db.get_or_create_artist("Boards of Canada")
        a2 = db.get_or_create_artist("boards of canada")  # case-insensitive
        assert a1 == a2

        al1 = db.get_or_create_album("Geogaddi", artist_id=a1, year=2002,
                                     album_artist="Boards of Canada")
        al2 = db.get_or_create_album("Geogaddi", artist_id=a1, year=2002,
                                     album_artist="Boards of Canada")
        assert al1 == al2


def test_upsert_track_roundtrip_and_stats():
    with Database(":memory:") as db:
        track = Track(
            path="/music/a.flac", filename="a.flac", extension=".flac",
            file_size=100, modified_time=123.0, sha256="abc",
        )
        track.tags.title = "A"
        track.info.duration = 60.0
        tid = db.upsert_track(track)
        assert tid > 0

        # Upsert again with same path updates, not duplicates.
        track.file_size = 200
        tid2 = db.upsert_track(track)
        assert tid2 == tid

        stats = db.stats()
        assert stats["tracks"] == 1
        assert stats["total_size"] == 200
        assert stats["total_duration"] == 60.0


def test_config_kv():
    with Database(":memory:") as db:
        assert db.config_get("missing", "fallback") == "fallback"
        db.config_set("theme", "dark")
        assert db.config_get("theme") == "dark"


def test_search_tracks_by_title_artist_album():
    with Database(":memory:") as db:
        artist = db.get_or_create_artist("Daft Punk")
        album = db.get_or_create_album("Discovery", artist_id=artist, year=2001,
                                       album_artist="Daft Punk")
        track = Track(
            path="/music/one_more_time.flac", filename="one_more_time.flac",
            extension=".flac", file_size=100, modified_time=1.0,
        )
        track.tags.title = "One More Time"
        track.artist_id = artist
        track.album_id = album
        db.upsert_track(track)

        # Match by title (case-insensitive, partial).
        by_title = db.search_tracks("more time")
        assert [r["title"] for r in by_title] == ["One More Time"]
        assert by_title[0]["artist_name"] == "Daft Punk"
        assert by_title[0]["album_name"] == "Discovery"

        # Match by artist and by album too.
        assert len(db.search_tracks("daft")) == 1
        assert len(db.search_tracks("discovery")) == 1

        # No false positives.
        assert db.search_tracks("nonexistent") == []


def test_search_tracks_finds_untagged_by_filename():
    """A file with no tags (title NULL) is still findable by its filename."""
    with Database(":memory:") as db:
        track = Track(
            path="/music/mystery_track.flac", filename="mystery_track.flac",
            extension=".flac", file_size=10, modified_time=1.0,
        )
        # No tags set at all.
        db.upsert_track(track)

        assert db.search_tracks("mystery")  # matched by filename
        assert db.search_tracks("")          # blank query lists everything
        by_path = db.search_tracks("/music/")
        assert len(by_path) == 1
