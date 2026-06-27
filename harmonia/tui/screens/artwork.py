from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Input, Static, DataTable

from .base import BaseScreen


class ArtworkScreen(BaseScreen):
    TITLE = "Artwork"

    def compose(self) -> ComposeResult:
        with Vertical(id="artwork-area"):
            yield Static("Artwork Search", classes="screen-title")
            with Horizontal():
                yield Input(placeholder="Artist", id="artwork-artist")
                yield Input(placeholder="Album", id="artwork-album")
            yield Button("Search", id="artwork-btn", variant="primary")
            yield Static(id="artwork-progress")
            yield DataTable(id="artwork-results")
            yield Static(id="artwork-selected")
            with Horizontal():
                yield Button("Download Selected", id="artwork-download", variant="primary")
                yield Button("Save As...", id="artwork-save")
                yield Button("Embed in Track", id="artwork-embed")

    def on_mount(self) -> None:
        dt = self.query_one("#artwork-results", DataTable)
        dt.add_columns("Provider", "URL", "Size", "Format", "Confidence")
        dt.cursor_type = "row"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "artwork-btn":
            asyncio.run(self._search())
        elif event.button.id == "artwork-download":
            asyncio.run(self._download_selected())
        elif event.button.id == "artwork-save":
            asyncio.run(self._save_selected())
        elif event.button.id == "artwork-embed":
            asyncio.run(self._embed_selected())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        dt = self.query_one("#artwork-results", DataTable)
        row = dt.get_row(event.row_key)
        self._selected_candidate = row
        self.query_one("#artwork-selected", Static).update(
            f"Selected: {row[0]} — {row[1]} ({row[2]}, {row[3]}, {row[4]})"
        )

    async def _search(self) -> None:
        artist = self.query_one("#artwork-artist", Input).value.strip()
        album = self.query_one("#artwork-album", Input).value.strip()
        if not artist and not album:
            self.query_one("#artwork-progress", Static).update(
                "[yellow]Enter artist or album to search.[/yellow]"
            )
            return

        progress = self.query_one("#artwork-progress", Static)
        progress.update(f"Searching artwork for [bold]{artist}[/bold] — [bold]{album}[/bold] …")

        try:
            await self.library.initialize_providers()
            self._candidates = await self.library.search_artwork(artist, album, limit=10)
        except Exception as exc:
            progress.update(f"[red]Error:[/red] {exc}")
            return
        finally:
            await self.library.shutdown_providers()

        dt = self.query_one("#artwork-results", DataTable)
        dt.clear()

        if not self._candidates:
            progress.update("[yellow]No artwork found.[/yellow]")
            return

        progress.update("")
        for c in self._candidates:
            dt.add_row(
                c.provider,
                c.url[:60] + ("…" if len(c.url) > 60 else ""),
                f"{c.width}x{c.height}" if c.width and c.height else "?",
                c.format or "?",
                f"{c.confidence:.0%}",
            )

    async def _get_selected_candidate(self):
        dt = self.query_one("#artwork-results", DataTable)
        if dt.cursor_row is None or dt.cursor_row >= len(self._candidates):
            self.query_one("#artwork-progress", Static).update("[red]No artwork selected.[/red]")
            return None
        return self._candidates[dt.cursor_row]

    async def _download_selected(self) -> None:
        candidate = await self._get_selected_candidate()
        if not candidate:
            return

        progress = self.query_one("#artwork-progress", Static)
        progress.update(f"Downloading from {candidate.provider}…")

        try:
            await self.library.initialize_providers()
            data = await self.library.download_artwork(candidate)
        except Exception as exc:
            progress.update(f"[red]Download failed:[/red] {exc}")
            return
        finally:
            await self.library.shutdown_providers()

        if not data:
            progress.update("[red]No data downloaded.[/red]")
            return

        self._downloaded_data = data
        progress.update(f"[green]Downloaded {len(data)} bytes.[/green]")

    async def _save_selected(self) -> None:
        if not hasattr(self, '_downloaded_data') or not self._downloaded_data:
            self.query_one("#artwork-progress", Static).update("[red]Nothing to save — download first.[/red]")
            return

        save_path = Path.home() / "artwork.jpg"
        save_path.write_bytes(self._downloaded_data)
        self.query_one("#artwork-progress", Static).update(f"[green]Saved to {save_path}[/green]")

    async def _embed_selected(self) -> None:
        self.query_one("#artwork-progress", Static).update("[yellow]Embed in track — not yet implemented.[/yellow]")
