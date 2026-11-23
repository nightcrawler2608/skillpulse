"""All SQL used by the pipeline lives here, so the rest of the code stays clean."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

import psycopg

from skillpulse.config import ACTIVE_JOB_DAYS
from skillpulse.ingest.cleaner import CleanJob

INSERT_JOB_SQL = """
INSERT INTO jobs (source_job_id, dedupe_hash, title, role_id, company, city, state, category,
                  salary_min, salary_max, contract_type, contract_time, posted_at,
                  description, url)
SELECT %(source_job_id)s, %(dedupe_hash)s, %(title)s, %(role_id)s, %(company)s, %(city)s,
       %(state)s, %(category)s, %(salary_min)s, %(salary_max)s, %(contract_type)s,
       %(contract_time)s, %(posted_at)s, %(description)s, %(url)s
-- skip reposts: same title+company+city already seen in the active window
WHERE NOT EXISTS (
    SELECT 1 FROM jobs
    WHERE dedupe_hash = %(dedupe_hash)s
      AND fetched_at > now() - make_interval(days => %(active_days)s)
)
ON CONFLICT (source, source_job_id) DO NOTHING
"""


def load_role_ids(conn: psycopg.Connection) -> dict[str, int]:
    return dict(conn.execute("SELECT name, id FROM roles").fetchall())


def insert_jobs(conn: psycopg.Connection, jobs: list[CleanJob]) -> int:
    """Insert jobs, skipping duplicates. Returns how many were actually new."""
    if not jobs:
        return 0
    rows = [{**asdict(j), "active_days": ACTIVE_JOB_DAYS} for j in jobs]
    with conn.cursor() as cur:
        # executemany sends the rows in a batch (few network round trips), but the
        # statements still run one after another, so a repost later in the same
        # batch is caught by the NOT EXISTS check. rowcount = total rows inserted.
        cur.executemany(INSERT_JOB_SQL, rows)
        return max(cur.rowcount, 0)


def expire_old_jobs(conn: psycopg.Connection) -> int:
    """Mark old jobs inactive and drop their heavy columns to save space."""
    cur = conn.execute(
        """
        UPDATE jobs
        SET is_active = FALSE, description = NULL, embedding = NULL
        WHERE is_active
          AND coalesce(posted_at, fetched_at) < now() - make_interval(days => %s)
        """,
        (ACTIVE_JOB_DAYS,),
    )
    return cur.rowcount


def start_run(conn: psycopg.Connection, started_at: datetime) -> int:
    row = conn.execute(
        "INSERT INTO pipeline_runs (started_at, status) VALUES (%s, 'running') RETURNING id",
        (started_at,),
    ).fetchone()
    conn.commit()  # so the run is visible even if the pipeline crashes later
    return row[0]


def finish_run(conn: psycopg.Connection, run_id: int, **fields) -> None:
    conn.execute(
        """
        UPDATE pipeline_runs
        SET finished_at = now(), status = %(status)s, error = %(error)s,
            api_calls = %(api_calls)s, jobs_fetched = %(jobs_fetched)s,
            jobs_new = %(jobs_new)s, jobs_unmapped = %(jobs_unmapped)s
        WHERE id = %(run_id)s
        """,
        {"run_id": run_id, "error": None, **fields},
    )
    conn.commit()
