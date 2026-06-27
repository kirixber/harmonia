"""The core API facade.

Frontends construct one :class:`Library` and call its methods. They never
import :mod:`harmonia.database` or build a :class:`Scanner` themselves — this
is the seam that guarantees CLI, TUI and GUI behave identically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..database import Database
from ..jobs.job import ProgressCallback
from ..providers import ProviderManager
from .metadata.normalize import normalize_tags
from .metadata.rename import RenamePlan, Renamer, RenameStatus
from .metadata.validate import Issue, Severity, validate_tags
from .metadata.writer import TagWriter, WriteResult
from .models import TrackTags
from .scanner import ScanResult, Scanner
from .duplicates import DuplicateReport, build_report, DupTrack
from .artwork import ArtworkEngine
from .quality import QualityEngine

# Fields a caller may edit through edit_track.
_EDITABLE = (
    "title", "artist", "album", "album_artist", "genre", "composer",
    "track_number", "total_tracks", "disc_number", "year", "isrc",
    "musicbrainz_track_id", "musicbrainz_album_id", "musicbrainz_artist_id",
)


@dataclass(slots=True)
class EditOutcome:
    """Result of an edit: what was written plus any validation issues."""

    write: WriteResult | None
    issues: list[Issue] = field(default_factory=list)
    blocked: bool = False

    @property
    def ok(self) -> bool:
        return not self.blocked and self.write is not None and self.write.ok


class Library:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db = Database(db_path)
        self.scanner = Scanner(self.db)
        self.writer = TagWriter(self.scanner.reader)
        self.renamer = Renamer()
        self.quality_engine = QualityEngine(self.db)

        # Provider manager (initialized lazily)
        self._provider_manager: ProviderManager | None = None
        self._artwork_engine: ArtworkEngine | None = None

    def scan(
        self, path: str | Path, progress: ProgressCallback | None = None
    ) -> ScanResult:
        """Index (or re-index) every audio file under ``path``."""
        return self.scanner.scan(path, progress)

    # -- metadata editing --------------------------------------------------

    def _row_to_tags(self, row) -> TrackTags:
        """Read authoritative tags from the file (DB row is a denormalized cache)."""
        return self.scanner.reader.read_tags(row["path"])

    def validate_track(self, track_id: int) -> list[Issue]:
        row = self.db.get_track(track_id)
        if row is None:
            return []
        return validate_tags(self._row_to_tags(row))

    def edit_track(
        self,
        track_id: int,
        changes: dict,
        *,
        dry_run: bool = False,
        source: str = "edit",
        force: bool = False,
    ) -> EditOutcome:
        """Validate → write → verify → record history → refresh the DB row.

        Rejects unknown fields. If the proposed result has ERROR-level
        validation issues the write is blocked unless ``force`` is set.
        """
        row = self.db.get_track(track_id)
        if row is None:
            raise KeyError(f"no track with id {track_id}")
        path = row["path"]

        unknown = set(changes) - set(_EDITABLE)
        if unknown:
            raise ValueError(f"non-editable fields: {sorted(unknown)}")

        proposed = self._apply_changes(self._row_to_tags(row), changes)
        issues = validate_tags(proposed)
        blocking = [i for i in issues if i.severity is Severity.ERROR]
        if blocking and not force and not dry_run:
            return EditOutcome(write=None, issues=issues, blocked=True)

        result = self.writer.apply(path, changes, dry_run=dry_run)

        if result.ok and not dry_run:
            self.db.record_tag_changes(track_id, path, result.changes, source)
            self.scanner.index_file(path)
        return EditOutcome(write=result, issues=issues)

    def normalize_track(self, track_id: int, *, dry_run: bool = False) -> EditOutcome:
        row = self.db.get_track(track_id)
        if row is None:
            raise KeyError(f"no track with id {track_id}")
        _, changes = normalize_tags(self._row_to_tags(row))
        if not changes:
            return EditOutcome(write=None, issues=[])
        change_dict = {c.field: c.new for c in changes}
        return self.edit_track(
            track_id, change_dict, dry_run=dry_run, source="normalize", force=True
        )

    def normalize_all(
        self, *, dry_run: bool = True, progress: ProgressCallback | None = None
    ) -> list[tuple[int, EditOutcome]]:
        """Normalize every track. Defaults to dry-run (preview only)."""
        from ..jobs.job import Progress

        rows = self.db.iter_tracks()
        out: list[tuple[int, EditOutcome]] = []
        for index, row in enumerate(rows, start=1):
            outcome = self.normalize_track(row["id"], dry_run=dry_run)
            if outcome.write and outcome.write.changes:
                out.append((row["id"], outcome))
            if progress:
                progress(Progress(index, len(rows), Path(row["path"]).name))
        return out

    @staticmethod
    def _apply_changes(tags: TrackTags, changes: dict) -> TrackTags:
        from dataclasses import fields as dc_fields

        merged = TrackTags(**{f.name: getattr(tags, f.name) for f in dc_fields(tags)})
        for key, value in changes.items():
            setattr(merged, key, value)
        return merged

    # -- renaming ----------------------------------------------------------

    def preview_rename(
        self, track_id: int, template: str, base_dir=None
    ) -> RenamePlan:
        row = self.db.get_track(track_id)
        if row is None:
            raise KeyError(f"no track with id {track_id}")
        return self.renamer.plan(row["path"], self._row_to_tags(row), template, base_dir)

    def rename_track(
        self, track_id: int, template: str, base_dir=None, *, dry_run: bool = False
    ) -> RenamePlan:
        plan = self.preview_rename(track_id, template, base_dir)
        if not dry_run and plan.status is RenameStatus.RENAME:
            if self.renamer.apply(plan):
                self.db.update_track_path(plan.old_path, plan.new_path)
                self.db.commit()
        return plan

    def rename_all(
        self,
        template: str,
        base_dir=None,
        *,
        dry_run: bool = True,
        progress: ProgressCallback | None = None,
    ) -> list[RenamePlan]:
        """Plan (and optionally apply) a rename across the whole library.

        Defaults to dry-run — nothing moves until ``dry_run=False``.
        """
        from ..jobs.job import Progress

        rows = self.db.iter_tracks()
        plans: list[RenamePlan] = []
        for index, row in enumerate(rows, start=1):
            plan = self.rename_track(row["id"], template, base_dir, dry_run=dry_run)
            plans.append(plan)
            if progress:
                progress(Progress(index, len(rows), Path(plan.old_path).name))
        return plans

    # -- reports -----------------------------------------------------------

    def metadata_report(self):
        """Library-wide metadata health report (see core.reports)."""
        from .reports import generate_metadata_report

        return generate_metadata_report(self.db.tracks_with_names())

    # -- duplicates --------------------------------------------------------

    def duplicate_report(self, review_threshold: int = 75) -> DuplicateReport:
        """Library-wide duplicate detection report."""
        rows = self.db.tracks_for_dedup()
        tracks = [DupTrack.from_row(r) for r in rows]
        return build_report(tracks, review_threshold=review_threshold)

    # -- statistics --------------------------------------------------------

    def stats(self) -> dict:
        return self.db.stats()

    def last_scan(self) -> dict | None:
        row = self.db.last_scan()
        return dict(row) if row else None

    def config_get(self, key: str, default: str | None = None) -> str | None:
        return self.db.config_get(key, default)

    def config_set(self, key: str, value: str) -> None:
        self.db.config_set(key, value)

    def close(self) -> None:
        self.db.close()

    @property
    def provider_manager(self) -> ProviderManager:
        if self._provider_manager is None:
            from ..providers import ProviderManager
            from ..providers.dummy import get_dummy_providers

            self._provider_manager = ProviderManager(self.db)
            for p in get_dummy_providers():
                self._provider_manager.register(p)
            # Note: call initialize_all() before using
        return self._provider_manager

    @property
    def artwork_engine(self) -> ArtworkEngine:
        if self._artwork_engine is None:
            self._artwork_engine = ArtworkEngine(self.db, self.provider_manager)
        return self._artwork_engine

    async def initialize_providers(self) -> None:
        """Initialize all registered providers."""
        await self.provider_manager.initialize_all()

    async def shutdown_providers(self) -> None:
        """Shutdown all providers."""
        await self.provider_manager.shutdown_all()

    # -- artwork -------------------------------------------------------------

    async def search_artwork(self, artist: str, album: str, limit: int = 10):
        """Search for album artwork."""
        return await self.artwork_engine.search_album(artist, album, limit=limit)

    async def download_artwork(self, candidate) -> bytes | None:
        """Download artwork for a candidate."""
        return await self.artwork_engine.download_artwork(candidate)

    def store_artwork(self, data: bytes, **kwargs):
        """Cache artwork bytes to disk (keyed by content hash) and record it."""
        return self.artwork_engine.store_artwork(data, **kwargs)

    def embed_artwork(
        self,
        track_id: int,
        image,
        *,
        mime_type: str = "image/jpeg",
        dry_run: bool = False,
        backup: bool = True,
        only_if_missing: bool = False,
    ):
        """Embed cover art into a track's file (dry-run/backup by default)."""
        return self.artwork_engine.embed_artwork_for_track(
            track_id, image, mime_type=mime_type, dry_run=dry_run,
            backup=backup, only_if_missing=only_if_missing,
        )

    # -- audio quality -------------------------------------------------------

    def analyze_quality(self, track_id: int):
        """Analyze audio quality for a track."""
        return self.quality_engine.analyze_quality(track_id)

    def compare_quality(self, track_ids: list[int]):
        """Compare quality across tracks."""
        return self.quality_engine.compare_quality(track_ids)

    def best_quality(self, track_ids: list[int]) -> int | None:
        """Return the track ID with best quality."""
        return self.quality_engine.best_quality(track_ids)

    def compute_fingerprint(self, track_id: int):
        """Compute acoustic fingerprint."""
        return self.quality_engine.compute_fingerprint(track_id)

    def compute_replaygain(self, track_id: int):
        """Compute ReplayGain values."""
        return self.quality_engine.compute_replaygain(track_id)

    def __enter__(self) -> "Library":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
