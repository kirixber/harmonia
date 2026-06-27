from __future__ import annotations

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Input, Static, DataTable

from textual import work

from .base import BaseScreen
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
            self._start_scan()

    def _start_scan(self) -> None:
        path_input = self.query_one("#scan-path", Input)
        target = Path(path_input.value).expanduser()
        if not target.exists():
            self.query_one("#scan-progress", Static).update(
                f"[red]Path not found:[/red] {target}"
            )
            return

        # Touch the Library now so its SQLite connection is created on the UI
        # thread (the worker below runs on a separate thread).
        _ = self.library
        self.query_one("#scan-btn", Button).disabled = True
        self.query_one("#scan-progress", Static).update("Scanning…")
        self._scan_worker(target)

    @work(thread=True, exclusive=True)
    def _scan_worker(self, target: Path) -> None:
        """Run the blocking scan off the UI thread.

        Textual widgets are only safe to touch from the UI thread, so every
        update is marshalled back via ``self.app.call_from_thread``.
        """
        progress_label = self.query_one("#scan-progress", Static)

        def on_progress(p: Progress) -> None:
            self.app.call_from_thread(
                progress_label.update,
                f"Indexing: {p.done}/{p.total} — {p.message[:40]}",
            )

        try:
            result = self.library.scan(target, progress=on_progress)
        except Exception as exc:
            self.app.call_from_thread(
                progress_label.update, f"[red]Error:[/red] {exc}"
            )
            self.app.call_from_thread(self._enable_button)
            return

        self.app.call_from_thread(self._show_result, result)
        self.app.call_from_thread(self._enable_button)

    def _enable_button(self) -> None:
        self.query_one("#scan-btn", Button).disabled = False

    def _show_result(self, result) -> None:
        self.query_one("#scan-progress", Static).update(
            f"[green]Done.[/green] Scanned {result.scanned_files} file(s)."
        )
        dt = self.query_one("#scan-results", DataTable)
        dt.clear()
        dt.add_row("Scanned", str(result.scanned_files))
        dt.add_row("[green]Valid[/green]", str(result.valid_files))
        dt.add_row("[red]Corrupted[/red]", str(result.corrupted_files))
        dt.add_row("[green]New[/green]", str(result.new_files))
        dt.add_row("[yellow]Updated[/yellow]", str(result.updated_files))
        dt.add_row("[red]Removed[/red]", str(result.removed_files))
        if result.warnings:
            dt.add_row("[yellow]Warnings[/yellow]", str(result.warnings))
        if result.errors:
            dt.add_row("[red]Errors[/red]", str(result.errors))
