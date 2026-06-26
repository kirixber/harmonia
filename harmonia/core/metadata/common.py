"""Small shared types for the metadata engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FieldChange:
    """One field's before/after value, used by normalize, edit and history."""

    field: str
    old: object
    new: object

    def __str__(self) -> str:
        return f"{self.field}: {self.old!r} → {self.new!r}"
