"""Main TUI application."""

from __future__ import annotations

import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static

from .. import __version__
from .constants import MENU_ENTRIES
from .screens import (
    MainMenuScreen,
    ScanScreen,
    ArtworkScreen,
    MetadataScreen,
    DuplicatesScreen,
    ReportsScreen,
    SettingsScreen,
)

SCREEN_MAP = {
    "ScanScreen": ScanScreen,
    "ArtworkScreen": ArtworkScreen,
    "MetadataScreen": MetadataScreen,
    "DuplicatesScreen": DuplicatesScreen,
    "ReportsScreen": ReportsScreen,
    "SettingsScreen": SettingsScreen,
}


class HarmoniaApp(App[None]):
    TITLE = f"HARMONIA v{__version__}"
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "back", "Back", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())

    def action_back(self) -> None:
        if len(self.screen_stack) > 2:
            self.pop_screen()

    def open_screen(self, screen_name: str) -> None:
        screen_class = SCREEN_MAP.get(screen_name)
        if screen_class:
            self.push_screen(screen_class())


def main() -> None:
    app = HarmoniaApp()
    app.run()
    sys.exit(0)
