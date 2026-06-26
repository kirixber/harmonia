# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

**v0.1 implemented** (repo scaffold, SQLite layer + migrations, incremental scanner, Mutagen
metadata reader, core `Library` facade, Rich CLI main menu). Remaining phases (v0.2+) are still
spec-only. The design docs (`architecture.md`, `database.md`, `metadata_engine.md`,
`artwork_pipeline.md`, `duplicate_detection.md`, `providers.md`, `plugin_system.md`, `prd.md`,
`implementation_plan.md`) are the authoritative blueprint — update the relevant spec whenever a
structural decision changes.

Stack (from `prd.md`): Python 3.13+, SQLite (stdlib `sqlite3`), Mutagen, Rich now; aiohttp, Pillow,
RapidFuzz, Textual, PySide6, FFmpeg arrive with the phases that need them.

## Commands

```bash
pip install -e ".[dev]"        # install with dev deps (pytest)
harmonia                       # launch interactive main menu (default)
harmonia scan <path>           # index a directory recursively
harmonia stats                 # library statistics
python -m harmonia ...         # same entry point without the console script
pytest                         # run the suite
pytest tests/test_scanner.py::test_incremental_skip_unchanged   # single test
HARMONIA_HOME=/tmp/h harmonia stats   # override the data/db/log location (used by tests)
```

Tests synthesize real FLAC files with `ffmpeg` (via the `music_root` fixture) and **skip** if
`ffmpeg` is absent. Use an in-memory DB in tests with `Database(":memory:")` / `Library(":memory:")`.

Build order is staged (`implementation_plan.md`): v0.1 scanner + SQLite + metadata → v0.2 editing/
renaming → v0.3 duplicates → v0.4 artwork → v0.5 audio analysis → v0.6 Textual TUI → v0.7 PySide6
GUI → v1.0 docs/tests/CI.

## Architecture — the one rule that governs everything

**One backend, many frontends.** Every feature is implemented once in the core library and reused
by all three frontends. The CLI, Textual TUI, and PySide6 GUI must produce identical results
because they all call the same core API. These constraints are not optional:

- **Frontends contain no business logic.** They only collect input, render, show progress, and call
  the core. Any logic that lives in a frontend is a bug.
- **Only the database module touches SQLite.** No frontend and no other core module issues queries
  directly.
- **The core never contains provider-specific logic.** It requests a *capability* (artwork,
  metadata, lyrics, audio analysis); the Provider Manager decides *which* provider fulfills it. The
  core must never know how a given provider works.
- **The core never depends on optional features.** Providers and analyzers are plugins behind
  defined interfaces; a missing/failing plugin is logged and disabled, never fatal.

Intended layout (`harmonia/`): `core/{scanner,metadata,artwork,duplicates,quality,reports}`,
`database/`, `providers/`, `cli/`, `tui/`, `gui/`, `utils/`, `jobs/`.

## Cross-cutting subsystems

- **Jobs** (`jobs/`): all long-running work (scan, artwork download, duplicate compare, fingerprint)
  runs as a job reporting progress / elapsed / ETA / warnings / errors, with states
  queued→running→completed/failed/cancelled. This is what keeps every frontend responsive.
- **Providers / Provider Manager**: providers run **concurrently** and results are **merged**, not
  queried serially. Manager owns discovery, ordering, retries, rate limiting, health checks, and
  caching. Every request is hashed (SHA256 of artist/album/track) → cached in SQLite. Priority order
  is configurable; the default artwork order is Apple Music → Qobuz → Cover Art Archive →
  MusicBrainz → iTunes → Deezer.
- **Caching**: never call an online provider when a valid cached response exists. Metadata responses
  cache in SQLite (~90d); artwork *binaries* live on disk under `cache/artwork/<sha256>.jpg` (~30d)
  while only their metadata rows live in SQLite. Image bytes are never stored inside SQLite.
- **Database migrations**: schema versions have integer migration IDs and must be reversible when
  practical. UI never bypasses the database module.

## Safety invariants (do not weaken these)

These are the project's core promises; preserve them in any implementation:

- **Deleting music and writing tags are irreversible** — favor correctness over aggressiveness.
  Duplicate detection and artwork/metadata writes default to dry-run / preview / backup; nothing is
  overwritten or deleted without explicit confirmation or opt-in configuration.
- **Metadata writes are transaction-like**: validate → back up original values → apply → verify →
  update DB. A partial failure must never corrupt a file. Every automatic change is reversible and
  explainable.
- **Duplicate confidence is a weighted score** with deliberately low false-positive bias. Candidates
  are grouped first (by MusicBrainz Track ID, ISRC, normalized title+artist, ±1s duration bucket) to
  avoid O(n²) comparison. Thresholds: 99–100 definite, 90–98 high, 75–89 needs review, <75 not a
  duplicate.
- **Conflict resolution priority** (metadata): user edits > verified IDs (MusicBrainz/ISRC) > trusted
  providers > existing tags > filename inference. Merge provider results; never blindly replace.
- **Artwork favors correctness over resolution**: a verified 1500×1500 cover beats an incorrect
  4000×4000 one.

## Performance targets to design against

100,000+ tracks; cold scan < 10 min (SSD), incremental scan < 30 s, duplicate lookup < 5 s after
indexing. Achieved via incremental SQLite scanning, candidate grouping, indexes (path, sha256,
MusicBrainz IDs, ISRC, title+artist), cached fingerprints, async downloads, and parallel metadata
parsing.

## Provider/plugin interface contract

Providers subclass a common `Provider` base (`name`, `version`, `priority`, async
`initialize`/`shutdown`/`health_check`) and extend a category interface — e.g. `ArtworkProvider`
(`search_album`, `download`/`download_artwork`, `validate`) or `MetadataProvider`
(`search_artist`/`search_album`/`search_track`). All provider methods are async. Providers return
**structured errors** (network / auth / rate-limit / invalid-response / parsing) and must never raise
UI-facing exceptions or modify application state directly. Discovery is from `harmonia/providers/`,
later `~/.config/harmonia/plugins/`, eventually Python entry points. Enable/disable and ordering are
driven by `[providers]` config (TOML), not code.
