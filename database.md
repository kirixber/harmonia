# Harmonia Database Design

> Version: 0.1 Draft

## Purpose

The SQLite database is the authoritative index for the user's music
library. It stores metadata, caches provider responses, enables
incremental rescans, and allows the CLI, TUI, and GUI to work from the
same data source.

------------------------------------------------------------------------

# Design Goals

-   Fast lookups
-   Incremental scanning
-   Minimal duplication
-   Safe schema migrations
-   Extensible for plugins
-   Offline-friendly

------------------------------------------------------------------------

# High-Level ER Diagram

``` text
Artists ─────┐
             │
Albums ───── Tracks ───── Artwork
             │
             ├──────── Scan History
             │
             ├──────── Fingerprints
             │
             └──────── ReplayGain

Provider Cache
Config
Jobs
```

------------------------------------------------------------------------

# Core Tables

## tracks

Stores one record per audio file.

Columns:

-   id (INTEGER PRIMARY KEY)
-   path (TEXT UNIQUE)
-   filename
-   extension
-   file_size
-   modified_time
-   sha256
-   codec
-   bitrate
-   sample_rate
-   bit_depth
-   channels
-   duration
-   artist_id
-   album_id
-   title
-   track_number
-   disc_number
-   year
-   genre
-   musicbrainz_track_id
-   isrc
-   artwork_id
-   last_scanned

Indexes:

-   path
-   sha256
-   musicbrainz_track_id
-   isrc
-   title + artist_id

------------------------------------------------------------------------

## artists

-   id
-   name
-   sort_name
-   musicbrainz_artist_id

------------------------------------------------------------------------

## albums

-   id
-   artist_id
-   name
-   year
-   album_artist
-   total_tracks
-   musicbrainz_release_id
-   artwork_id

------------------------------------------------------------------------

## artwork

Stores cached artwork metadata.

Columns:

-   id
-   sha256
-   width
-   height
-   mime_type
-   file_size
-   local_path
-   source
-   downloaded_at

Artwork binaries are stored on disk, not inside SQLite.

------------------------------------------------------------------------

## provider_cache

Caches API responses.

Columns:

-   provider
-   request_hash
-   response_json
-   expires_at
-   created_at

Purpose:

-   Reduce API calls
-   Improve performance
-   Support offline mode

------------------------------------------------------------------------

## fingerprints

Optional table populated only if fingerprinting is enabled.

Columns:

-   track_id
-   acoustid
-   chromaprint
-   confidence

------------------------------------------------------------------------

## replaygain

Stores loudness analysis.

Columns:

-   track_id
-   track_gain
-   album_gain
-   peak

------------------------------------------------------------------------

## scan_history

Records every library scan.

Columns:

-   id
-   started_at
-   finished_at
-   scanned_files
-   new_files
-   updated_files
-   removed_files
-   warnings
-   errors

------------------------------------------------------------------------

## jobs

Tracks long-running background operations.

Columns:

-   id
-   type
-   state
-   progress
-   started_at
-   finished_at
-   message

States:

-   queued
-   running
-   completed
-   failed
-   cancelled

------------------------------------------------------------------------

## config

Application configuration.

Examples:

-   enabled providers
-   artwork resolution threshold
-   duplicate confidence threshold
-   theme
-   cache directory

------------------------------------------------------------------------

# Migration Strategy

Each schema version receives an integer migration ID.

Example:

v1 Initial schema

v2 ReplayGain table

v3 Plugin metadata

Migrations must always be reversible when practical.

------------------------------------------------------------------------

# Indexing Strategy

Indexes prioritize:

-   path
-   hashes
-   MusicBrainz IDs
-   ISRC
-   artist
-   album
-   title

Compound indexes should be added only after profiling.

------------------------------------------------------------------------

# Caching Philosophy

Never query an online provider if a valid cached response exists.

Artwork files are cached on disk.

Metadata responses are cached in SQLite.

------------------------------------------------------------------------

# Performance Targets

-   100,000+ tracks
-   Cold scan \< 10 minutes (SSD target)
-   Incremental scan \< 30 seconds
-   Constant-time path lookup
-   Minimal memory usage

------------------------------------------------------------------------

# Future Tables

-   lyrics
-   playlists
-   listening_history
-   user_tags
-   plugin_data
-   waveform_cache
-   spectral_analysis

------------------------------------------------------------------------

The schema should evolve through migrations while preserving backwards
compatibility whenever possible.
