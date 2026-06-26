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
    return parser


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
