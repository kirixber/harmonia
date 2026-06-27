from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, DataTable

from .base import BaseScreen
from ...utils.paths import database_path, home_dir, logs_dir


class SettingsScreen(BaseScreen):
    TITLE = "Settings"

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-area"):
            yield Static("Settings", classes="screen-title")
            yield DataTable(id="settings-table")
            yield Static(
                "Editable settings arrive with provider config in v0.4.",
                id="settings-note",
            )

    def on_mount(self) -> None:
        dt = self.query_one("#settings-table", DataTable)
        dt.add_columns("Key", "Value")
        dt.add_row("Home", str(home_dir()))
        dt.add_row("Database", str(database_path()))
        dt.add_row("Logs", str(logs_dir()))
