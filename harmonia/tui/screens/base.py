from __future__ import annotations

from textual.screen import Screen

from ...core.library import Library


class BaseScreen(Screen[None]):
    """Base screen owning one cross-thread-safe Library per screen.

    Some screens run blocking work in Textual thread workers (e.g. scanning).
    SQLite connections are thread-affine, so the Library is created up front
    on the UI thread with ``check_same_thread=False`` to allow a worker to
    use it and the UI thread to close it on unmount.
    """

    _library: Library | None = None

    @property
    def library(self) -> Library:
        if self._library is None:
            self._library = Library(check_same_thread=False)
        return self._library

    def on_mount(self) -> None:
        # Ensure the connection is created on the UI thread, not lazily on
        # whichever worker thread happens to touch it first.
        _ = self.library

    def on_unmount(self) -> None:
        if self._library is not None:
            self._library.close()
            self._library = None
