import csv

import pytest

from skillpulse.llm import planner
from skillpulse.llm.planner import (
    RESOURCES_CSV,
    PlanError,
    PlanWeek,
    apply_llm_text,
    make_plan,
    resource_for,
    schedule,
)
from skillpulse.nlp.taxonomy import default_skills

MISSING = ["Power BI", "Teamwork", "Python", "Tableau", "Statistics", "AWS"]


def test_schedule_orders_by_value_sizes_skills_and_skips_soft_skills():
    items, skipped = schedule(MISSING, total_weeks=6, hours_per_week=8)
    assert [(i.skill, i.weeks) for i in items] == [
        ("Power BI", [1]), ("Python", [2, 3]), ("Tableau", [4]), ("Statistics", [5, 6])]
    assert skipped == ["AWS"]                     # didn't fit; Teamwork isn't scheduled


def test_more_hours_means_big_skills_take_one_week():
    items, _ = schedule(["Python", "AWS"], total_weeks=4, hours_per_week=12)
    assert [i.weeks for i in items] == [[1], [2]]


def test_links_are_checked_list_or_youtube_search():
    assert resource_for("Python")[0].startswith("https://docs.python.org")
    url, label = resource_for("Looker")
    assert url.startswith("https://www.youtube.com/results?search_query=Looker")
    assert "YouTube" in label


def test_every_resource_skill_exists_in_dictionary():
    names = {s.name for s in default_skills()}
    with open(RESOURCES_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows and all(r["skill"] in names and r["url"].startswith("https://") for r in rows)


def test_template_plan_when_llm_off():
    plan = make_plan(MISSING, "Data Analyst", ["SQL"], total_weeks=6, use_llm=False)
    assert plan.source == "template" and "switched off" in plan.note
    assert all(i.goal and len(i.tasks) == 3 and i.project and i.link for i in plan.items)


def _answer(items, **overrides):
    out = [{"skill": i.skill, "goal": "g", "tasks": ["a", "b", "c"], "project": "p"}
           for i in items]
    out[0].update(overrides)
    return out


def test_valid_llm_answer_is_applied():
    items = [PlanWeek([1], "Power BI"), PlanWeek([2, 3], "Python")]
    apply_llm_text(items, _answer(items, goal="Build one dashboard"))
    assert items[0].goal == "Build one dashboard" and items[1].tasks == ["a", "b", "c"]


@pytest.mark.parametrize("bad", [
    lambda items: _answer(items)[:1],                           # dropped a skill
    lambda items: _answer(items, skill="Excel"),                # changed the schedule
    lambda items: _answer(items, tasks=[]),                     # empty parts
    lambda items: _answer(items, project="see https://x.io"),   # invented link
])
def test_invalid_llm_answers_are_rejected(bad):
    items = [PlanWeek([1], "Power BI"), PlanWeek([2], "Tableau")]
    with pytest.raises(PlanError):
        apply_llm_text(items, bad(items))


def test_gemini_failure_falls_back_to_template(monkeypatch):
    def boom(prompt):
        raise PlanError("Gemini HTTP 503 (all models)")
    monkeypatch.setattr(planner, "call_gemini", boom)
    plan = make_plan(MISSING, "Data Analyst", [], total_weeks=4, use_llm=True)
    assert plan.source == "template" and "wasn't available" in plan.note and plan.items


def test_gemini_success_is_used(monkeypatch):
    monkeypatch.setattr(planner, "call_gemini",
                        lambda prompt: [{"skill": s, "goal": "G", "tasks": ["x", "y", "z"],
                                         "project": "P"} for s in ("Power BI", "Python")])
    plan = make_plan(["Power BI", "Python"], "Data Analyst", [], total_weeks=4, use_llm=True)
    assert plan.source == "gemini" and plan.items[0].goal == "G"


def test_prompt_contains_no_resume_text():
    items, _ = schedule(["Power BI"], 4, 8)
    prompt = planner.build_prompt(items, "Data Analyst", ["SQL"], 0, 8)
    assert "SQL" in prompt and "Power BI" in prompt and "resume" not in prompt.lower()


def test_llm_switch_off(monkeypatch):
    monkeypatch.setenv("SKILLPULSE_LLM", "off")
    assert planner.llm_enabled() is False
