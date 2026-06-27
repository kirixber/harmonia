from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Input, Static, DataTable

from .base import BaseScreen


class DuplicatesScreen(BaseScreen):
    TITLE = "Duplicates"

    def compose(self) -> ComposeResult:
        with Vertical(id="duplicates-area"):
            yield Static("Duplicate Detection", classes="screen-title")
            with Horizontal():
                yield Input(placeholder="Review threshold (default 75)", id="dup-threshold")
                yield Button("Scan", id="dup-btn", variant="primary")
            yield Static(id="dup-progress")
            yield DataTable(id="dup-results")

    def on_mount(self) -> None:
        dt = self.query_one("#dup-results", DataTable)
        dt.add_columns("Confidence", "Track A", "Track B", "Score")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dup-btn":
            self._scan()

    def _scan(self) -> None:
        threshold_str = self.query_one("#dup-threshold", Input).value.strip()
        threshold = int(threshold_str) if threshold_str.isdigit() else 75

        progress = self.query_one("#dup-progress", Static)
        progress.update("Scanning for duplicates …")

        try:
            report = self.library.duplicate_report(review_threshold=threshold)
        except Exception as exc:
            progress.update(f"[red]Error:[/red] {exc}")
            return

        dt = self.query_one("#dup-results", DataTable)
        dt.clear()

        if not report.clusters:
            progress.update("[green]No duplicates found.[/green]")
            return

        for cluster in report.clusters:
            for match in cluster.matches:
                a = cluster.tracks[0]
                b = cluster.tracks[1] if len(cluster.tracks) > 1 else a
                dt.add_row(
                    match.confidence.value,
                    Path(a.path).name,
                    Path(b.path).name,
                    str(match.score),
                )

        progress.update(
            f"Summary: {report.definite} definite, {report.high} high, {report.review} needs review."
        )
