"""Interactive main menu — the numbered terminal menu from the mockup.

Loops until the user chooses Exit. Each entry delegates to :mod:`actions`,
which calls the core. Unbuilt entries show a 'coming soon' notice so the
menu shape matches the final product from day one.
"""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text

from .metadata_menu import run_metadata_menu

from .. import __version__
from ..core.library import Library
from . import actions

# (key, label, handler-name). Handlers resolved against this module's _on_*.
ENTRIES = [
    ("1", "Scan Library", "scan"),
    ("2", "Artwork", "artwork"),
    ("3", "Metadata", "metadata"),
    ("4", "Duplicates", "duplicates"),
    ("5", "Audio Quality", "audio_quality"),
    ("6", "Reports", "reports"),
    ("7", "Settings", "settings"),
    ("0", "Exit", "exit"),
]


def _render_menu() -> Panel:
    header = Group(
        Rule(style="grey50"),
        Align.center(Text(f"HARMONIA v{__version__}", style="bold")),
        Rule(style="grey50"),
    )
    lines = [header, Text()]
    for key, label, _ in ENTRIES:
        lines.append(Text(f"  {key}. {label}"))
    return Panel(Group(*lines), title="Main Menu", border_style="white", padding=(1, 2))


def run(console: Console | None = None, db_path=None) -> None:
    console = console or Console()
    choices = [e[0] for e in ENTRIES]
    with Library(db_path) as library:
        while True:
            console.print(_render_menu())
            choice = Prompt.ask("Select", choices=choices, default="0", show_choices=False)
            handler = _HANDLERS[choice]
            if handler(library, console) is False:
                break
            console.print()


def _on_scan(library: Library, console: Console) -> None:
    path = Prompt.ask("Path to scan", default=".")
    actions.run_scan(library, console, path)


def _on_reports(library: Library, console: Console) -> None:
    actions.show_reports(library, console)


def _on_settings(library: Library, console: Console) -> None:
    actions.show_settings(library, console)


def _on_artwork(library: Library, console: Console) -> None:
    actions.not_implemented(console, "Artwork")


def _on_metadata(library: Library, console: Console) -> None:
    run_metadata_menu(library, console)


def _on_duplicates(library: Library, console: Console) -> None:
    actions.not_implemented(console, "Duplicates")


def _on_audio_quality(library: Library, console: Console) -> None:
    actions.not_implemented(console, "Audio Quality")


def _on_exit(library: Library, console: Console) -> bool:
    console.print("[dim]Goodbye.[/dim]")
    return False


_HANDLERS = {
    "1": _on_scan,
    "2": _on_artwork,
    "3": _on_metadata,
    "4": _on_duplicates,
    "5": _on_audio_quality,
    "6": _on_reports,
    "7": _on_settings,
    "0": _on_exit,
}
