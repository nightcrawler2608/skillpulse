"""Database connection helper (PostgreSQL on Neon)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from skillpulse.config import get_settings


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Open a connection, commit on success, roll back on error, always close.

    Usage:
        with get_connection() as conn:
            conn.execute("SELECT 1")
    """
    settings = get_settings()
    settings.require("database_url")
    # connect_timeout: Neon may need a few seconds to wake up from sleep.
    conn = psycopg.connect(settings.database_url, connect_timeout=15)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
