from harmonia.core.metadata.validate import Severity, valid_isrc, validate_tags
from harmonia.core.models import TrackTags


def test_isrc_format():
    assert valid_isrc("USRC17607839")
    assert valid_isrc("us-rc1-76-07839")  # separators tolerated
    assert not valid_isrc("ABC123")


def test_clean_tags_have_no_issues():
    tags = TrackTags(title="Song", artist="Artist", album="Album",
                     track_number=1, year=2020, isrc="USRC17607839")
    assert validate_tags(tags) == []


def test_missing_required_fields():
    issues = validate_tags(TrackTags())
    fields = {(i.field, i.severity) for i in issues}
    assert ("title", Severity.ERROR) in fields
    assert ("artist", Severity.ERROR) in fields
    assert ("album", Severity.WARNING) in fields


def test_bad_values_flagged():
    tags = TrackTags(title="t", artist="a", album="b",
                     track_number=0, year=3000, isrc="BAD")
    flagged = {i.field for i in validate_tags(tags)}
    assert {"track_number", "year", "isrc"} <= flagged
