"""Metadata submenu: validation report, normalize, rename, edit a track.

Like the main menu, this only collects input and renders; every operation
goes through the Library facade via :mod:`actions`.
"""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.text import Text

from ..core.library import Library
from ..core.metadata.rename import NAMED_TEMPLATES
from . import actions

_ENTRIES = [
    ("1", "Validation report"),
    ("2", "Normalize tags"),
    ("3", "Rename files"),
    ("4", "Edit a track"),
    ("0", "Back"),
]


def _render() -> Panel:
    header = Group(Rule(style="grey50"),
                   Align.center(Text("Metadata", style="bold")),
                   Rule(style="grey50"))
    lines = [header, Text()]
    for key, label in _ENTRIES:
        lines.append(Text(f"  {key}. {label}"))
    return Panel(Group(*lines), title="Metadata", border_style="white", padding=(1, 2))


def run_metadata_menu(library: Library, console: Console) -> None:
    choices = [e[0] for e in _ENTRIES]
    while True:
        console.print(_render())
        choice = Prompt.ask("Select", choices=choices, default="0", show_choices=False)
        if choice == "0":
            return
        if choice == "1":
            actions.show_metadata_report(library, console)
        elif choice == "2":
            apply = Confirm.ask("Apply changes? (No = preview)", default=False)
            actions.run_normalize(library, console, apply=apply)
        elif choice == "3":
            _rename_flow(library, console)
        elif choice == "4":
            _edit_flow(library, console)
        console.print()


def _rename_flow(library: Library, console: Console) -> None:
    console.print("Presets: " + ", ".join(NAMED_TEMPLATES))
    template = Prompt.ask("Template (preset name or custom pattern)",
                          default="artist-album-track-title")
    base = Prompt.ask("Base directory (blank = keep each file in place)", default="")
    apply = Confirm.ask("Apply moves? (No = preview)", default=False)
    actions.run_rename(library, console, template, base_dir=base or None, apply=apply)


def _edit_flow(library: Library, console: Console) -> None:
    track_id = Prompt.ask("Track id")
    if not track_id.isdigit():
        console.print("[red]Track id must be a number.[/red]")
        return
    field = Prompt.ask("Field (e.g. title, artist, album, genre, year)")
    value = Prompt.ask("New value")
    apply = Confirm.ask("Apply? (No = preview)", default=True)
    try:
        actions.run_edit(library, console, int(track_id), {field: value}, apply=apply)
    except (KeyError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
