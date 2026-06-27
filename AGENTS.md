# AGENTS.md — Harmonia Development Guide

## Project Overview
**Harmonia** — open-source music library manager for collectors. One backend, many frontends (CLI, Textual TUI, PySide6 GUI). Current: v0.2 (scanner, SQLite, metadata editing, renaming). Python 3.13+, SQLite (stdlib), Mutagen, Rich.

## Key Commands
```bash
pip install -e ".[dev]"           # install with dev deps (pytest)
harmonia                          # interactive main menu (default)
harmonia scan <path>              # index a directory recursively
harmonia stats                    # library statistics
harmonia report [--json F] [--csv F]  # metadata health report
harmonia normalize [--apply]      # normalize tags (preview unless --apply)
harmonia rename <template> [--base D] [--apply]  # rename from template
harmonia edit <id> --set FIELD=VALUE [--dry-run]  # edit one track's tags
python -m harmonia ...            # same entry point without console script
pytest                            # run test suite
pytest tests/test_scanner.py::test_incremental_skip_unchanged  # single test
HARMONIA_HOME=/tmp/h harmonia stats  # override data/db/log location (tests)
```

## Architecture — The One Rule
**Frontends contain no business logic.** They only collect input, render, show progress, and call the core API. Any logic in a frontend is a bug.

- Only `harmonia/database/` touches SQLite — no frontend or other core module queries directly.
- Core never contains provider-specific logic; it requests capabilities, Provider Manager decides which provider fulfills.
- Core never depends on optional features — providers/analyzers are plugins behind interfaces; missing/failing plugin is logged and disabled, never fatal.

## Layout
```
harmonia/
  core/{scanner,metadata,artwork,duplicates,quality,reports}
  database/
  providers/
  cli/
  tui/      (future)
  gui/      (future)
  utils/
  jobs/
```

## Cross-Cutting Subsystems
- **Jobs** (`jobs/`): all long-running work (scan, artwork download, duplicate compare, fingerprint) runs as a job with progress/elapsed/ETA/warnings/errors, states: queued→running→completed/failed/cancelled.
- **Providers / Provider Manager**: providers run concurrently, results merged (not serial). Manager owns discovery, ordering, retries, rate limiting, health checks, caching. Requests hashed (SHA256 of artist/album/track) → cached in SQLite.
- **Caching**: never call online provider when valid cached response exists. Metadata responses cache in SQLite (~90d); artwork binaries on disk at `cache/artwork/<sha256>.jpg` (~30d); image bytes never in SQLite.
- **Database migrations**: schema versions have integer migration IDs, reversible when practical. UI never bypasses database module.

## Safety Invariants (Do Not Weaken)
- Deleting music and writing tags are irreversible — favor correctness over aggressiveness. Duplicate detection and artwork/metadata writes default to dry-run/preview/backup; nothing overwritten/deleted without explicit confirmation.
- Metadata writes are transaction-like: validate → back up original values → apply → verify → update DB. Partial failure must never corrupt a file. Every automatic change is reversible and explainable.
- Duplicate confidence is weighted score with low false-positive bias. Candidates grouped first (MusicBrainz Track ID, ISRC, normalized title+artist, ±1s duration bucket) to avoid O(n²). Thresholds: 99–100 definite, 90–98 high, 75–89 needs review, <75 not a duplicate.
- Conflict resolution priority: user edits > verified IDs (MusicBrainz/ISRC) > trusted providers > existing tags > filename inference. Merge provider results; never blindly replace.
- Artwork favors correctness over resolution: verified 1500×1500 beats incorrect 4000×4000.

## Performance Targets
100,000+ tracks; cold scan < 10 min (SSD), incremental scan < 30 s, duplicate lookup < 5 s after indexing. Achieved via incremental SQLite scanning, candidate grouping, indexes (path, sha256, MusicBrainz IDs, ISRC, title+artist), cached fingerprints, async downloads, parallel metadata parsing.

## Provider/Plugin Interface Contract
Providers subclass common `Provider` base (`name`, `version`, `priority`, async `initialize`/`shutdown`/`health_check`) and extend a category interface (e.g. `ArtworkProvider` with `search_album`, `download`/`download_artwork`, `validate`; `MetadataProvider` with `search_artist`/`search_album`/`search_track`). All methods async. Return structured errors (network/auth/rate-limit/invalid-response/parsing); never raise UI-facing exceptions or modify app state directly. Discovery from `harmonia/providers/`, later `~/.config/harmonia/plugins/`, eventually Python entry points. Enable/disable/ordering driven by `[providers]` config (TOML), not code.

## Testing
- Tests synthesize real FLAC files with `ffmpeg` (via `music_root` fixture) — **skip if ffmpeg absent**.
- Use in-memory DB in tests: `Database(":memory:")` / `Library(":memory:")`.
- Run: `pytest` (configured with `testpaths = ["tests"]`, `-q`).

## Core Entry Points
- `harmonia/__main__.py` → `harmonia.cli.app:main`
- `harmonia.core.library.Library` — single facade for all frontends
- `harmonia.database.db.Database` — owns SQLite connection, all persistence flows through here
- `harmonia.core.scanner.Scanner` — incremental scanner with file stat checks

## Environment
- `HARMONIA_HOME` — overrides default data/db/log location (used by tests)
- Default DB path via `harmonia.utils.paths.database_path()`