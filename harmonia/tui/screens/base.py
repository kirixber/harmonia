from __future__ import annotations

from textual.screen import Screen

from ...core.library import Library


class BaseScreen(Screen[None]):
    _library: Library | None = None

    @property
    def library(self) -> Library:
        if self._library is None:
            self._library = Library()
        return self._library

    def on_unmount(self) -> None:
        if self._library is not None:
            self._library.close()
            self._library = None
