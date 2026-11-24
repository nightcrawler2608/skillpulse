"""Rebuild the daily skill-demand table used by the dashboard.

Run:  python pipelines/aggregate.py          # last 45 days (nightly)
      python pipelines/aggregate.py --all    # everything (first time / after big changes)
"""

from __future__ import annotations

import argparse
import sys
import time

from skillpulse.analytics.aggregate import rebuild
from skillpulse.db.connection import get_connection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    t = time.time()
    with get_connection() as conn:
        n = rebuild(conn, days=None if args.all else 45)
    print(f"skill_demand_daily: {n} rows written in {time.time() - t:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
