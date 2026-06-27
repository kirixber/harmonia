from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Input, Static, DataTable

from .base import BaseScreen
from ...utils.format import human_duration


class QualityScreen(BaseScreen):
    """Inspect and compare audio quality metrics for indexed tracks.

    Search tracks by title (or artist/album), click rows to select them,
    then analyze or compare the selection — no internal IDs required.
    Pure frontend: all analysis happens in ``QualityEngine`` via ``Library``.
    """

    TITLE = "Audio Quality"

    def __init__(self) -> None:
        super().__init__()
        # Maps a results-table row key -> track id, plus the current selection.
        self._row_to_id: dict = {}
        self._selected: list[int] = []
        self._names: dict[int, str] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="quality-area"):
            yield Static("Audio Quality", classes="screen-title")
            with Horizontal():
                yield Input(
                    placeholder="Search tracks by title, artist or album…",
                    id="quality-search",
                )
                yield Button("Search", id="quality-search-btn", variant="primary")
            yield Static(
                "Tip: click a row to add it to the selection.",
                id="quality-progress",
            )
            yield DataTable(id="quality-results")
            yield Static(id="quality-selection")
            with Horizontal():
                yield Button("Analyze Selected", id="quality-analyze", variant="primary")
                yield Button("Compare Selected", id="quality-compare")
                yield Button("Clear Selection", id="quality-clear")
            yield DataTable(id="quality-metrics")

    def on_mount(self) -> None:
        results = self.query_one("#quality-results", DataTable)
        results.add_columns("Title", "Artist", "Album", "Duration")
        results.cursor_type = "row"

        metrics = self.query_one("#quality-metrics", DataTable)
        metrics.add_columns(
            "Track", "Codec", "Bitrate", "Sample Rate", "Bit Depth",
            "Channels", "Duration",
        )

    # -- events ------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quality-search-btn":
            self._search()
        elif event.button.id == "quality-analyze":
            self._analyze()
        elif event.button.id == "quality-compare":
            self._compare()
        elif event.button.id == "quality-clear":
            self._clear_selection()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Pressing Enter in the search box runs the search."""
        if event.input.id == "quality-search":
            self._search()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "quality-results":
            return
        track_id = self._row_to_id.get(event.row_key)
        if track_id is None:
            return
        if track_id not in self._selected:
            self._selected.append(track_id)
        self._render_selection()

    # -- actions -----------------------------------------------------------

    def _search(self) -> None:
        query = self.query_one("#quality-search", Input).value.strip()
        progress = self.query_one("#quality-progress", Static)
        if not query:
            progress.update("[yellow]Type something to search for.[/yellow]")
            return

        rows = self.library.search_tracks(query, limit=50)
        dt = self.query_one("#quality-results", DataTable)
        dt.clear()
        self._row_to_id.clear()

        if not rows:
            progress.update(f"[yellow]No tracks match '{query}'.[/yellow]")
            return

        for row in rows:
            title = row["title"] or Path(row["path"]).name
            artist = row["artist_name"] or "—"
            album = row["album_name"] or "—"
            self._names[row["id"]] = title
            row_key = dt.add_row(
                title, artist, album, human_duration(row["duration"] or 0)
            )
            self._row_to_id[row_key] = row["id"]

        progress.update(
            f"Found {len(rows)} track(s). Click rows to select, then Analyze or Compare."
        )

    def _track_name(self, track_id: int) -> str:
        if track_id in self._names:
            return self._names[track_id]
        row = self.library.db.get_track(track_id)
        return Path(row["path"]).name if row else f"#{track_id}"

    def _render_selection(self) -> None:
        sel = self.query_one("#quality-selection", Static)
        if not self._selected:
            sel.update("")
            return
        names = ", ".join(self._track_name(t) for t in self._selected)
        sel.update(f"[bold]Selected ({len(self._selected)}):[/bold] {names}")

    def _clear_selection(self) -> None:
        self._selected.clear()
        self._render_selection()
        self.query_one("#quality-metrics", DataTable).clear()
        self.query_one("#quality-progress", Static).update("Selection cleared.")

    @staticmethod
    def _is_lossless(codec: str) -> bool:
        return codec.upper() in (
            "FLAC", "ALAC", "APE", "WAVPACK", "WAVE", "WAV", "AIFF"
        )

    def _add_metrics_row(self, dt: DataTable, track_id: int, m) -> None:
        # Bit depth is only meaningful for lossless formats; for lossy codecs
        # it is genuinely absent, so show "n/a" instead of a misleading "?".
        if m.bit_depth:
            bit_depth = f"{m.bit_depth}-bit"
        elif m.codec and not self._is_lossless(m.codec):
            bit_depth = "n/a"
        else:
            bit_depth = "?"

        dt.add_row(
            self._track_name(track_id),
            m.codec or "?",
            f"{m.bitrate // 1000} kbps" if m.bitrate else "?",
            f"{m.sample_rate:,} Hz" if m.sample_rate else "?",
            bit_depth,
            str(m.channels) if m.channels else "?",
            human_duration(m.duration),
        )

    def _analyze(self) -> None:
        progress = self.query_one("#quality-progress", Static)
        if not self._selected:
            progress.update("[red]Select at least one track first.[/red]")
            return

        dt = self.query_one("#quality-metrics", DataTable)
        dt.clear()
        for tid in self._selected:
            self._add_metrics_row(dt, tid, self.library.analyze_quality(tid))
        progress.update(f"Analyzed {len(self._selected)} track(s).")

    def _compare(self) -> None:
        progress = self.query_one("#quality-progress", Static)
        if len(self._selected) < 2:
            progress.update("[red]Select at least two tracks to compare.[/red]")
            return

        dt = self.query_one("#quality-metrics", DataTable)
        dt.clear()
        for metrics in self.library.compare_quality(self._selected):
            self._add_metrics_row(dt, metrics.track_id, metrics)

        best = self.library.best_quality(self._selected)
        if best is not None:
            progress.update(
                f"[green]Best quality:[/green] {self._track_name(best)}."
            )
        else:
            progress.update("[yellow]Could not determine best quality.[/yellow]")
