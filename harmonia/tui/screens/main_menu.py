from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Static

from ..constants import MENU_ENTRIES


class MainMenuScreen(Screen[None]):
    def compose(self) -> ComposeResult:
        yield Static(f"HARMONIA", id="menu-title")
        for key, label, _ in MENU_ENTRIES:
            btn = Button(f"{key}. {label}", id=f"menu-{key}", classes="menu-item")
            yield btn

    def on_button_pressed(self, event: Button.Pressed) -> None:
        for key, label, screen_name in MENU_ENTRIES:
            if event.button.id == f"menu-{key}":
                if screen_name is None:
                    self.app.notify(f"{label} — coming soon", severity="warning")
                    return
                self.app.open_screen(screen_name)
                return
