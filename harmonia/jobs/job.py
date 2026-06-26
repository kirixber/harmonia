"""Job progress primitives.

The core reports progress through a simple ``ProgressCallback`` so that the
CLI, TUI and GUI can each render it their own way (a Rich bar, a Textual
widget, a Qt progress dialog) without the core knowing which frontend is
listening.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Progress:
    """A single progress tick handed to a callback."""

    done: int
    total: int
    message: str = ""

    @property
    def fraction(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(1.0, self.done / self.total)

    @property
    def percent(self) -> int:
        return int(self.fraction * 100)


# A frontend supplies one of these to receive live updates. None == headless.
ProgressCallback = Callable[[Progress], None]
