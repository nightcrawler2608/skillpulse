"""Compute embeddings for active jobs that don't have one yet.

Run:  python pipelines/embed_jobs.py
Needs: pip install -e ".[nlp]"
Runs nightly after skill extraction. Only new jobs are processed, so it's quick.
"""

from __future__ import annotations

import sys
import time

from skillpulse.db.connection import get_connection
from skillpulse.matching.embedder import embed, to_pgvector
from skillpulse.nlp.extractor import job_text

BATCH = 256


def main() -> int:
    t = time.time()
    done = 0
    with get_connection() as conn:
        while True:
            rows = conn.execute(
                """SELECT id, title, description FROM jobs
                   WHERE is_active AND embedding IS NULL AND description IS NOT NULL
                   ORDER BY id LIMIT %s""", (BATCH,)).fetchall()
            if not rows:
                break
            vecs = embed([job_text(title, desc) for _, title, desc in rows])
            with conn.cursor() as cur:
                cur.executemany("UPDATE jobs SET embedding = %s::vector WHERE id = %s",
                                [(to_pgvector(v), job_id) for (job_id, _, _), v in zip(rows, vecs)])
            conn.commit()
            done += len(rows)
            print(f"  embedded {done} jobs...")
    print(f"Embedded {done} jobs in {time.time() - t:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
