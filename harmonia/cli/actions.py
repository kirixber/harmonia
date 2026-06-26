"""Rendering for each core operation, reused by the menu and by subcommands.

These functions are the only place the CLI turns core results into terminal
output. They call the :class:`~harmonia.core.library.Library` and render with
Rich; they contain no library logic of their own.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress as RichProgress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from ..core.library import Library
from ..jobs.job import Progress
from ..utils.format import human_duration, human_size
from ..utils.paths import database_path, home_dir, logs_dir

PLANNED = {
    "Artwork": "v0.4",
    "Metadata editing": "v0.2",
    "Duplicates": "v0.3",
    "Audio Quality": "v0.5",
}


def run_scan(library: Library, console: Console, path: str | Path) -> None:
    target = Path(path).expanduser()
    if not target.exists():
        console.print(f"[red]Path not found:[/red] {target}")
        return

    console.print(f"Scanning [bold]{target}[/bold] …")
    with RichProgress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    ) as bar:
        task = bar.add_task("Indexing", total=None)

        def on_progress(p: Progress) -> None:
            bar.update(task, total=p.total, completed=p.done, description=p.message[:40])

        result = library.scan(target, progress=on_progress)

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_row("Scanned", str(result.scanned_files))
    table.add_row("[green]New[/green]", str(result.new_files))
    table.add_row("[yellow]Updated[/yellow]", str(result.updated_files))
    table.add_row("[red]Removed[/red]", str(result.removed_files))
    if result.errors:
        table.add_row("[red]Errors[/red]", str(result.errors))
    console.print(Panel(table, title="Scan complete", border_style="green"))


def show_reports(library: Library, console: Console) -> None:
    stats = library.stats()
    table = Table(title="Library", show_header=False, box=None)
    table.add_row("Tracks", f"{stats['tracks']:,}")
    table.add_row("Artists", f"{stats['artists']:,}")
    table.add_row("Albums", f"{stats['albums']:,}")
    table.add_row("Total time", human_duration(stats["total_duration"]))
    table.add_row("Total size", human_size(stats["total_size"]))
    console.print(Panel(table, border_style="cyan"))

    last = library.last_scan()
    if last:
        console.print(
            f"[dim]Last scan:[/dim] {last['root']}  "
            f"[dim]at[/dim] {last['finished_at']}  "
            f"([green]+{last['new_files']}[/green] / "
            f"[yellow]~{last['updated_files']}[/yellow] / "
            f"[red]-{last['removed_files']}[/red])"
        )
    else:
        console.print("[dim]No scans recorded yet. Choose 'Scan Library' first.[/dim]")


def show_settings(library: Library, console: Console) -> None:
    table = Table(show_header=False, box=None)
    table.add_row("Home", str(home_dir()))
    table.add_row("Database", str(database_path()))
    table.add_row("Logs", str(logs_dir()))
    console.print(Panel(table, title="Settings", border_style="magenta"))
    console.print("[dim]Editable settings arrive with provider config in v0.4.[/dim]")


def not_implemented(console: Console, feature: str) -> None:
    version = PLANNED.get(feature, "a later release")
    console.print(
        Panel(
            f"[bold]{feature}[/bold] is planned for [cyan]{version}[/cyan].\n"
            f"The scaffolding is in place; this action is not wired up yet.",
            title="Coming soon",
            border_style="yellow",
        )
    )
