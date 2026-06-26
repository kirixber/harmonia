from harmonia.core.metadata.normalize import (
    normalize_feat,
    normalize_tags,
    normalize_text,
    normalize_whitespace,
)
from harmonia.core.models import TrackTags


def test_whitespace():
    assert normalize_whitespace("  a   b  ") == "a b"


def test_feat_variants():
    assert normalize_feat("Song ft Drake") == "Song feat. Drake"
    assert normalize_feat("Song FEAT. Drake") == "Song feat. Drake"
    assert normalize_feat("Song featuring Drake") == "Song feat. Drake"


def test_recase_only_uniform_case():
    assert normalize_text("IMAGINE DRAGONS") == "Imagine Dragons"
    assert normalize_text("the dark side of the moon") == "The Dark Side of the Moon"
    # Mixed/intentional case is preserved.
    assert normalize_text("deadmau5") == "deadmau5"
    assert normalize_text("will.i.am") == "will.i.am"


def test_normalize_tags_reports_changes():
    tags = TrackTags(title="HELLO  WORLD", artist="Adele", album="25")
    new, changes = normalize_tags(tags)
    assert new.title == "Hello World"
    assert new.artist == "Adele"  # unchanged
    fields_changed = {c.field for c in changes}
    assert fields_changed == {"title"}
