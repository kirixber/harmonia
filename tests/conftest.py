"""Shared fixtures. Generates real audio files with ffmpeg when available;
tests that need them skip cleanly if ffmpeg is missing.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mutagen.flac import FLAC

HAVE_FFMPEG = shutil.which("ffmpeg") is not None


def _make_flac(path: Path, seconds: float = 1.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-c:a", "flac", str(path),
        ],
        check=True,
    )


@pytest.fixture
def music_root(tmp_path: Path) -> Path:
    """A small on-disk library: 2 albums, tagged FLAC files."""
    if not HAVE_FFMPEG:
        pytest.skip("ffmpeg not available to synthesize audio fixtures")

    root = tmp_path / "music"
    specs = [
        ("Artist A/Album One", "01 - First.flac",
         dict(title="First", artist="Artist A", album="Album One",
              tracknumber="1/2", date="2020", genre="Rock")),
        ("Artist A/Album One", "02 - Second.flac",
         dict(title="Second", artist="Artist A", album="Album One",
              tracknumber="2/2", date="2020")),
        ("Artist B/Album Two", "01 - Solo.flac",
         dict(title="Solo", artist="Artist B", album="Album Two",
              tracknumber="1", date="2019")),
    ]
    for rel_dir, name, tags in specs:
        d = root / rel_dir
        d.mkdir(parents=True, exist_ok=True)
        fpath = d / name
        _make_flac(fpath)
        audio = FLAC(fpath)
        for k, v in tags.items():
            audio[k] = v
        audio.save()
    return root
