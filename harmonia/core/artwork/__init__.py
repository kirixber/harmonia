"""Artwork engine: search, download, cache to disk, record in the DB.

Caching policy (architecture.md / database.md): image binaries live on disk
under ``cache/artwork/<sha256>.jpg`` keyed by *content* hash; only their
metadata rows live in SQLite, and all SQL goes through the database layer.
"""

from __future__ import annotations

import hashlib
import shutil
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


@dataclass(slots=True)
class EmbedResult:
    """Result of embedding artwork into an audio file."""

    path: str
    embedded: bool = False
    skipped: bool = False
    backup_path: Optional[str] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


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

    # -- embedding ---------------------------------------------------------

    def embed_artwork(
        self,
        track_path: str | Path,
        image: bytes | str | Path,
        *,
        mime_type: str = "image/jpeg",
        dry_run: bool = False,
        backup: bool = True,
        only_if_missing: bool = False,
    ) -> EmbedResult:
        """Embed cover art into an audio file.

        Favors correctness/safety over aggressiveness (architecture.md):
        defaults to backing up the original file and never overwrites an
        existing cover unless asked. ``image`` may be raw bytes or a path
        to an image on disk (e.g. a cached artwork file).
        """
        track = Path(track_path)
        if not track.exists():
            return EmbedResult(str(track), error="track not found")

        if isinstance(image, (str, Path)):
            img_path = Path(image)
            if not img_path.exists():
                return EmbedResult(str(track), error="image not found")
            data = img_path.read_bytes()
        else:
            data = image
        if not data:
            return EmbedResult(str(track), error="empty image data")

        try:
            has_cover = self._has_embedded_cover(track)
        except Exception as exc:  # unreadable / unsupported file
            return EmbedResult(str(track), error=f"cannot read track: {exc}")

        if only_if_missing and has_cover:
            return EmbedResult(str(track), skipped=True)

        if dry_run:
            return EmbedResult(str(track), embedded=True)

        backup_path: Optional[str] = None
        if backup:
            dest = track.with_suffix(track.suffix + ".bak")
            shutil.copy2(track, dest)
            backup_path = str(dest)

        try:
            self._write_cover(track, data, mime_type)
        except Exception as exc:
            # Restore from backup so a partial write never corrupts the file.
            if backup_path:
                shutil.copy2(backup_path, track)
            return EmbedResult(str(track), error=f"embed failed: {exc}",
                               backup_path=backup_path)

        return EmbedResult(str(track), embedded=True, backup_path=backup_path)

    def embed_artwork_for_track(
        self,
        track_id: int,
        image: bytes | str | Path,
        *,
        mime_type: str = "image/jpeg",
        dry_run: bool = False,
        backup: bool = True,
        only_if_missing: bool = False,
    ) -> EmbedResult:
        """Embed artwork into the file backing a DB track id."""
        row = self.db.get_track(track_id)
        if not row:
            return EmbedResult("", error=f"no track with id {track_id}")
        return self.embed_artwork(
            row["path"], image, mime_type=mime_type, dry_run=dry_run,
            backup=backup, only_if_missing=only_if_missing,
        )

    @staticmethod
    def _has_embedded_cover(path: Path) -> bool:
        """True if the file already carries embedded cover art."""
        from mutagen import File as MutagenFile
        from mutagen.flac import FLAC
        from mutagen.mp4 import MP4
        from mutagen.id3 import ID3

        audio = MutagenFile(str(path))
        if audio is None:
            return False
        if isinstance(audio, FLAC):
            return bool(audio.pictures)
        if isinstance(audio, MP4):
            return bool(audio.tags and audio.tags.get("covr"))
        tags = getattr(audio, "tags", None)
        if isinstance(tags, ID3):
            return bool(tags.getall("APIC"))
        # Opus/OGG store cover art in METADATA_BLOCK_PICTURE.
        if tags is not None and "metadata_block_picture" in tags:
            return True
        return False

    @staticmethod
    def _write_cover(path: Path, data: bytes, mime_type: str) -> None:
        """Write/replace embedded cover art, dispatching on container type."""
        import base64

        from mutagen import File as MutagenFile
        from mutagen.flac import FLAC, Picture
        from mutagen.mp4 import MP4, MP4Cover
        from mutagen.id3 import ID3, APIC
        from mutagen.oggopus import OggOpus
        from mutagen.oggvorbis import OggVorbis

        suffix = path.suffix.lower()

        def _picture() -> Picture:
            pic = Picture()
            pic.type = 3  # front cover
            pic.mime = mime_type
            pic.data = data
            return pic

        if suffix == ".flac":
            audio = FLAC(str(path))
            audio.clear_pictures()
            audio.add_picture(_picture())
            audio.save()
            return

        if suffix in (".m4a", ".mp4", ".aac", ".alac"):
            audio = MP4(str(path))
            fmt = MP4Cover.FORMAT_PNG if "png" in mime_type else MP4Cover.FORMAT_JPEG
            audio["covr"] = [MP4Cover(data, imageformat=fmt)]
            audio.save()
            return

        if suffix == ".mp3":
            try:
                tags = ID3(str(path))
            except Exception:
                tags = ID3()
            tags.delall("APIC")
            tags.add(APIC(encoding=3, mime=mime_type, type=3, desc="Cover", data=data))
            tags.save(str(path))
            return

        if suffix in (".opus", ".ogg", ".oga"):
            audio = MutagenFile(str(path))
            if not isinstance(audio, (OggOpus, OggVorbis)):
                raise ValueError(f"unsupported ogg container: {type(audio).__name__}")
            pic = _picture()
            encoded = base64.b64encode(pic.write()).decode("ascii")
            audio["metadata_block_picture"] = [encoded]
            audio.save()
            return

        raise ValueError(f"artwork embedding not supported for {suffix}")
