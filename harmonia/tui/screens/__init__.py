"""TUI screens."""

from .main_menu import MainMenuScreen
from .scan import ScanScreen
from .artwork import ArtworkScreen
from .metadata import MetadataScreen
from .duplicates import DuplicatesScreen
from .reports import ReportsScreen
from .settings import SettingsScreen

__all__ = [
    "MainMenuScreen",
    "ScanScreen",
    "ArtworkScreen",
    "MetadataScreen",
    "DuplicatesScreen",
    "ReportsScreen",
    "SettingsScreen",
]
