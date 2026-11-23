"""Daily job ingestion pipeline. GitHub Actions runs this every night.

Run locally:
    python pipelines/daily_ingest.py --dry-run     # fetch + clean, no database writes
    python pipelines/daily_ingest.py               # full run

Steps: fetch -> clean -> de-duplicate -> map roles -> save -> expire old jobs -> log run.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from datetime import UTC, datetime

from skillpulse.config import ROLES
from skillpulse.ingest.adzuna_client import AdzunaClient
from skillpulse.ingest.collector import collect
from skillpulse.ingest.role_mapper import RoleMapper

log = logging.getLogger("daily_ingest")


def print_summary(result, calls: int) -> None:
    print(f"\nAPI calls:        {calls}")
    print(f"Raw results:      {result.raw_count}")
    print(f"Unique jobs:      {len(result.jobs)}")
    print(f"Rejected:         {result.rejected}")
    print(f"Unmapped titles:  {result.unmapped}")
    if result.failed_queries:
        print(f"Failed queries:   {len(result.failed_queries)}")
    cities = Counter(j.city or "Unknown" for j in result.jobs)
    print("Top cities:       " + ", ".join(f"{c} ({n})" for c, n in cities.most_common(6)))


def run(dry_run: bool, max_calls: int | None) -> int:
    started = datetime.now(UTC)
    client = AdzunaClient.from_settings(**({"max_calls": max_calls} if max_calls else {}))

    if dry_run:
        # Role ids don't exist without the DB, so use positions 1..10 just for counting.
        mapper = RoleMapper(role_ids={r.name: i for i, r in enumerate(ROLES, 1)})
        result = collect(client, mapper)
        print_summary(result, client.calls_made)
        print("\nDry run: nothing written to the database.")
        return 0

    from skillpulse.db import repository as repo
    from skillpulse.db.connection import get_connection

    with get_connection() as conn:
        run_id = repo.start_run(conn, started)
        try:
            mapper = RoleMapper(role_ids=repo.load_role_ids(conn))
            result = collect(client, mapper)
            new = repo.insert_jobs(conn, result.jobs)
            expired = repo.expire_old_jobs(conn)
            conn.commit()
            # Partial success (some queries failed) still counts, but is flagged.
            status = "success" if not result.failed_queries else "partial"
            repo.finish_run(conn, run_id, status=status, api_calls=client.calls_made,
                            jobs_fetched=len(result.jobs), jobs_new=new,
                            jobs_unmapped=result.unmapped)
        except Exception as e:
            conn.rollback()
            repo.finish_run(conn, run_id, status="failed", error=str(e)[:500],
                            api_calls=client.calls_made, jobs_fetched=None,
                            jobs_new=None, jobs_unmapped=None)
            raise

    print_summary(result, client.calls_made)
    print(f"New jobs saved:   {new}")
    print(f"Expired jobs:     {expired}")
    print(f"Run status:       {status}")
    # If every query failed, make the GitHub Action go red so you notice.
    return 1 if not result.jobs else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SkillPulse daily job ingestion")
    parser.add_argument("--dry-run", action="store_true", help="don't write to the database")
    parser.add_argument("--max-calls", type=int, help="override the API call budget")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    return run(args.dry_run, args.max_calls)


if __name__ == "__main__":
    sys.exit(main())
