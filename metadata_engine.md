# Metadata Engine

> Version: 0.1 Draft

## Purpose

The Metadata Engine is responsible for reading, validating, repairing,
normalizing, enriching and writing metadata for every supported audio
format.

It provides a single API for all frontends and is the authoritative
source for metadata operations inside Harmonia.

------------------------------------------------------------------------

# Goals

-   Preserve data integrity
-   Never destroy user data
-   Batch processing
-   Transaction-like writes
-   Format-independent API
-   Extensible provider support

------------------------------------------------------------------------

# Responsibilities

-   Read metadata
-   Write metadata
-   Normalize tags
-   Batch edit tags
-   Rename files/folders
-   Import metadata
-   Export metadata
-   Validate tag consistency

------------------------------------------------------------------------

# Supported Formats

-   FLAC (Vorbis Comments)
-   Opus
-   MP3 (ID3v2)
-   AAC
-   M4A
-   ALAC
-   OGG
-   WAV (limited)

The UI never communicates with format-specific libraries directly.

------------------------------------------------------------------------

# Metadata Model

The engine exposes a unified track model.

``` text
Track
├── Title
├── Artist
├── Album
├── Album Artist
├── Genre
├── Composer
├── Disc Number
├── Track Number
├── Year
├── ISRC
├── MusicBrainz IDs
├── ReplayGain
└── Artwork
```

Format-specific differences are hidden behind adapters.

------------------------------------------------------------------------

# Normalization Rules

Examples:

    IMAGINE DRAGONS

↓

    Imagine Dragons

    feat
    Ft.
    FEAT.

↓

    feat.

Whitespace:

-   Trim leading/trailing spaces
-   Collapse repeated spaces
-   Normalize Unicode

------------------------------------------------------------------------

# Validation

Checks include:

-   Missing title
-   Missing artist
-   Missing album
-   Invalid track number
-   Duplicate MusicBrainz IDs
-   Invalid ISRC
-   Corrupted tags

Each issue receives:

-   Severity
-   Description
-   Suggested fix

------------------------------------------------------------------------

# Rename Engine

Naming templates:

    Title - Artist
    Artist - Title
    Artist/Album/Track - Title
    Disc/Track - Title

Users may create custom templates.

Illegal filename characters are sanitized.

------------------------------------------------------------------------

# Metadata Providers

The engine can enrich tags using plugins.

Examples:

-   MusicBrainz
-   Discogs
-   Last.fm
-   Apple Music

The engine merges provider results instead of blindly replacing existing
tags.

------------------------------------------------------------------------

# Conflict Resolution

Priority:

1.  User edits
2.  Verified IDs (MusicBrainz / ISRC)
3.  Trusted providers
4.  Existing tags
5.  Filename inference

Every automatic change is reversible.

------------------------------------------------------------------------

# Write Strategy

Before writing:

1.  Validate
2.  Backup original values
3.  Apply changes
4.  Verify write
5.  Update database

Partial failures must not corrupt files.

------------------------------------------------------------------------

# Reports

Generate:

-   Missing metadata
-   Inconsistent album artist
-   Duplicate ISRC
-   Unknown genres
-   Invalid years
-   Missing track numbers

CSV and JSON export supported.

------------------------------------------------------------------------

# Future Enhancements

-   AI-assisted metadata repair
-   Multi-language tag support
-   Lyrics integration
-   Mood and BPM detection
-   Automatic genre normalization

------------------------------------------------------------------------

## Guiding Principle

Metadata should become **more consistent** after every Harmonia
operation, never less. Every automatic modification must be explainable,
reversible, and based on verifiable information whenever possible.
