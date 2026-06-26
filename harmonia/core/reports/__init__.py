"""Library-wide reports (metadata health now; more in later phases)."""

from .metadata_report import Report, ReportEntry, generate_metadata_report

__all__ = ["Report", "ReportEntry", "generate_metadata_report"]
