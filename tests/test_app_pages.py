"""Smoke tests: every page of the web app renders without errors.

Uses Streamlit's AppTest with FAKE data (no database, no internet), so CI catches a broken
page before it reaches the website. The resume page is left out (it needs the language
model); its logic is tested in test_scorer / test_recommender / test_planner.
"""

import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

import data
from skillpulse.analytics.clustering import cluster_jobs
from skillpulse.analytics.market import DataStatus

TOP = pd.DataFrame({"skill": ["SQL", "Power BI", "Python", "Excel"],
                    "category": ["database", "bi_tool", "language", "office"],
                    "jobs": [30, 20, 12, 8]}).assign(share=lambda d: d.jobs / 64)


def fake_clusters(role_id):
    groups = {"java": ["Java", "Spring Boot", "Microservices"],
              "react": ["React", "JavaScript", "TypeScript"]}
    skills = [core[:2] + core[2:] * (i % 2) for core in groups.values() for i in range(25)]
    return cluster_jobs(skills, ["Developer"] * len(skills))


@pytest.fixture(autouse=True)
def fake_data(monkeypatch):
    monkeypatch.setenv("SKILLPULSE_TRACKING", "off")
    fakes = {
        "status": lambda: DataStatus(date(2026, 11, 20), date(2026, 11, 25), 6, 1976,
                                     datetime.now(UTC)),
        "roles": lambda: {"Data Analyst": 1, "Machine Learning Engineer": 3},
        "top_skills": lambda role_id, city, days, n=15: (TOP.head(n), 64),
        "salary": lambda role_id, city, days: {"n": 9, "median": 6.8, "p25": 5.4, "p75": 9.0},
        "trend": lambda role_id, city, skills, days, freq: pd.DataFrame({
            "period": pd.to_datetime(["2026-11-24", "2026-11-25"] * len(skills)),
            "skill": [s for s in skills for _ in range(2)],
            "jobs": [3, 4] * len(skills), "total": [20, 22] * len(skills),
            "share": [0.15, 0.18] * len(skills)}),
        "movers": lambda role_id, city: None,
        "cities": lambda role_id, days: pd.DataFrame({"city": ["Bengaluru", "Pune"],
                                                      "jobs": [40, 24]}),
        "trending": lambda days=7, n=8: TOP[["skill", "jobs"]],
        "clusters": fake_clusters,
    }
    for name, fn in fakes.items():
        monkeypatch.setattr(data, name, fn)


# home links to other pages, which only works inside the app's navigation: it's covered by
# test_entry_point_runs_home_with_navigation instead.
@pytest.mark.parametrize("page", ["market", "roles", "about"])
def test_page_renders_without_errors(page):
    at = AppTest.from_file(str(APP / "views" / f"{page}.py"), default_timeout=30).run()
    assert not at.exception, at.exception


def test_market_shows_numbers_from_data():
    at = AppTest.from_file(str(APP / "views" / "market.py"), default_timeout=30).run()
    page_html = " ".join(h.proto.body for h in at.get("html"))
    assert "64" in page_html and "SQL" in page_html


def test_role_explorer_shows_kinds():
    at = AppTest.from_file(str(APP / "views" / "roles.py"), default_timeout=30).run()
    page_html = " ".join(h.proto.body for h in at.get("html"))
    assert "Kind 1" in page_html and "Kind 2" in page_html


def test_entry_point_runs_home_with_navigation():
    at = AppTest.from_file(str(APP / "main.py"), default_timeout=30).run()
    assert not at.exception, at.exception


def test_database_down_shows_friendly_message(monkeypatch):
    def down():
        raise ConnectionError("db unreachable")
    monkeypatch.setattr(data, "status", down)
    at = AppTest.from_file(str(APP / "main.py"), default_timeout=30).run()
    assert not at.exception
    assert any("can't reach its database" in e.value for e in at.error)
