# Harmonia Architecture

> Version: 0.1 Draft

## Purpose

This document defines the high-level architecture of Harmonia.

The guiding principle is **one backend, many frontends**. Every feature
is implemented once in the core library and reused by the CLI, Textual
TUI, and PySide6 GUI.

------------------------------------------------------------------------

# Architecture Overview

``` text
                   +-------------------+
                   |      CLI          |
                   +-------------------+
                            |
                   +-------------------+
                   |   Textual TUI     |
                   +-------------------+
                            |
                   +-------------------+
                   |    PySide6 GUI    |
                   +-------------------+
                            |
                   =====================
                     Harmonia Core API
                   =====================
          Scanner  Metadata  Artwork  Duplicates
             |         |         |          |
              ---------- Database ----------
                            |
                        SQLite Cache
                            |
                  Online Provider Layer
```

------------------------------------------------------------------------

# Layered Design

## 1. Frontends

Frontends contain **no business logic**.

Responsibilities:

-   User interaction
-   Rendering
-   Progress display
-   Collecting input
-   Calling the core API

The CLI, TUI and GUI should produce identical results because they all
call the same backend.

------------------------------------------------------------------------

## 2. Core Layer

The core layer contains every library-management feature.

Modules:

-   scanner
-   metadata
-   artwork
-   duplicates
-   quality
-   reports
-   configuration
-   jobs

Every module must expose a clean Python API independent of the UI.

------------------------------------------------------------------------

## 3. Database Layer

SQLite stores:

-   indexed tracks
-   albums
-   artists
-   artwork cache
-   provider cache
-   scan history
-   hashes
-   configuration

No UI accesses SQLite directly.

Only the database module performs queries.

------------------------------------------------------------------------

## 4. Provider Layer

External services are abstracted behind interfaces.

Example:

``` python
class ArtworkProvider:
    async def search_album(...)
    async def download(...)
```

Initial providers:

-   Apple Music
-   Qobuz
-   Cover Art Archive
-   MusicBrainz
-   iTunes
-   Deezer

Future providers can be added without changing the core.

------------------------------------------------------------------------

# Directory Layout

``` text
harmonia/
    core/
        scanner/
        metadata/
        artwork/
        duplicates/
        quality/
        reports/

    database/
    providers/
    cli/
    tui/
    gui/
    utils/
    jobs/
```

------------------------------------------------------------------------

# Job System

Long-running operations execute as jobs.

Examples:

-   Scan library
-   Download artwork
-   Compare duplicates
-   Fingerprint tracks

Each job reports:

-   progress
-   elapsed time
-   ETA
-   warnings
-   errors

This keeps all frontends responsive.

------------------------------------------------------------------------

# Caching Strategy

Artwork downloads, metadata lookups and provider responses are cached.

Goals:

-   Avoid unnecessary API calls
-   Reduce rate-limit issues
-   Improve scan performance
-   Allow offline operation after first sync

------------------------------------------------------------------------

# Error Handling

Errors are categorized:

-   User errors
-   File errors
-   Network errors
-   Provider errors
-   Internal errors

Every error should include:

-   message
-   cause
-   suggested action

------------------------------------------------------------------------

# Logging

Every operation is logged.

Log levels:

-   DEBUG
-   INFO
-   WARNING
-   ERROR

Logs are stored under:

``` text
logs/
```

------------------------------------------------------------------------

# Plugin Philosophy

The core should never depend on optional features.

Plugins may provide:

-   Artwork providers
-   Metadata providers
-   Lyrics
-   Last.fm integration
-   Discogs
-   ReplayGain analyzers

Each plugin communicates through defined interfaces.

------------------------------------------------------------------------

# Performance Goals

-   Index 100,000 tracks
-   Incremental rescans
-   Async downloads
-   Parallel metadata parsing
-   Low memory footprint

------------------------------------------------------------------------

# Testing Strategy

Every module must have unit tests.

Integration tests cover:

-   scanning
-   artwork
-   duplicate detection
-   database migrations

------------------------------------------------------------------------

# Future Architecture

Future versions may introduce:

-   Remote API
-   Web dashboard
-   Synchronization
-   Plugin marketplace
-   Distributed artwork cache

------------------------------------------------------------------------

This document is the architectural blueprint for Harmonia and should be
updated whenever a major structural decision changes.
