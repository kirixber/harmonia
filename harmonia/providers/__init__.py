"""Provider package: discovery, base classes, and built-in providers."""

from .base import (
    Provider,
    ProviderCategory,
    ProviderError,
    ProviderInfo,
    ArtworkProvider,
    ArtworkCandidate,
    MetadataProvider,
    ArtistMatch,
    AlbumMatch,
    TrackMatch,
)
from .manager import ProviderManager

__all__ = [
    "Provider",
    "ProviderCategory",
    "ProviderError",
    "ProviderInfo",
    "ArtworkProvider",
    "ArtworkCandidate",
    "MetadataProvider",
    "ArtistMatch",
    "AlbumMatch",
    "TrackMatch",
    "ProviderManager",
]