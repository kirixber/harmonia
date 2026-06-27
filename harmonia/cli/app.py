"""CLI entry point.

With no arguments it launches the interactive main menu. Subcommands expose
the same actions for scripting: ``scan``, ``stats``, ``menu``, ``version``.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from .. import __version__
from ..core.library import Library
from ..utils.logging import setup_logging
from . import actions, menu


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harmonia", description="Harmonia — music library manager."
    )
    parser.add_argument(
        "--db", help="Path to the Harmonia database (defaults to the user data dir)."
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"Harmonia {__version__}"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("menu", help="Launch the interactive main menu (default).")

    scan = sub.add_parser("scan", help="Scan a directory into the library index.")
    scan.add_argument("path", help="Directory to scan recursively.")

    sub.add_parser("stats", help="Show library statistics.")

    report = sub.add_parser("report", help="Library metadata health report.")
    report.add_argument("--json", dest="json_path", help="Write report as JSON.")
    report.add_argument("--csv", dest="csv_path", help="Write report as CSV.")

    norm = sub.add_parser("normalize", help="Normalize tags across the library.")
    norm.add_argument("--apply", action="store_true",
                      help="Write changes (default previews only).")

    rename = sub.add_parser("rename", help="Rename files from a metadata template.")
    rename.add_argument("template", help="Preset name or custom pattern.")
    rename.add_argument("--base", dest="base_dir", help="Base directory for output.")
    rename.add_argument("--apply", action="store_true",
                        help="Move files (default previews only).")

    edit = sub.add_parser("edit", help="Edit one track's tags.")
    edit.add_argument("track_id", type=int)
    edit.add_argument("--set", dest="sets", action="append", metavar="FIELD=VALUE",
                      default=[], help="Field assignment (repeatable).")
    edit.add_argument("--dry-run", action="store_true", help="Preview without writing.")

    dup = sub.add_parser("duplicates", help="Find duplicate tracks.")
    dup.add_argument("--threshold", type=int, default=75,
                     help="Review threshold (default 75).")
    dup.add_argument("--json", dest="json_path", help="Write report as JSON.")

    artwork = sub.add_parser("artwork", help="Artwork operations.")
    artwork_sub = artwork.add_subparsers(dest="artwork_cmd")
    art_search = artwork_sub.add_parser("search", help="Search artwork for album.")
    art_search.add_argument("artist")
    art_search.add_argument("album")
    art_search.add_argument("--limit", type=int, default=10)

    quality = sub.add_parser("quality", help="Audio quality analysis.")
    quality_sub = quality.add_subparsers(dest="quality_cmd")
    qual_analyze = quality_sub.add_parser("analyze", help="Analyze track quality.")
    qual_analyze.add_argument("track_id", type=int)
    qual_compare = quality_sub.add_parser("compare", help="Compare quality of tracks.")
    qual_compare.add_argument("track_ids", nargs="+", type=int)
    qual_best = quality_sub.add_parser("best", help="Find best quality track.")
    qual_best.add_argument("track_ids", nargs="+", type=int)
    qual_fp = quality_sub.add_parser("fingerprint", help="Compute fingerprint.")
    qual_fp.add_argument("track_id", type=int)
    qual_rg = quality_sub.add_parser("replaygain", help="Compute ReplayGain.")
    qual_rg.add_argument("track_id", type=int)
    return parser


def _parse_sets(sets: list[str]) -> dict:
    changes: dict[str, str] = {}
    for item in sets:
        if "=" not in item:
            raise SystemExit(f"--set expects FIELD=VALUE, got: {item!r}")
        field, value = item.split("=", 1)
        changes[field.strip()] = value
    return changes


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)
    console = Console()

    if args.command in (None, "menu"):
        menu.run(console=console, db_path=args.db)
        return 0

    with Library(args.db) as library:
        if args.command == "scan":
            actions.run_scan(library, console, args.path)
        elif args.command == "stats":
            actions.show_reports(library, console)
        elif args.command == "report":
            actions.show_metadata_report(library, console, args.json_path, args.csv_path)
        elif args.command == "normalize":
            actions.run_normalize(library, console, apply=args.apply)
        elif args.command == "rename":
            actions.run_rename(library, console, args.template,
                               base_dir=args.base_dir, apply=args.apply)
        elif args.command == "edit":
            try:
                actions.run_edit(library, console, args.track_id,
                                 _parse_sets(args.sets), apply=not args.dry_run)
            except (KeyError, ValueError) as exc:
                console.print(f"[red]{exc}[/red]")
                return 1
        elif args.command == "duplicates":
            actions.show_duplicates(library, console, args.threshold, args.json_path)
        elif args.command == "artwork":
            if args.artwork_cmd == "search":
                import asyncio
                asyncio.run(actions.artwork_search(library, console, args.artist, args.album, args.limit))
        elif args.command == "quality":
            if args.quality_cmd == "analyze":
                actions.quality_analyze(library, console, args.track_id)
            elif args.quality_cmd == "compare":
                actions.quality_compare(library, console, args.track_ids)
            elif args.quality_cmd == "best":
                actions.quality_best(library, console, args.track_ids)
            elif args.quality_cmd == "fingerprint":
                actions.quality_fingerprint(library, console, args.track_id)
            elif args.quality_cmd == "replaygain":
                actions.quality_replaygain(library, console, args.track_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
