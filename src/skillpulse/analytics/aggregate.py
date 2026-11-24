"""Pre-compute daily skill counts into skill_demand_daily (fast dashboard).

One row = (day, role, city, skill): how many postings that day mentioned the
skill (job_count), and how many postings listed any skill at all (total_jobs).

Why "postings that list any skill" as the total: about a third of Adzuna
previews are only company description with no skills. Counting them would make
every skill look rarer than it is. We show both numbers in the app.

city = a tracked city name, or 'ALL' for every location together.
day  = the date the job was posted, in Indian time.
"""

from __future__ import annotations

import psycopg

from skillpulse.config import CITIES

ALL = "ALL"
TRACKED = [c.name for c in CITIES if c.adzuna_where]   # real cities (not "All India")

# For each job: its day, role, and city bucket(s): its own tracked city + 'ALL'.
AGG_SQL = """
WITH j AS (
    SELECT id, role_id,
           (coalesce(posted_at, fetched_at) AT TIME ZONE 'Asia/Kolkata')::date AS day,
           city
    FROM jobs
    WHERE role_id IS NOT NULL
      AND EXISTS (SELECT 1 FROM job_skills s WHERE s.job_id = jobs.id)
),
jc AS (            -- each job counted once in 'ALL' and once in its tracked city
    SELECT id, role_id, day, %(all)s AS city FROM j WHERE day >= %(since)s
    UNION ALL
    SELECT id, role_id, day, city FROM j WHERE day >= %(since)s AND city = ANY(%(tracked)s)
),
totals AS (
    SELECT day, role_id, city, count(*) AS total_jobs FROM jc GROUP BY 1, 2, 3
)
INSERT INTO skill_demand_daily (day, role_id, city, skill_id, job_count, total_jobs)
SELECT jc.day, jc.role_id, jc.city, s.skill_id, count(*), t.total_jobs
FROM jc
JOIN job_skills s ON s.job_id = jc.id
JOIN totals t USING (day, role_id, city)
GROUP BY jc.day, jc.role_id, jc.city, s.skill_id, t.total_jobs
"""


def rebuild(conn: psycopg.Connection, days: int | None = 45) -> int:
    """Recompute the last `days` days (None = everything). Safe to re-run."""
    if days is None:
        since = conn.execute(
            "SELECT coalesce(min(coalesce(posted_at, fetched_at)), now()) FROM jobs"
        ).fetchone()[0].date()
    else:
        since = conn.execute(
            "SELECT ((now() AT TIME ZONE 'Asia/Kolkata')::date - %s::int)", (days,)
        ).fetchone()[0]
    conn.execute("DELETE FROM skill_demand_daily WHERE day >= %s", (since,))
    cur = conn.execute(AGG_SQL, {"all": ALL, "since": since, "tracked": TRACKED})
    return cur.rowcount
