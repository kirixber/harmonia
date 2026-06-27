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


def show_duplicates(
    library: Library, console: Console, threshold: int = 75, json_path=None
) -> None:
    console.print("Scanning for duplicates …")
    report = library.duplicate_report(review_threshold=threshold)

    if not report.clusters:
        console.print("[green]No duplicates found.[/green]")
        return

    table = Table(title=f"Duplicates (threshold={threshold})", show_header=True, header_style="bold")
    table.add_column("Confidence")
    table.add_column("Track A")
    table.add_column("Track B")
    table.add_column("Score", justify="right")

    for cluster in report.clusters:
        for match in cluster.matches:
            a = cluster.tracks[0]  # simplified - just show first track as reference
            b = cluster.tracks[1] if len(cluster.tracks) > 1 else a
            conf_style = {
                "definite": "red",
                "high": "orange3",
                "review": "yellow",
            }.get(match.confidence.value, "white")
            table.add_row(
                f"[{conf_style}]{match.confidence.value}[/{conf_style}]",
                Path(a.path).name,
                Path(b.path).name,
                str(match.score),
            )

    console.print(Panel(table, border_style="yellow"))
    console.print(
        f"[dim]Summary: {report.definite} definite, {report.high} high, {report.review} needs review.[/dim]"
    )

    if json_path:
        import json
        data = {
            "summary": report.summary(),
            "clusters": [
                {
                    "confidence": c.confidence.value,
                    "tracks": [{"id": t.id, "path": t.path} for t in c.tracks],
                    "matches": [
                        {"a": m.a, "b": m.b, "score": m.score, "signals": m.signals}
                        for m in c.matches
                    ],
                }
                for c in report.clusters
            ],
        }
        Path(json_path).write_text(json.dumps(data, indent=2))
        console.print(f"Wrote JSON → [bold]{json_path}[/bold]")


async def artwork_search(
    library: Library, console: Console, artist: str, album: str, limit: int = 10
) -> None:
    console.print(f"Searching artwork for [bold]{artist}[/bold] — [bold]{album}[/bold] …")
    await library.initialize_providers()
    try:
        candidates = await library.search_artwork(artist, album, limit=limit)
    finally:
        await library.shutdown_providers()

    if not candidates:
        console.print("[yellow]No artwork found.[/yellow]")
        return

    table = Table(title="Artwork candidates", show_header=True, header_style="bold")
    table.add_column("Provider")
    table.add_column("URL")
    table.add_column("Size")
    table.add_column("Format")
    table.add_column("Confidence", justify="right")

    for c in candidates:
        table.add_row(
            c.provider,
            c.url[:60] + ("…" if len(c.url) > 60 else ""),
            f"{c.width}x{c.height}" if c.width and c.height else "?",
            c.format or "?",
            f"{c.confidence:.0%}",
        )

    console.print(Panel(table, border_style="cyan"))


def quality_analyze(library: Library, console: Console, track_id: int) -> None:
    metrics = library.analyze_quality(track_id)
    table = Table(title=f"Quality Analysis (Track {track_id})", show_header=False, box=None)
    table.add_row("Codec", metrics.codec or "?")
    table.add_row("Bitrate", f"{metrics.bitrate} kbps" if metrics.bitrate else "?")
    table.add_row("Sample Rate", f"{metrics.sample_rate} Hz" if metrics.sample_rate else "?")
    table.add_row("Bit Depth", f"{metrics.bit_depth}-bit" if metrics.bit_depth else "?")
    table.add_row("Channels", str(metrics.channels) if metrics.channels else "?")
    table.add_row("Duration", f"{metrics.duration:.1f}s" if metrics.duration else "?")
    if metrics.dynamic_range is not None:
        table.add_row("Dynamic Range", f"{metrics.dynamic_range:.1f} dB")
    if metrics.clipping is not None:
        table.add_row("Clipping", f"{metrics.clipping:.1f}%")
    if metrics.true_peak is not None:
        table.add_row("True Peak", f"{metrics.true_peak:.2f} dBTP")
    console.print(Panel(table, border_style="cyan"))


def quality_compare(library: Library, console: Console, track_ids: list[int]) -> None:
    metrics_list = library.compare_quality(track_ids)
    table = Table(title="Quality Comparison", show_header=True, header_style="bold")
    table.add_column("Track ID")
    table.add_column("Codec")
    table.add_column("Bitrate")
    table.add_column("Sample Rate")
    table.add_column("Bit Depth")
    table.add_column("Channels")
    table.add_column("Duration")
    for m in metrics_list:
        table.add_row(
            str(m.track_id),
            m.codec or "?",
            f"{m.bitrate} kbps" if m.bitrate else "?",
            f"{m.sample_rate} Hz" if m.sample_rate else "?",
            f"{m.bit_depth}-bit" if m.bit_depth else "?",
            str(m.channels) if m.channels else "?",
            f"{m.duration:.1f}s" if m.duration else "?",
        )
    console.print(Panel(table, border_style="cyan"))


def quality_best(library: Library, console: Console, track_ids: list[int]) -> None:
    best = library.best_quality(track_ids)
    if best is None:
        console.print("[yellow]No valid tracks to compare.[/yellow]")
        return
    console.print(f"[green]Best quality:[/green] Track {best}")


def quality_fingerprint(library: Library, console: Console, track_id: int) -> None:
    fp = library.compute_fingerprint(track_id)
    table = Table(title=f"Fingerprint (Track {track_id})", show_header=False, box=None)
    table.add_row("AcoustID", fp.acoustid or "Not found")
    table.add_row("Chromaprint", fp.chromaprint[:80] + "…" if fp.chromaprint and len(fp.chromaprint) > 80 else (fp.chromaprint or "Not computed"))
    table.add_row("Confidence", f"{fp.confidence:.2f}" if fp.confidence else "N/A")
    console.print(Panel(table, border_style="cyan"))


def quality_replaygain(library: Library, console: Console, track_id: int) -> None:
    rg = library.compute_replaygain(track_id)
    table = Table(title=f"ReplayGain (Track {track_id})", show_header=False, box=None)
    table.add_row("Track Gain", f"{rg.track_gain:.2f} dB" if rg.track_gain else "Not computed")
    table.add_row("Track Peak", f"{rg.track_peak:.4f}" if rg.track_peak else "Not computed")
    table.add_row("Album Gain", f"{rg.album_gain:.2f} dB" if rg.album_gain else "Not computed")
    table.add_row("Album Peak", f"{rg.album_peak:.4f}" if rg.album_peak else "Not computed")
    console.print(Panel(table, border_style="cyan"))


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
