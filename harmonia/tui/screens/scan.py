from __future__ import annotations

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Input, Static, DataTable

from .base import BaseScreen
from ...core.library import Library
from ...jobs.job import Progress


class ScanScreen(BaseScreen):
    TITLE = "Scan Library"

    def compose(self) -> ComposeResult:
        with Vertical(id="scan-area"):
            yield Static("Scan Library", classes="screen-title")
            yield Static("Enter a directory path to scan:")
            yield Input(placeholder="/path/to/music", id="scan-path")
            yield Button("Scan", id="scan-btn", variant="primary")
            yield Static(id="scan-progress")
            yield DataTable(id="scan-results")

    def on_mount(self) -> None:
        dt = self.query_one("#scan-results", DataTable)
        dt.add_columns("Metric", "Value")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "scan-btn":
            self._run_scan()

    def _run_scan(self) -> None:
        path_input = self.query_one("#scan-path", Input)
        target = Path(path_input.value).expanduser()
        if not target.exists():
            self.query_one("#scan-progress", Static).update(
                f"[red]Path not found:[/red] {target}"
            )
            return

        progress_label = self.query_one("#scan-progress", Static)
        progress_label.update("Scanning…")

        def on_progress(p: Progress) -> None:
            self.call_from_thread(
                progress_label.update, f"Indexing: {p.done}/{p.total} — {p.message[:40]}"
            )

        try:
            result = self.library.scan(target, progress=on_progress)
        except Exception as exc:
            progress_label.update(f"[red]Error:[/red] {exc}")
            return

        progress_label.update("")

        dt = self.query_one("#scan-results", DataTable)
        dt.clear()
        dt.add_row("Scanned", str(result.scanned_files))
        dt.add_row("[green]New[/green]", str(result.new_files))
        dt.add_row("[yellow]Updated[/yellow]", str(result.updated_files))
        dt.add_row("[red]Removed[/red]", str(result.removed_files))
        if result.errors:
            dt.add_row("[red]Errors[/red]", str(result.errors))
