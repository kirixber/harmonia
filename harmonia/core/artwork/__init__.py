"""Artwork engine: search, download, cache to disk, record in the DB.

Caching policy (architecture.md / database.md): image binaries live on disk
under ``cache/artwork/<sha256>.jpg`` keyed by *content* hash; only their
metadata rows live in SQLite, and all SQL goes through the database layer.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ...database import Database
from ...providers import ArtworkCandidate, ProviderManager
from ...utils.paths import artwork_cache_dir, ensure_dir


@dataclass(slots=True)
class ArtworkResult:
    """Result of an artwork fetch for an album."""

    candidate: ArtworkCandidate
    sha256: Optional[str] = None
    local_path: Optional[str] = None
    error: Optional[str] = None


class ArtworkEngine:
    """High-level artwork operations over the Provider Manager."""

    def __init__(self, db: Database, provider_manager: ProviderManager) -> None:
        self.db = db
        self.pm = provider_manager

    async def search_album(
        self, artist: str, album: str, limit: int = 10
    ) -> list[ArtworkCandidate]:
        return await self.pm.search_artwork(artist, album, limit=limit)

    async def download_artwork(self, candidate: ArtworkCandidate) -> Optional[bytes]:
        return await self.pm.download_artwork(candidate)

    def get_cached_artwork(self, sha256: str) -> Optional[Path]:
        """Return the on-disk path for cached artwork, if present and valid."""
        row = self.db.get_artwork(sha256)
        if row and row["local_path"]:
            path = Path(row["local_path"])
            if path.exists():
                return path
        return None

    def store_artwork(
        self,
        data: bytes,
        *,
        width: int = 0,
        height: int = 0,
        mime_type: str = "image/jpeg",
        source: str = "unknown",
    ) -> tuple[str, Path]:
        """Write artwork bytes to disk (keyed by content hash) and record it."""
        sha256 = hashlib.sha256(data).hexdigest()
        cache_root = ensure_dir(artwork_cache_dir())
        local_path = cache_root / f"{sha256}.jpg"
        local_path.write_bytes(data)

        self.db.upsert_artwork(
            sha256=sha256, width=width, height=height, mime_type=mime_type,
            file_size=len(data), local_path=str(local_path), source=source,
        )
        return sha256, local_path

    async def fetch_and_store(
        self, artist: str, album: str, limit: int = 5
    ) -> list[ArtworkResult]:
        """Search, download and cache artwork candidates for an album."""
        candidates = await self.search_album(artist, album, limit=limit)
        results: list[ArtworkResult] = []
        for candidate in candidates:
            data = await self.download_artwork(candidate)
            if not data:
                results.append(ArtworkResult(candidate, error="download failed"))
                continue
            sha256, local_path = self.store_artwork(
                data, width=candidate.width or 0, height=candidate.height or 0,
                mime_type=candidate.format or "image/jpeg", source=candidate.provider,
            )
            results.append(ArtworkResult(candidate, sha256=sha256,
                                         local_path=str(local_path)))
        return results
