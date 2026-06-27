"""TUI constants."""

from .. import __version__

MENU_ENTRIES = [
    ("1", "Scan Library", "ScanScreen"),
    ("2", "Artwork", "ArtworkScreen"),
    ("3", "Metadata", "MetadataScreen"),
    ("4", "Duplicates", "DuplicatesScreen"),
    ("5", "Audio Quality", None),
    ("6", "Reports", "ReportsScreen"),
    ("7", "Settings", "SettingsScreen"),
]

__all__ = ["MENU_ENTRIES"]
