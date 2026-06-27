"""TUI screens."""

from .main_menu import MainMenuScreen
from .scan import ScanScreen
from .artwork import ArtworkScreen
from .metadata import MetadataScreen
from .duplicates import DuplicatesScreen
from .quality import QualityScreen
from .reports import ReportsScreen
from .settings import SettingsScreen

__all__ = [
    "MainMenuScreen",
    "ScanScreen",
    "ArtworkScreen",
    "MetadataScreen",
    "DuplicatesScreen",
    "QualityScreen",
    "ReportsScreen",
    "SettingsScreen",
]
