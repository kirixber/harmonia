from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Static, DataTable

from .base import BaseScreen
from ...utils.format import human_duration, human_size
from ...utils.paths import database_path, home_dir, logs_dir


class ReportsScreen(BaseScreen):
    TITLE = "Reports"

    def compose(self) -> ComposeResult:
        with Vertical(id="reports-area"):
            yield Static("Library Report", classes="screen-title")
            yield Button("Refresh", id="report-btn", variant="primary")
            yield DataTable(id="report-results")
            yield Static(id="report-scan-info")

    def on_mount(self) -> None:
        dt = self.query_one("#report-results", DataTable)
        dt.add_columns("Metric", "Value")
        self._refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "report-btn":
            self._refresh()

    def _refresh(self) -> None:
        stats = self.library.stats()
        dt = self.query_one("#report-results", DataTable)
        dt.clear()
        dt.add_row("Tracks", f"{stats['tracks']:,}")
        dt.add_row("Artists", f"{stats['artists']:,}")
        dt.add_row("Albums", f"{stats['albums']:,}")
        dt.add_row("Total time", human_duration(stats["total_duration"]))
        dt.add_row("Total size", human_size(stats["total_size"]))

        last = self.library.last_scan()
        info = self.query_one("#report-scan-info", Static)
        if last:
            info.update(
                f"Last scan: {last['root']} at {last['finished_at']} "
                f"(+{last['new_files']} / ~{last['updated_files']} / -{last['removed_files']})"
            )
        else:
            info.update("No scans recorded yet. Choose 'Scan Library' first.")
