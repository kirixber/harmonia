# Artwork Pipeline

> Version: 0.1 Draft

## Purpose

The Artwork Pipeline is responsible for discovering, validating,
downloading, caching, embedding and maintaining album artwork across the
user's music library.

The primary objective is to always use the highest-quality verified
artwork while minimizing unnecessary downloads.

------------------------------------------------------------------------

# Design Goals

-   Highest available resolution
-   Correct album matching
-   Provider-agnostic architecture
-   Offline cache
-   Safe replacement
-   Batch processing
-   Resume interrupted jobs

------------------------------------------------------------------------

# Pipeline Overview

``` text
Library Scan
      │
Missing / Low Quality Artwork
      │
Album Identification
      │
Provider Search
      │
Candidate Collection
      │
Quality Scoring
      │
Validation
      │
Download
      │
Disk Cache
      │
Embed Into Tracks
      │
Generate Report
```

------------------------------------------------------------------------

# Artwork Providers

Providers are queried in configurable priority order.

Default order:

1.  Apple Music
2.  Qobuz
3.  Cover Art Archive
4.  MusicBrainz
5.  iTunes
6.  Deezer

Future:

-   Discogs
-   TIDAL
-   Last.fm
-   Fanart.tv

------------------------------------------------------------------------

# Provider Interface

Every provider must implement:

``` python
class ArtworkProvider:
    async def search_album(...)
    async def fetch_candidates(...)
    async def download(...)
    async def health_check(...)
```

The core never communicates with provider-specific APIs directly.

------------------------------------------------------------------------

# Candidate Validation

Each candidate receives a score.

Factors include:

-   Album title similarity
-   Artist similarity
-   Release year
-   Track count
-   MusicBrainz Release ID
-   UPC (when available)
-   Image resolution
-   Source reliability

Low-confidence candidates require user review.

------------------------------------------------------------------------

# Artwork Quality Ranking

Resolution is not the only metric.

Ranking:

1.  Correct release match
2.  Square aspect ratio
3.  Resolution
4.  JPEG quality
5.  Color profile
6.  Compression artifacts
7.  File size

Preferred minimum:

-   1400×1400

Preferred target:

-   3000×3000+

------------------------------------------------------------------------

# Cache

Artwork is stored separately from tracks.

``` text
cache/
    artwork/
        sha256.jpg
```

Benefits:

-   Prevent duplicate downloads
-   Offline operation
-   Instant reuse

SQLite stores metadata while image files remain on disk.

------------------------------------------------------------------------

# Embedding

Supported formats:

-   FLAC
-   Opus
-   MP3
-   AAC
-   M4A

Options:

-   Replace existing artwork
-   Replace only low-resolution artwork
-   Embed only if missing
-   Save cover.jpg
-   Save folder.jpg

------------------------------------------------------------------------

# Safety

Default behaviour:

-   Preview changes
-   Backup original tags
-   Dry-run support

Nothing is overwritten without explicit confirmation or configuration.

------------------------------------------------------------------------

# Batch Processing

Artwork downloads are asynchronous.

Pipeline:

1.  Build album queue
2.  Query providers
3.  Cache responses
4.  Download selected artwork
5.  Embed
6.  Update database

Progress information:

-   Albums completed
-   Current provider
-   ETA
-   Errors
-   Retry count

------------------------------------------------------------------------

# Reporting

Reports include:

-   Albums updated
-   Missing artwork
-   Low-resolution artwork
-   Download failures
-   Provider usage
-   Cache hit ratio

CSV and JSON export supported.

------------------------------------------------------------------------

# Future Enhancements

-   AI upscaling (optional)
-   Artwork comparison viewer
-   Animated artwork support
-   Multi-disc artwork
-   Booklet downloads
-   Back cover support
-   Artist images
-   Automatic artwork refresh

------------------------------------------------------------------------

## Guiding Principle

Artwork should always favor **correctness over resolution**.

A verified 1500×1500 cover is preferable to an incorrect 4000×4000
image.
