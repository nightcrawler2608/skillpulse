"""Re-apply the role mapper to stored jobs (after title keywords change).

New jobs are mapped when they're collected; this updates jobs already in the database,
so a keyword fix helps immediately instead of only for tomorrow's jobs. Cheap (no API
calls), safe to re-run, and also runs nightly.

    python pipelines/remap_roles.py            # apply
    python pipelines/remap_roles.py --dry-run  # only show what would change
"""

from __future__ import annotations

import argparse
from collections import Counter

from skillpulse.db import repository as repo
from skillpulse.db.connection import get_connection
from skillpulse.ingest.role_mapper import RoleMapper


def main(dry_run: bool) -> int:
    with get_connection() as conn:
        ids = repo.load_role_ids(conn)
        names = {v: k for k, v in ids.items()}
        mapper = RoleMapper(role_ids=ids)
        rows = conn.execute("SELECT id, title, role_id FROM jobs WHERE is_active").fetchall()
        changes = [(jid, mapper.role_id(title), old) for jid, title, old in rows
                   if mapper.role_id(title) != old]
        moves = Counter((names.get(old, "(unmapped)"), names.get(new, "(unmapped)"))
                        for _, new, old in changes)
        for (a, b), n in moves.most_common():
            print(f"{n:4}  {a} -> {b}")
        print(f"\n{len(changes)} of {len(rows)} active jobs change role.")
        if dry_run or not changes:
            return 0
        with conn.cursor() as cur:
            cur.executemany("UPDATE jobs SET role_id = %s WHERE id = %s",
                            [(new, jid) for jid, new, _ in changes])
        conn.commit()
        print("Saved. Re-run pipelines/aggregate.py --all to refresh the dashboard numbers.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    raise SystemExit(main(ap.parse_args().dry_run))
