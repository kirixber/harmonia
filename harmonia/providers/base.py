"""Provider base classes and interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(self, message: str, kind: str = "internal") -> None:
        super().__init__(message)
        self.kind = kind  # network, auth, rate_limit, invalid_response, parsing, internal


class ProviderCategory(str, Enum):
    ARTWORK = "artwork"
    METADATA = "metadata"
    LYRICS = "lyrics"
    AUDIO_ANALYSIS = "audio_analysis"


@dataclass(slots=True)
class ProviderInfo:
    name: str
    version: str
    category: ProviderCategory
    priority: int = 0  # higher = tried first
    requires_auth: bool = False
    rate_limit: Optional[tuple[int, int]] = None  # (requests, seconds)


class Provider(ABC):
    """Base class for all providers."""

    info: ProviderInfo

    def __init__(self) -> None:
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Called once at startup. Raise to disable provider."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Called at application exit."""

    async def health_check(self) -> bool:
        """Quick check if provider is reachable. Return True if healthy."""
        return True


class ArtworkProvider(Provider):
    """Interface for artwork providers."""

    info: ProviderInfo

    @abstractmethod
    async def search_album(
        self, artist: str, album: str, limit: int = 10
    ) -> list["ArtworkCandidate"]:
        """Search for album artwork. Return list of candidates."""

    @abstractmethod
    async def download_artwork(self, candidate: "ArtworkCandidate") -> bytes:
        """Download artwork bytes for a candidate."""

    @abstractmethod
    async def validate_artwork(self, data: bytes) -> bool:
        """Validate artwork bytes (dimensions, format, etc.)."""


@dataclass(slots=True)
class ArtworkCandidate:
    provider: str
    url: str
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    size_bytes: Optional[int] = None
    confidence: float = 1.0  # 0-1, provider's own confidence

    def cache_key(self) -> str:
        """Unique key for caching this candidate."""
        return f"{self.provider}:{self.url}"


class MetadataProvider(Provider):
    """Interface for metadata providers."""

    info: ProviderInfo

    @abstractmethod
    async def search_artist(self, query: str, limit: int = 10) -> list["ArtistMatch"]:
        """Search for artists."""

    @abstractmethod
    async def search_album(
        self, artist: str, album: str, limit: int = 10
    ) -> list["AlbumMatch"]:
        """Search for albums."""

    @abstractmethod
    async def search_track(
        self, artist: str, title: str, album: Optional[str] = None, limit: int = 10
    ) -> list["TrackMatch"]:
        """Search for tracks."""


@dataclass(slots=True)
class ArtistMatch:
    name: str
    musicbrainz_id: Optional[str] = None
    score: float = 1.0


@dataclass(slots=True)
class AlbumMatch:
    title: str
    artist: str
    musicbrainz_id: Optional[str] = None
    year: Optional[int] = None
    track_count: Optional[int] = None
    score: float = 1.0


@dataclass(slots=True)
class TrackMatch:
    title: str
    artist: str
    album: str
    musicbrainz_id: Optional[str] = None
    isrc: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    duration: Optional[float] = None
    score: float = 1.0