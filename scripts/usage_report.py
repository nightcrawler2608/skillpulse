"""Phase 7 results: how many people used SkillPulse, what they did, and what they thought.

    python scripts/usage_report.py                    # everything recorded
    python scripts/usage_report.py --since 2026-11-26 # from launch day (skip test rows)

Reads only the anonymous usage_events and feedback tables (random per-tab ids, no personal
data) and writes reports/usage_report.md. The 👍 rate on job matches is a real-user check of
match quality, to set beside the synthetic Precision@5.
"""

from __future__ import annotations

import argparse
import math
from datetime import date

import pandas as pd

from skillpulse.config import PROJECT_ROOT
from skillpulse.db.connection import get_connection

REPORT = PROJECT_ROOT / "reports" / "usage_report.md"

EVENTS_SQL = """
SELECT e.created_at, e.session_id, e.event, r.name AS role
FROM usage_events e LEFT JOIN roles r ON r.id = e.role_id
WHERE e.created_at >= %s
"""
FEEDBACK_SQL = """
SELECT f.created_at, f.session_id, f.target, f.rating, r.name AS role
FROM feedback f LEFT JOIN roles r ON r.id = f.role_id
WHERE f.created_at >= %s
"""


def wilson(up: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a share (Wilson score): honest error bars for small n."""
    if n == 0:
        return (0.0, 0.0)
    p = up / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def table(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["_none yet_"]
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return out


def build(since: date) -> list[str]:
    with get_connection() as c:
        ev = pd.DataFrame(c.execute(EVENTS_SQL, (since,)).fetchall(),
                          columns=["at", "sid", "event", "role"])
        fb = pd.DataFrame(c.execute(FEEDBACK_SQL, (since,)).fetchall(),
                          columns=["at", "sid", "target", "rating", "role"])
    lines = [f"# SkillPulse usage report ({date.today()})", "",
             f"Data from {since} onward. Anonymous: one random id per browser tab.", ""]
    if ev.empty and fb.empty:
        return [*lines, "No usage recorded yet."]

    visitors = ev.sid.nunique()
    analysed = ev[ev.event == "analyze"]
    plans = ev[ev.event.str.startswith("plan:")]
    lines += [
        "## Headline numbers", "",
        f"- **Visitors (browser sessions):** {visitors}",
        f"- **Resumes analysed:** {len(analysed)} by {analysed.sid.nunique()} visitors",
        (f"- **Learning plans made:** {len(plans)} "
        f"({(plans.event == 'plan:gemini').sum()} worded by Gemini, "
        f"{(plans.event == 'plan:template').sum()} template)"),
        f"- **Switched to a better-fitting role:** {(ev.event == 'switch_role').sum()}",
        f"- **Feedback votes:** {len(fb)} from {fb.sid.nunique() if not fb.empty else 0} visitors",
        "",
        "## Pages viewed (once per visit)", "",
        *table(ev[ev.event.str.startswith("view:")].assign(page=lambda d: d.event.str[5:])
               .groupby("page").size().sort_values(ascending=False)
               .rename("visits").reset_index()),
        "", "## Resumes analysed, by target role", "",
        *table(analysed.groupby("role").size().sort_values(ascending=False)
               .rename("resumes").reset_index()),
    ]
    lines += ["", "## Feedback (👍 share with 95% confidence interval)", ""]
    if fb.empty:
        lines.append("_none yet_")
    else:
        rows = []
        for target, g in fb.groupby("target"):
            up, n = int((g.rating > 0).sum()), len(g)
            lo, hi = wilson(up, n)
            rows.append({"what": target, "votes": n, "👍": up,
                         "👍 share": f"{up / n:.0%}", "95% CI": f"{lo:.0%}–{hi:.0%}"})
        lines += table(pd.DataFrame(rows))
        jobs = fb[fb.target == "job"]
        if len(jobs):
            up = int((jobs.rating > 0).sum())
            lo, hi = wilson(up, len(jobs))
            lines += ["", (f"**Job matches judged good by real users: {up}/{len(jobs)} "
                          f"({up / len(jobs):.0%}, 95% CI {lo:.0%}–{hi:.0%}).** Compare with the "
                          "synthetic Precision@5 of 0.80. Users vote on jobs they choose to rate, "
                          "so this isn't the same measure, but it is real.")]
    daily = ev.assign(day=pd.to_datetime(ev["at"]).dt.date).groupby("day").sid.nunique()
    lines += ["", "## Visitors per day", "", *table(daily.rename("visitors").reset_index())]
    return lines


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=date.fromisoformat, default=date(2000, 1, 1),
                    help="first day to count, e.g. launch day (YYYY-MM-DD)")
    lines = build(ap.parse_args().since)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved {REPORT}")
