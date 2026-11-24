"""Pick a fixed random sample of jobs to hand-label for evaluation.

Run:
    python scripts/make_eval_sample.py                       # dev set: 15 jobs per role
    python scripts/make_eval_sample.py --split test --per-role 10   # held-out test set

Jobs already in the other set are excluded, so dev and test never overlap.
The job text is saved in the file because the database deletes descriptions
after 30 days, and the evaluation must be repeatable.
"""

from __future__ import annotations

import argparse
import csv
import sys

from skillpulse.db.connection import get_connection
from skillpulse.nlp.evalsets import SPLITS, sample_path
from skillpulse.nlp.extractor import job_text


def existing_ids(split: str) -> list[int]:
    path = sample_path(split)
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return [int(r["job_id"]) for r in csv.DictReader(f)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=SPLITS, default="dev")
    parser.add_argument("--per-role", type=int, default=15)
    parser.add_argument("--seed", type=float, default=0.42)
    parser.add_argument("--force", action="store_true", help="replace an existing sample")
    args = parser.parse_args()

    out = sample_path(args.split)
    if out.exists() and not args.force:
        print(f"{out} already exists (labels depend on it). Use --force to replace it.")
        return 1
    exclude = [i for s in SPLITS if s != args.split for i in existing_ids(s)]

    with get_connection() as conn:
        conn.execute("SELECT setseed(%s)", (args.seed,))   # same "random" sample every time
        rows = conn.execute(
            """
            SELECT id, role, title, description FROM (
                SELECT j.id, r.name AS role, j.title, j.description,
                       row_number() OVER (PARTITION BY j.role_id ORDER BY random()) AS n
                FROM jobs j JOIN roles r ON r.id = j.role_id
                WHERE j.description IS NOT NULL AND NOT (j.id = ANY(%s))
            ) t WHERE n <= %s ORDER BY role, id
            """,
            (exclude, args.per_role),
        ).fetchall()

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["job_id", "role", "title", "text"])
        for job_id, role, title, desc in rows:
            w.writerow([job_id, role, title, job_text(title, desc)])
    print(f"Saved {len(rows)} {args.split} jobs to {out} (excluded {len(exclude)} from other sets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
