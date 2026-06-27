"""Duplicate detection: group candidates, score confidence, rank quality.

Deliberately false-positive averse (``duplicate_detection.md``). Deleting
music is irreversible, so the engine only detects and ranks — destructive
actions live behind explicit, dry-run-by-default library methods.
"""

from .detector import (
    Confidence,
    DupTrack,
    DuplicateDetector,
    Match,
    dedupe_key,
    similarity,
)
from .report import (
    DuplicateCluster,
    DuplicateReport,
    build_report,
)

__all__ = [
    "Confidence",
    "DupTrack",
    "DuplicateDetector",
    "Match",
    "dedupe_key",
    "similarity",
    "DuplicateCluster",
    "DuplicateReport",
    "build_report",
]
