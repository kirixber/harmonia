# Duplicate Detection Engine

> Version: 0.1 Draft

## Purpose

The Duplicate Detection Engine identifies multiple copies of the same
recording while minimizing false positives. It combines metadata,
identifiers, file properties, and optional audio fingerprinting into a
weighted confidence score.

------------------------------------------------------------------------

# Objectives

-   Extremely low false-positive rate
-   Fast enough for libraries with 100,000+ tracks
-   Deterministic results
-   Safe review before deletion
-   Incremental rescanning

------------------------------------------------------------------------

# Detection Pipeline

``` text
Library Scan
      │
Metadata Extraction
      │
Normalization
      │
Candidate Grouping
      │
Weighted Comparison
      │
Confidence Score
      │
Quality Ranking
      │
User Review / Auto Action
```

------------------------------------------------------------------------

# Metadata Normalization

Before comparison, normalize:

-   Unicode normalization
-   Trim whitespace
-   Collapse repeated spaces
-   Case folding
-   Remove common punctuation differences
-   Standardize "feat.", "ft.", "&"

Examples:

    The Weeknd
    the weeknd
    THE WEEKND

become:

    the weeknd

------------------------------------------------------------------------

# Candidate Grouping

Only files that are likely related are compared.

Primary grouping keys:

-   MusicBrainz Track ID
-   ISRC
-   Normalized title + artist
-   Duration bucket (±1 second)

This avoids O(n²) comparisons.

------------------------------------------------------------------------

# Confidence Score

  Signal                   Weight
  ---------------------- --------
  MusicBrainz Track ID        100
  ISRC                         95
  Audio Fingerprint            90
  Title                        35
  Artist                       30
  Album                        10
  Track Number                  5
  Duration                     20

Example:

    Title      ✓
    Artist     ✓
    Duration   ✓
    Album      ✗
    ISRC       ✓

    Confidence = 96%

Thresholds:

-   99--100%: Definite duplicate
-   90--98%: High confidence
-   75--89%: Needs review
-   \<75%: Not a duplicate

------------------------------------------------------------------------

# Quality Ranking

When duplicates are found, choose the preferred file.

Ranking order:

1.  Lossless over lossy
2.  Higher bit depth
3.  Higher sample rate
4.  Higher bitrate (lossy)
5.  Longer duration (if mismatch)
6.  More complete metadata
7.  Embedded artwork
8.  Larger file size
9.  Newer encoder (when known)

The ranking policy should be configurable.

------------------------------------------------------------------------

# Safe Actions

No destructive action occurs without one of:

-   Dry run
-   Interactive review
-   Explicit auto-delete configuration

Recommended workflow:

    Scan
    ↓
    Preview
    ↓
    Backup / Trash
    ↓
    Permanent delete

------------------------------------------------------------------------

# Fingerprinting

Optional support:

-   Chromaprint
-   AcoustID

Fingerprints improve matching when metadata is incorrect or missing.

------------------------------------------------------------------------

# Performance

Strategies:

-   Candidate grouping
-   SQLite indexes
-   Cached fingerprints
-   Parallel metadata parsing
-   Incremental scans

Target:

-   100,000 tracks
-   \<5 seconds duplicate lookup after indexing

------------------------------------------------------------------------

# Reports

Outputs include:

-   Duplicate groups
-   Confidence
-   Kept file
-   Removed file(s)
-   Reasoning
-   Space saved

CSV and JSON export supported.

------------------------------------------------------------------------

# Future Improvements

-   Detect transcodes
-   Identify alternate masters
-   Multi-disc awareness
-   Live duplicate detection during import
-   Machine-learning assisted confidence tuning

------------------------------------------------------------------------

## Design Principle

Deleting music is irreversible.

The engine should always prioritize correctness over aggressiveness.
