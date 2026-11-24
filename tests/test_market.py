"""Analytics query logic, tested with a fake database connection."""

from datetime import date
from types import SimpleNamespace

from skillpulse.analytics import market


class FakeCursor:
    def __init__(self, rows, cols=()):
        self._rows = rows
        self.description = [SimpleNamespace(name=c) for c in cols]

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0]


class FakeConn:
    """Answers each query by the first matching keyword in `answers`."""

    def __init__(self, answers):
        self.answers = answers

    def execute(self, sql, params=None):
        for key, (rows, cols) in self.answers.items():
            if key in sql:
                return FakeCursor(rows, cols)
        raise AssertionError(f"unexpected query: {sql[:80]}")


LAST = date(2026, 11, 24)


def test_top_skills_share_uses_postings_that_list_skills():
    conn = FakeConn({
        "SELECT max(day) FROM skill_demand_daily": ([(LAST,)], ()),
        "coalesce(sum(t), 0)": ([(40,)], ()),
        "k.name AS skill, k.category": ([("SQL", "database", 10), ("Python", "language", 4)],
                                        ("skill", "category", "jobs")),
    })
    df = market.top_skills(conn, role_id=1, city="ALL", days=30)
    assert df.attrs["total"] == 40
    assert df.set_index("skill")["share"].to_dict() == {"SQL": 0.25, "Python": 0.10}


def test_trend_fills_missing_days_with_zero():
    conn = FakeConn({
        "SELECT max(day) FROM skill_demand_daily": ([(LAST,)], ()),
        "max(total_jobs) AS total": ([(date(2026, 11, 23), 20), (LAST, 10)], ("day", "total")),
        "d.job_count AS jobs": ([(date(2026, 11, 23), "SQL", 5)], ("day", "skill", "jobs")),
    })
    df = market.skill_trend(conn, 1, "ALL", ["SQL"], days=30, freq="D")
    assert df["share"].tolist() == [0.25, 0.0]   # SQL had no mentions on the 24th


def test_movers_waits_for_enough_history():
    conn = FakeConn({
        "SELECT max(day) FROM skill_demand_daily": ([(LAST,)], ()),
        "coalesce(sum(t), 0)": ([(100,)], ()),
        "count(DISTINCT day)": ([(date(2026, 11, 20), LAST, 5)], ()),
        "SELECT count(*) FROM jobs": ([(1463,)], ()),
        "max(finished_at)": ([(None,)], ()),
    })
    assert market.movers(conn, 1, "ALL") is None   # 5 days < 28 needed


def test_salary_hidden_when_too_few():
    conn = FakeConn({
        "SELECT max(day) FROM skill_demand_daily": ([(LAST,)], ()),
        "salary_min + coalesce": ([(500000,)] * 3, ()),
    })
    assert market.salary_summary(conn, 1, "ALL", 30) == {"n": 3}
