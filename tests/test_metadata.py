from harmonia.core.metadata.reader import (
    MetadataReader,
    _parse_int,
    _parse_total,
    _parse_year,
    is_audio_file,
)


def test_parsers():
    assert _parse_int("3/12") == 3
    assert _parse_total("3/12") == 12
    assert _parse_int("07") == 7
    assert _parse_total("5") is None
    assert _parse_year("2002-03-01") == 2002
    assert _parse_year("nonsense") is None


def test_is_audio_file():
    assert is_audio_file("song.FLAC")
    assert is_audio_file("a.opus")
    assert not is_audio_file("cover.jpg")


def test_reader_reads_flac_tags_and_info(music_root):
    reader = MetadataReader()
    flac = next(music_root.rglob("01 - First.flac"))
    tags, info = reader.read(flac)
    assert tags.title == "First"
    assert tags.artist == "Artist A"
    assert tags.album == "Album One"
    assert tags.track_number == 1
    assert tags.total_tracks == 2
    assert tags.year == 2020
    assert info.lossless is True
    assert info.duration and info.duration > 0
    assert info.sample_rate and info.sample_rate > 0
