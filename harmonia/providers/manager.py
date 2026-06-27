"""Provider Manager: discovery, ordering, retries, rate limiting, caching."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .base import (
    ArtworkCandidate,
    ArtworkProvider,
    MetadataProvider,
    Provider,
    ProviderCategory,
    ProviderError,
    ProviderInfo,
)

from ..database import Database
from ..utils.logging import get_logger

log = get_logger(__name__)


@dataclass(slots=True)
class RateLimiter:
    """Token bucket rate limiter per provider."""
    requests: int
    period: int  # seconds
    tokens: float = field(default=0, init=False)
    last_refill: float = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.requests)
        self.last_refill = time.monotonic()

    async def acquire(self) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self.last_refill
            if elapsed >= self.period:
                self.tokens = float(self.requests)
                self.last_refill = now
            if self.tokens >= 1:
                self.tokens -= 1
                return
            await asyncio.sleep(0.1)


class ProviderManager:
    """Manages provider lifecycle, ordering, retries, rate limiting, and caching."""

    def __init__(self, db: Database, config: Optional[dict] = None) -> None:
        self.db = db
        self.config = config or {}
        self._providers: dict[ProviderCategory, list[Provider]] = defaultdict(list)
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._initialized = False

    def register(self, provider: Provider) -> None:
        """Register a provider instance."""
        self._providers[provider.info.category].append(provider)

    async def initialize_all(self) -> None:
        """Initialize all registered providers. Failed providers are logged and skipped."""
        for category, providers in self._providers.items():
            for p in providers:
                try:
                    await p.initialize()
                    if p.info.rate_limit:
                        self._rate_limiters[p.info.name] = RateLimiter(*p.info.rate_limit)
                except Exception as e:
                    # Provider failed to initialize - log and continue
                    print(f"Provider {p.info.name} failed to initialize: {e}")

        # Sort by priority (higher first)
        for providers in self._providers.values():
            providers.sort(key=lambda p: p.info.priority, reverse=True)

        self._initialized = True

    async def shutdown_all(self) -> None:
        for providers in self._providers.values():
            for p in providers:
                try:
                    await p.shutdown()
                except Exception:
                    pass

    def get_providers(self, category: ProviderCategory) -> list[Provider]:
        return self._providers.get(category, [])

    # --- Caching (metadata responses only; image bytes never go in SQLite) ---

    def _request_hash(self, *parts: str) -> str:
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    # --- Artwork ---

    async def search_artwork(
        self, artist: str, album: str, limit: int = 10
    ) -> list[ArtworkCandidate]:
        """Search all artwork providers concurrently, merge results."""
        request_hash = self._request_hash("search", artist, album, str(limit))
        cached = self.db.provider_cache_get(
            ProviderCategory.ARTWORK.value, request_hash, max_age_days=90
        )
        if cached:
            return [ArtworkCandidate(**c) for c in json.loads(cached)]

        providers = self.get_providers(ProviderCategory.ARTWORK)
        if not providers:
            return []

        async def search_one(p: ArtworkProvider) -> list[ArtworkCandidate]:
            try:
                if p.info.rate_limit:
                    await self._rate_limiters[p.info.name].acquire()
                return await p.search_album(artist, album, limit=limit)
            except ProviderError as e:
                log.warning("Artwork provider %s error: %s", p.info.name, e)
                return []
            except Exception as e:  # provider isolation: never fatal
                log.warning("Artwork provider %s unexpected error: %s", p.info.name, e)
                return []

        results = await asyncio.gather(*[search_one(p) for p in providers])
        merged: list[ArtworkCandidate] = []
        for r in results:
            merged.extend(r)

        # Deduplicate by URL
        seen = set()
        unique = []
        for c in merged:
            if c.url not in seen:
                seen.add(c.url)
                unique.append(c)

        # Sort by confidence desc
        unique.sort(key=lambda c: c.confidence, reverse=True)
        unique = unique[:limit]

        self.db.provider_cache_set(
            ProviderCategory.ARTWORK.value, request_hash,
            json.dumps([{
                "provider": c.provider, "url": c.url, "thumbnail_url": c.thumbnail_url,
                "width": c.width, "height": c.height, "format": c.format,
                "size_bytes": c.size_bytes, "confidence": c.confidence
            } for c in unique]),
        )

        return unique

    async def download_artwork(self, candidate: ArtworkCandidate) -> Optional[bytes]:
        """Download and validate artwork bytes.

        Returns raw bytes; on-disk caching (keyed by content hash) is the
        artwork engine's job — image bytes are never stored in SQLite.
        """
        provider = None
        for p in self.get_providers(ProviderCategory.ARTWORK):
            if p.info.name == candidate.provider:
                provider = p
                break
        if not provider:
            return None

        try:
            if provider.info.rate_limit:
                await self._rate_limiters[provider.info.name].acquire()
            data = await provider.download_artwork(candidate)
            if await provider.validate_artwork(data):
                return data
        except Exception as e:  # provider isolation
            log.warning("Artwork download failed (%s): %s", candidate.provider, e)
        return None

    # --- Metadata (placeholder for v0.4+) ---

    async def search_metadata(self, *args, **kwargs) -> list:
        """Placeholder for metadata search (v0.4+)."""
        return []