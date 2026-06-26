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


def show_metadata_report(
    library: Library, console: Console, json_path=None, csv_path=None
) -> None:
    report = library.metadata_report()
    table = Table(title="Metadata report", show_header=True, header_style="bold")
    table.add_column("Category")
    table.add_column("Count", justify="right")
    for category, count in report.summary.items():
        style = "red" if count else "dim"
        table.add_row(category.replace("_", " "), f"[{style}]{count}[/{style}]")
    console.print(Panel(table, border_style="cyan"))
    console.print(f"[dim]{report.total} issue(s) across the library.[/dim]")

    if json_path:
        report.to_json(json_path)
        console.print(f"Wrote JSON → [bold]{json_path}[/bold]")
    if csv_path:
        report.to_csv(csv_path)
        console.print(f"Wrote CSV → [bold]{csv_path}[/bold]")


def _changes_table(title: str, rows: list[tuple[str, str]]) -> Table:
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Track")
    table.add_column("Change")
    for name, change in rows:
        table.add_row(name, change)
    return table


def run_normalize(library: Library, console: Console, apply: bool = False) -> None:
    outcomes = library.normalize_all(dry_run=not apply)
    if not outcomes:
        console.print("[green]Nothing to normalize — tags already clean.[/green]")
        return
    rows = []
    for tid, outcome in outcomes:
        name = Path(library.db.get_track(tid)["path"]).name
        for change in outcome.write.changes:
            rows.append((name, str(change)))
    verb = "Applied" if apply else "Would change (preview)"
    console.print(Panel(_changes_table(verb, rows), border_style="yellow"))
    if not apply:
        console.print("[dim]Re-run with --apply to write these changes.[/dim]")


def run_rename(
    library: Library, console: Console, template: str, base_dir=None, apply: bool = False
) -> None:
    plans = library.rename_all(template, base_dir=base_dir, dry_run=not apply)
    table = Table(title="Rename plan", show_header=True, header_style="bold")
    table.add_column("Status")
    table.add_column("From → To")
    shown = 0
    for plan in plans:
        if plan.status.value in ("unchanged",):
            continue
        color = {"rename": "green", "conflict": "red", "missing": "yellow"}.get(
            plan.status.value, "white"
        )
        dest = Path(plan.new_path).name if plan.new_path else "—"
        table.add_row(f"[{color}]{plan.status.value}[/{color}]",
                      f"{Path(plan.old_path).name} → {dest}")
        shown += 1
    if shown == 0:
        console.print("[green]All files already match the template.[/green]")
        return
    console.print(Panel(table, border_style="cyan"))
    if not apply:
        console.print("[dim]Preview only. Re-run with --apply to move files.[/dim]")


def run_edit(
    library: Library, console: Console, track_id: int, changes: dict, apply: bool = True
) -> None:
    outcome = library.edit_track(track_id, changes, dry_run=not apply)
    if outcome.blocked:
        console.print("[red]Edit blocked by validation errors:[/red]")
        for issue in outcome.issues:
            if issue.severity.value == "error":
                console.print(f"  • {issue.field}: {issue.message} — {issue.suggestion}")
        return
    if outcome.write is None or not outcome.write.changes:
        console.print("[dim]No changes — values already match.[/dim]")
        return
    rows = [(str(track_id), str(c)) for c in outcome.write.changes]
    verb = "Applied" if apply else "Would change (preview)"
    console.print(Panel(_changes_table(verb, rows), border_style="green"))
    if outcome.write.errors:
        console.print(f"[red]Errors:[/red] {', '.join(outcome.write.errors)}")


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
