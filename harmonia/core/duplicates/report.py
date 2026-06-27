"""Duplicate report structures and builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .detector import Confidence, DupTrack, Match


@dataclass(slots=True)
class DuplicateCluster:
    """A group of tracks that are duplicates of each other."""

    tracks: list[DupTrack]
    matches: list[Match] = field(default_factory=list)

    @property
    def best_match(self) -> Optional[Match]:
        if not self.matches:
            return None
        return max(self.matches, key=lambda m: m.score)

    @property
    def confidence(self) -> Confidence:
        bm = self.best_match
        return bm.confidence if bm else Confidence.NONE


@dataclass(slots=True)
class DuplicateReport:
    """Library-wide duplicate scan result."""

    clusters: list[DuplicateCluster] = field(default_factory=list)
    scanned: int = 0

    @property
    def total_duplicate_pairs(self) -> int:
        return sum(len(c.matches) for c in self.clusters)

    @property
    def definite(self) -> int:
        return sum(1 for c in self.clusters if c.confidence is Confidence.DEFINITE)

    @property
    def high(self) -> int:
        return sum(1 for c in self.clusters if c.confidence is Confidence.HIGH)

    @property
    def review(self) -> int:
        return sum(1 for c in self.clusters if c.confidence is Confidence.REVIEW)

    def summary(self) -> dict[str, int]:
        return {
            "definite": self.definite,
            "high": self.high,
            "review": self.review,
            "total_clusters": len(self.clusters),
            "total_pairs": self.total_duplicate_pairs,
        }


def build_report(tracks: list[DupTrack], review_threshold: int = 75) -> DuplicateReport:
    """Build a duplicate report from a list of tracks."""
    from .detector import DuplicateDetector

    detector = DuplicateDetector(review_threshold=review_threshold)
    clusters: list[DuplicateCluster] = []

    for group in detector.candidate_groups(tracks):
        matches = []
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                match = detector.score_pair(group[i], group[j])
                if match.score >= review_threshold:
                    matches.append(match)
        if matches:
            clusters.append(DuplicateCluster(tracks=group, matches=matches))

    return DuplicateReport(clusters=clusters, scanned=len(tracks))