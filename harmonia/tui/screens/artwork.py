from __future__ import annotations

import asyncio

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

    def on_mount(self) -> None:
        dt = self.query_one("#artwork-results", DataTable)
        dt.add_columns("Provider", "URL", "Size", "Format", "Confidence")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "artwork-btn":
            asyncio.run(self._search())

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
            candidates = await self.library.search_artwork(artist, album, limit=10)
        except Exception as exc:
            progress.update(f"[red]Error:[/red] {exc}")
            return
        finally:
            await self.library.shutdown_providers()

        dt = self.query_one("#artwork-results", DataTable)
        dt.clear()

        if not candidates:
            progress.update("[yellow]No artwork found.[/yellow]")
            return

        progress.update("")
        for c in candidates:
            dt.add_row(
                c.provider,
                c.url[:60] + ("…" if len(c.url) > 60 else ""),
                f"{c.width}x{c.height}" if c.width and c.height else "?",
                c.format or "?",
                f"{c.confidence:.0%}",
            )
