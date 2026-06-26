"""Database layer. The single owner of all SQLite access.

No other module — and certainly no frontend — issues queries directly.
Everything goes through :class:`~harmonia.database.db.Database`.
"""

from .db import Database

__all__ = ["Database"]
