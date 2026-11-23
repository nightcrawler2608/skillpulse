"""Create all tables and load the roles list.

Run:  python -m skillpulse.db.migrate

Safe to run many times: tables are only created if missing, and roles are
updated in place if you change them in config.py.
"""

from __future__ import annotations

from pathlib import Path

from skillpulse.config import ROLES
from skillpulse.db.connection import get_connection

SCHEMA_FILE = Path(__file__).with_name("schema.sql")


def migrate() -> None:
    with get_connection() as conn:
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO roles (name, search_term, title_keywords)
                VALUES (%s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                SET search_term = EXCLUDED.search_term,
                    title_keywords = EXCLUDED.title_keywords
                """,
                [(r.name, r.search_term, list(r.title_keywords)) for r in ROLES],
            )
        count = conn.execute("SELECT count(*) FROM roles").fetchone()[0]
    print(f"Schema ready. {count} roles in database.")


if __name__ == "__main__":
    migrate()
