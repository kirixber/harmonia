"""Metadata engine: read (v0.1) and, later, validate/normalize/write tags.

The UI never talks to format-specific libraries; it goes through this
module's :class:`~harmonia.core.metadata.reader.MetadataReader`.
"""

from .reader import MetadataReader

__all__ = ["MetadataReader"]
