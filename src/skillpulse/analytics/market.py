"""Read-only queries behind the market dashboard. All return pandas DataFrames.

Every number comes with its sample size, so the app can warn when it is small.
Time windows are measured back from the LATEST day we have data for (not from
today), so the dashboard never looks empty just because tonight's run hasn't
happened yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import psycopg

ALL = "ALL"
MIN_JOBS = 20            # below this, shares are shown with a "small sample" warning
MIN_SALARIES = 8         # below this, we don't show a salary figure at all
MOVER_WINDOW = 14        # rising/falling compares the last 14 days vs the 14 before
MIN_MOVER_JOBS = 30      # each window needs at least this many postings


def _df(conn: psycopg.Connection, sql: str, params) -> pd.DataFrame:
    cur = conn.execute(sql, params)
    cols = [d.name for d in cur.description]
    return pd.DataFrame(cur.fetchall(), columns=cols)


@dataclass
class DataStatus:
    first_day: date | None
    last_day: date | None
    days: int
    total_jobs: int
    last_run: object | None     # timestamp of the last successful pipeline run


def data_status(conn) -> DataStatus:
    first, last, n_days = conn.execute(
        "SELECT min(day), max(day), count(DISTINCT day) FROM skill_demand_daily"
    ).fetchone()
    total = conn.execute("SELECT count(*) FROM jobs").fetchone()[0]
    run = conn.execute("SELECT max(finished_at) FROM pipeline_runs WHERE status IN "
                       "('success','partial')").fetchone()[0]
    return DataStatus(first, last, n_days or 0, total, run)


def roles(conn) -> list[tuple[int, str]]:
    return conn.execute("SELECT id, name FROM roles ORDER BY name").fetchall()


def _window(conn, days: int, offset: int = 0) -> tuple[date, date]:
    last = conn.execute("SELECT max(day) FROM skill_demand_daily").fetchone()[0] or date.today()
    end = last - timedelta(days=offset)
    return end - timedelta(days=days - 1), end


def postings_in_window(conn, role_id: int, city: str, days: int, offset: int = 0) -> int:
    """Postings that list at least one skill, for this role/city/window."""
    start, end = _window(conn, days, offset)
    row = conn.execute(
        """SELECT coalesce(sum(t), 0) FROM (
               SELECT day, max(total_jobs) t FROM skill_demand_daily
               WHERE role_id = %s AND city = %s AND day BETWEEN %s AND %s GROUP BY day) x""",
        (role_id, city, start, end),
    ).fetchone()
    return int(row[0])


def top_skills(conn, role_id: int, city: str, days: int, n: int = 15) -> pd.DataFrame:
    """skill, category, jobs (postings mentioning it), share (0-1 of postings listing skills)."""
    start, end = _window(conn, days)
    total = postings_in_window(conn, role_id, city, days)
    df = _df(conn, """
        SELECT k.name AS skill, k.category, sum(d.job_count)::int AS jobs
        FROM skill_demand_daily d JOIN skills k ON k.id = d.skill_id
        WHERE d.role_id = %s AND d.city = %s AND d.day BETWEEN %s AND %s
        GROUP BY k.name, k.category ORDER BY jobs DESC, skill LIMIT %s""",
        (role_id, city, start, end, n))
    df["share"] = df["jobs"] / total if total else 0.0
    df.attrs["total"] = total
    return df


def skill_trend(conn, role_id: int, city: str, skills: list[str], days: int,
                freq: str = "D") -> pd.DataFrame:
    """Share of postings mentioning each skill per day ('D') or week ('W')."""
    start, end = _window(conn, days)
    totals = _df(conn, """
        SELECT day, max(total_jobs) AS total FROM skill_demand_daily
        WHERE role_id = %s AND city = %s AND day BETWEEN %s AND %s GROUP BY day""",
        (role_id, city, start, end))
    counts = _df(conn, """
        SELECT d.day, k.name AS skill, d.job_count AS jobs
        FROM skill_demand_daily d JOIN skills k ON k.id = d.skill_id
        WHERE d.role_id = %s AND d.city = %s AND d.day BETWEEN %s AND %s
          AND k.name = ANY(%s)""",
        (role_id, city, start, end, skills))
    if totals.empty:
        return pd.DataFrame(columns=["period", "skill", "jobs", "total", "share"])
    totals["period"] = pd.to_datetime(totals["day"]).dt.to_period(freq).dt.start_time
    counts["period"] = pd.to_datetime(counts["day"]).dt.to_period(freq).dt.start_time
    t = totals.groupby("period", as_index=False)["total"].sum()
    grid = t.merge(pd.DataFrame({"skill": skills}), how="cross")   # zero-fill missing days
    c = counts.groupby(["period", "skill"], as_index=False)["jobs"].sum()
    out = grid.merge(c, on=["period", "skill"], how="left").fillna({"jobs": 0})
    out["share"] = out["jobs"] / out["total"]
    return out.sort_values(["skill", "period"])


def movers(conn, role_id: int, city: str, n: int = 5) -> pd.DataFrame | None:
    """Skills whose share changed most: last 14 days vs the 14 before.
    Returns None when there isn't enough history or data to say anything honest."""
    cur_total = postings_in_window(conn, role_id, city, MOVER_WINDOW)
    prev_total = postings_in_window(conn, role_id, city, MOVER_WINDOW, offset=MOVER_WINDOW)
    status = data_status(conn)
    if status.days < 2 * MOVER_WINDOW or min(cur_total, prev_total) < MIN_MOVER_JOBS:
        return None
    cur = top_skills(conn, role_id, city, MOVER_WINDOW, n=200).set_index("skill")["share"]
    s, e = _window(conn, MOVER_WINDOW, offset=MOVER_WINDOW)
    prev = _df(conn, """
        SELECT k.name AS skill, sum(d.job_count)::float / %s AS share
        FROM skill_demand_daily d JOIN skills k ON k.id = d.skill_id
        WHERE d.role_id = %s AND d.city = %s AND d.day BETWEEN %s AND %s GROUP BY k.name""",
        (prev_total, role_id, city, s, e)).set_index("skill")["share"]
    both = pd.concat({"now": cur, "before": prev}, axis=1).fillna(0)
    both["change_pts"] = (both["now"] - both["before"]) * 100
    both = both[(both["now"] > 0.05) | (both["before"] > 0.05)]   # ignore tiny skills
    return both.sort_values("change_pts").reset_index().rename(columns={"index": "skill"})


def salary_summary(conn, role_id: int, city: str, days: int) -> dict:
    """Median and middle-50% range (in lakhs per year) of ADVERTISED salaries."""
    start, end = _window(conn, days)
    where_city = "" if city == ALL else "AND j.city = %(city)s"
    rows = conn.execute(f"""
        SELECT (salary_min + coalesce(salary_max, salary_min)) / 2 / 100000.0
        FROM jobs j
        WHERE role_id = %(role)s AND salary_min IS NOT NULL {where_city}
          AND (coalesce(posted_at, fetched_at) AT TIME ZONE 'Asia/Kolkata')::date
              BETWEEN %(start)s AND %(end)s""",
        {"role": role_id, "city": city, "start": start, "end": end}).fetchall()
    vals = pd.Series([float(r[0]) for r in rows])
    if len(vals) < MIN_SALARIES:
        return {"n": len(vals)}
    return {"n": len(vals), "median": vals.median(),
            "p25": vals.quantile(0.25), "p75": vals.quantile(0.75)}


def trending_overall(conn, days: int = 7, n: int = 8) -> pd.DataFrame:
    """Most-mentioned skills across all roles, India-wide (for the home ribbon)."""
    start, end = _window(conn, days)
    return _df(conn, """
        SELECT k.name AS skill, sum(d.job_count)::int AS jobs
        FROM skill_demand_daily d JOIN skills k ON k.id = d.skill_id
        WHERE d.city = %s AND d.day BETWEEN %s AND %s
        GROUP BY k.name ORDER BY jobs DESC LIMIT %s""", (ALL, start, end, n))


def city_counts(conn, role_id: int, days: int) -> pd.DataFrame:
    start, end = _window(conn, days)
    return _df(conn, """
        SELECT city, sum(t)::int AS jobs FROM (
            SELECT day, city, max(total_jobs) t FROM skill_demand_daily
            WHERE role_id = %s AND city <> %s AND day BETWEEN %s AND %s GROUP BY day, city) x
        GROUP BY city ORDER BY jobs DESC""", (role_id, ALL, start, end))
