from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Input, Static, DataTable

from .base import BaseScreen
from ...utils.format import human_duration


class QualityScreen(BaseScreen):
    """Inspect and compare audio quality metrics for indexed tracks.

    Pure frontend: all analysis happens in ``QualityEngine`` via the
    ``Library`` facade.
    """

    TITLE = "Audio Quality"

    def compose(self) -> ComposeResult:
        with Vertical(id="quality-area"):
            yield Static("Audio Quality", classes="screen-title")
            with Horizontal():
                yield Input(
                    placeholder="Track ID(s), comma-separated", id="quality-ids"
                )
                yield Button("Analyze", id="quality-analyze", variant="primary")
                yield Button("Compare", id="quality-compare")
            yield Static(id="quality-progress")
            yield DataTable(id="quality-results")

    def on_mount(self) -> None:
        dt = self.query_one("#quality-results", DataTable)
        dt.add_columns(
            "Track", "Codec", "Bitrate", "Sample Rate", "Bit Depth",
            "Channels", "Duration",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quality-analyze":
            self._analyze()
        elif event.button.id == "quality-compare":
            self._compare()

    def _parse_ids(self) -> list[int]:
        raw = self.query_one("#quality-ids", Input).value.strip()
        ids: list[int] = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        return ids

    def _track_name(self, track_id: int) -> str:
        row = self.library.db.get_track(track_id)
        return Path(row["path"]).name if row else f"#{track_id}"

    def _add_metrics_row(self, dt: DataTable, track_id: int, m) -> None:
        dt.add_row(
            self._track_name(track_id),
            m.codec or "?",
            f"{m.bitrate // 1000} kbps" if m.bitrate else "?",
            f"{m.sample_rate:,} Hz" if m.sample_rate else "?",
            f"{m.bit_depth}-bit" if m.bit_depth else "?",
            str(m.channels) if m.channels else "?",
            human_duration(m.duration),
        )

    def _analyze(self) -> None:
        ids = self._parse_ids()
        progress = self.query_one("#quality-progress", Static)
        if not ids:
            progress.update("[red]Enter one or more numeric track IDs.[/red]")
            return

        dt = self.query_one("#quality-results", DataTable)
        dt.clear()
        for tid in ids:
            metrics = self.library.analyze_quality(tid)
            self._add_metrics_row(dt, tid, metrics)
        progress.update(f"Analyzed {len(ids)} track(s).")

    def _compare(self) -> None:
        ids = self._parse_ids()
        progress = self.query_one("#quality-progress", Static)
        if len(ids) < 2:
            progress.update("[red]Enter at least two track IDs to compare.[/red]")
            return

        dt = self.query_one("#quality-results", DataTable)
        dt.clear()
        for metrics in self.library.compare_quality(ids):
            self._add_metrics_row(dt, metrics.track_id, metrics)

        best = self.library.best_quality(ids)
        if best is not None:
            progress.update(
                f"[green]Best quality:[/green] {self._track_name(best)} (id {best})."
            )
        else:
            progress.update("[yellow]Could not determine best quality.[/yellow]")
