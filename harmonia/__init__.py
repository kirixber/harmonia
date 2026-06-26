"""Harmonia — open-source music library manager.

One backend, many frontends. All business logic lives in this package's
``core``, ``database``, ``providers`` and ``jobs`` layers; the ``cli``,
``tui`` and ``gui`` packages only collect input, render, and call the core.
"""

__version__ = "0.1.0"
APP_NAME = "Harmonia"

__all__ = ["__version__", "APP_NAME"]
