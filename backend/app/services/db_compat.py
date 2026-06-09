from __future__ import annotations
"""
Database-agnostic date formatting for SQLAlchemy queries.
SQLite uses strftime(); PostgreSQL uses TO_CHAR().
"""
from sqlalchemy import func
from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

# Mapping from SQLite strftime formats to PostgreSQL TO_CHAR formats
_PG_FORMAT: dict[str, str] = {
    "%Y-%m-%d": "YYYY-MM-DD",
    "%Y-W%W":   "IYYY-IW",
    "%Y-%m":    "YYYY-MM",
    "%Y":       "YYYY",
}


def date_format(fmt: str, col):
    """Return a SQLAlchemy expression that formats a date column.

    Args:
        fmt: SQLite strftime format string (e.g. '%Y-%m')
        col: SQLAlchemy column expression
    """
    if _is_sqlite:
        return func.strftime(fmt, col)
    pg_fmt = _PG_FORMAT.get(fmt)
    if pg_fmt is None:
        raise ValueError(f"No PostgreSQL equivalent for strftime format {fmt!r}")
    return func.to_char(col, pg_fmt)
