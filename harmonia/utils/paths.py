"""Resolve where Harmonia keeps its database, cache and logs.

Honors ``HARMONIA_HOME`` for a single self-contained location (useful for
tests and portable installs); otherwise follows XDG-style defaults on
Linux/macOS and ``%LOCALAPPDATA%`` on Windows.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIRNAME = "harmonia"


def home_dir() -> Path:
    """Base directory holding all Harmonia runtime data."""
    override = os.environ.get("HARMONIA_HOME")
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / APP_DIRNAME

    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / APP_DIRNAME


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return home_dir() / "harmonia.db"


def cache_dir() -> Path:
    return home_dir() / "cache"


def artwork_cache_dir() -> Path:
    return cache_dir() / "artwork"


def logs_dir() -> Path:
    return home_dir() / "logs"
