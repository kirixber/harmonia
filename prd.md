# Harmonia PRD

## Vision

An open-source, cross-platform music library manager with one shared
backend powering a CLI, Textual TUI, and PySide6 GUI.

## Goals

-   Incremental SQLite-based scanning
-   Duplicate detection
-   Metadata normalization
-   Multi-provider artwork management
-   Audio quality analysis
-   Cross-platform support

## Core Modules

-   Scanner
-   Database
-   Metadata
-   Artwork
-   Duplicate Engine
-   Audio Analysis
-   Reports
-   Plugin System

## Artwork Providers (priority)

1.  Apple Music
2.  Qobuz
3.  Cover Art Archive
4.  MusicBrainz
5.  iTunes
6.  Deezer

## Tech Stack

Python 3.13, SQLite, Mutagen, aiohttp, Pillow, RapidFuzz, Rich, Textual,
PySide6, FFmpeg.
