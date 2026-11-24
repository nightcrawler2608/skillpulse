"""Pick a fixed random sample of jobs to hand-label for evaluation.

Run once:  python scripts/make_eval_sample.py
Creates data/eval/sample_jobs.csv: 15 jobs per role (150 total), chosen at random
with a fixed seed. The job text is saved in the file because the database deletes
descriptions after 30 days, and the evaluation must be repeatable.
"""

from __future__ import annotations

import csv
import sys

from skillpulse.config import PROJECT_ROOT
from skillpulse.db.connection import get_connection
from skillpulse.nlp.extractor import job_text

OUT = PROJECT_ROOT / "data" / "eval" / "sample_jobs.csv"
PER_ROLE = 15


def main() -> int:
    if OUT.exists() and "--force" not in sys.argv:
        print(f"{OUT} already exists (labels depend on it). Use --force to replace it.")
        return 1
    with get_connection() as conn:
        conn.execute("SELECT setseed(0.42)")   # same "random" sample every time
        rows = conn.execute(
            """
            SELECT id, role, title, description FROM (
                SELECT j.id, r.name AS role, j.title, j.description,
                       row_number() OVER (PARTITION BY j.role_id ORDER BY random()) AS n
                FROM jobs j JOIN roles r ON r.id = j.role_id
                WHERE j.description IS NOT NULL
            ) t WHERE n <= %s ORDER BY role, id
            """,
            (PER_ROLE,),
        ).fetchall()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["job_id", "role", "title", "text"])
        for job_id, role, title, desc in rows:
            w.writerow([job_id, role, title, job_text(title, desc)])
    print(f"Saved {len(rows)} jobs to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
