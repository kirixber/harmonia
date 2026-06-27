"""Dummy providers for testing and offline development."""

from __future__ import annotations

from typing import Optional

from .base import (
    ArtworkCandidate,
    ArtworkProvider,
    ArtistMatch,
    AlbumMatch,
    TrackMatch,
    MetadataProvider,
    Provider,
    ProviderCategory,
    ProviderError,
    ProviderInfo,
)


class DummyArtworkProvider(ArtworkProvider):
    """A dummy artwork provider that returns placeholder results."""

    info = ProviderInfo(
        name="dummy",
        version="0.1.0",
        category=ProviderCategory.ARTWORK,
        priority=0,
    )

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def search_album(
        self, artist: str, album: str, limit: int = 10
    ) -> list[ArtworkCandidate]:
        # Return a dummy candidate
        return [
            ArtworkCandidate(
                provider="dummy",
                url=f"https://example.com/artwork/{artist}/{album}.jpg",
                width=500,
                height=500,
                format="image/jpeg",
                confidence=0.5,
            )
        ][:limit]

    async def download_artwork(self, candidate: ArtworkCandidate) -> bytes:
        # Return a minimal 1x1 JPEG
        return bytes.fromhex(
            "FFD8FFE000104A46494600010101004800480000FFDB004300080606070605080707070909080A0C140D0C0B0B0C1912130F141D1A1F1E1D1A1C1C20242E2720222C231C1C2837292C30313434341F27393D38323C2E333432FFC00011080001000103012200021101031101FFC4001F0000010501010101010100000000000000000102030405060708090A0BFFC400B5100002010303020403050504040000017D01020300041105122131410613516107227114328191A1082342B1C11552D1F02433627282090A161718191A25262728292A3435363738393A434445464748494A535455565758595A636465666768696A737475767778797A838485868788898A92939495969798999AA2A3A4A5A6A7A8A9AAB2B3B4B5B6B7B8B9BAC2C3C4C5C6C7C8C9CAD2D3D4D5D6D7D8D9DAE1E2E3E4E5E6E7E8E9EAF1F2F3F4F5F6F7F8F9FAFFDA000C03010002110311003F00"
        )

    async def validate_artwork(self, data: bytes) -> bool:
        return data.startswith(b"\xFF\xD8\xFF")


class DummyMetadataProvider(MetadataProvider):
    """A dummy metadata provider for testing."""

    info = ProviderInfo(
        name="dummy",
        version="0.1.0",
        category=ProviderCategory.METADATA,
        priority=0,
    )

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def search_artist(self, query: str, limit: int = 10) -> list[ArtistMatch]:
        return [ArtistMatch(name=query, score=1.0)][:limit]

    async def search_album(self, artist: str, album: str, limit: int = 10) -> list[AlbumMatch]:
        return [AlbumMatch(title=album, artist=artist, score=1.0)][:limit]

    async def search_track(
        self, artist: str, title: str, album: Optional[str] = None, limit: int = 10
    ) -> list[TrackMatch]:
        return [TrackMatch(title=title, artist=artist, album=album or "", score=1.0)][:limit]


def get_dummy_providers() -> list[Provider]:
    """Return list of dummy providers for offline testing."""
    return [DummyArtworkProvider(), DummyMetadataProvider()]