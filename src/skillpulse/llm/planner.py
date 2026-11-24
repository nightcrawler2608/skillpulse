"""Week-by-week learning plan for the skills a resume is missing.

Who decides what (so the AI can't go off the rails):
1. OUR CODE picks the skills and the schedule: missing skills in order of how many
   score points they add, each given 1 or 2 weeks depending on how big it is, until
   the chosen number of weeks is full. Data, not the AI, decides what to learn.
2. GEMINI only writes the words for that fixed schedule: a goal, 3 tasks and a mini
   project per week, tailored to the role and the skills the person already has.
   Its answer must be valid JSON matching our schema, or it's thrown away.
3. If Gemini is switched off, has no key, hits its quota, times out or returns
   something invalid, a TEMPLATE writes the same plan. The app always works.
4. LINKS come from data/skills/resources.csv (checked by hand), never from the AI,
   because language models invent URLs.

Privacy: only skill names, the role, experience level and hours per week are sent to
Google. Never resume text, names or contact details.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import time
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import quote_plus

import requests

from skillpulse.config import PROJECT_ROOT, get_settings
from skillpulse.nlp.taxonomy import default_skills

log = logging.getLogger(__name__)

RESOURCES_CSV = PROJECT_ROOT / "data" / "skills" / "resources.csv"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = 25

# Big skills (a language, a framework, a cloud, ML) take 2 weeks at ~6-8 hours a week;
# tools and concepts take 1.
BIG_CATEGORIES = {"language", "web_frontend", "web_backend", "ml", "genai", "cloud",
                  "data_engineering", "data_science", "devops", "mobile", "data_platform"}
SMALL_SKILLS = {"Git", "GitHub", "Jira", "Confluence", "Postman", "Bootstrap", "jQuery",
                "Pivot Tables", "VLOOKUP", "REST APIs", "Agile", "Scrum", "Matplotlib",
                "Seaborn", "Linux", "CI/CD", "ETL"}
SKIP_CATEGORIES = {"soft"}          # "Teamwork" isn't something to schedule study weeks for


@dataclass
class PlanWeek:
    weeks: list[int]                 # e.g. [3, 4] for a 2-week skill
    skill: str
    goal: str = ""
    tasks: list[str] = field(default_factory=list)
    project: str = ""
    link: str = ""
    link_label: str = ""


@dataclass
class LearningPlan:
    items: list[PlanWeek]
    source: str                      # "gemini" or "template"
    note: str = ""                   # why the template was used, if it was
    skipped: list[str] = field(default_factory=list)   # missing skills that didn't fit


# --------------------------------------------------------------------------- schedule
@lru_cache(maxsize=1)
def _categories() -> dict[str, str]:
    return {s.name: s.category for s in default_skills()}


def weeks_needed(skill: str, hours_per_week: int) -> int:
    big = _categories().get(skill) in BIG_CATEGORIES and skill not in SMALL_SKILLS
    if not big:
        return 1
    return 1 if hours_per_week >= 12 else 2


def schedule(missing: list[str], total_weeks: int, hours_per_week: int
             ) -> tuple[list[PlanWeek], list[str]]:
    """Fill the weeks with missing skills in the given order (most valuable first)."""
    items, week, skipped = [], 1, []
    for skill in missing:
        if _categories().get(skill) in SKIP_CATEGORIES:
            continue
        n = weeks_needed(skill, hours_per_week)
        if week + n - 1 > total_weeks:
            skipped.append(skill)
            continue
        items.append(PlanWeek(list(range(week, week + n)), skill))
        week += n
    return items, skipped


# --------------------------------------------------------------------------- links
@lru_cache(maxsize=1)
def _resources() -> dict[str, tuple[str, str]]:
    with open(RESOURCES_CSV, encoding="utf-8") as f:
        return {r["skill"]: (r["url"], r["label"]) for r in csv.DictReader(f)}


def resource_for(skill: str) -> tuple[str, str]:
    if skill in _resources():
        return _resources()[skill]
    # No hand-checked link: a YouTube search is always valid and free.
    return (f"https://www.youtube.com/results?search_query={quote_plus(skill + ' tutorial')}",
            f"Free {skill} tutorials (YouTube search)")


# --------------------------------------------------------------------------- template
# Short noun phrases so they read well in every template sentence.
ROLE_PROJECTS = {
    "Data Analyst": "a public-data dashboard project (e.g. data.gov.in)",
    "Data Scientist": "a Kaggle prediction project",
    "Machine Learning Engineer": "a small model-serving API project",
    "Data Engineer": "a daily data-pipeline project",
    "Business Analyst": "a requirements project for an app you use",
    "Software Engineer": "a small tested tool on GitHub",
    "Frontend Developer": "a responsive web app that calls a public API",
    "Backend Developer": "a REST API project with a database",
    "Full Stack Developer": "a small full-stack app",
    "DevOps / Cloud Engineer": "a CI/CD pipeline project",
}


# (goal, hands-on practice, mini project) by kind of skill. {s} = skill, {p} = role project.
CATEGORY_TEXT = {
    "code": ("Write working {s} code on your own, not just follow along.",
             "Solve 10-15 small {s} exercises; push your solutions to a GitHub repo.",
             "Build {p} using {s}, with a short README explaining what it does."),
    "data": ("Understand {s} well enough to explain it and apply it once.",
             "Apply {s} step by step on a small public example; keep notes as you go.",
             "Use {s} in {p} and write 3 lines on what it changed."),
    "viz": ("Present data with {s} so someone else understands it at a glance.",
            "Rebuild 2 charts you like from news or reports, using {s}.",
            "Make a one-page report with {s} as part of {p}; share a screenshot on LinkedIn."),
    "platform": ("Set up {s} on a free tier and run one thing end to end.",
                 "Follow the free getting-started path; note every command or setting you use.",
                 "Deploy or run part of {p} on {s}, then shut it down to stay at ₹0."),
    "process": ("Understand how {s} is used day to day in {r} teams.",
                "Read the free guide and write a one-page summary in your own words.",
                "Apply {s} to {p}: write the document or board a real team would use."),
}
CATEGORY_GROUP = {
    "language": "code", "web_frontend": "code", "web_backend": "code", "mobile": "code",
    "python_lib": "code", "cs_fundamentals": "code", "testing": "code", "database": "data",
    "data_science": "data", "analytics": "data", "ml": "data", "genai": "code",
    "data_tool": "data", "office": "viz", "bi_tool": "viz", "design": "viz",
    "cloud": "platform", "devops": "platform", "data_platform": "platform",
    "data_engineering": "platform", "security": "platform",
    "process": "process", "business": "process",
}


# Concepts that sit in tool-heavy categories but aren't something you "set up".
GROUP_OVERRIDES = {
    **dict.fromkeys(["ETL", "Data Pipelines", "Data Warehousing", "Data Lake", "Data Modeling",
                     "Data Governance", "Data Quality", "Big Data", "CI/CD",
                     "Infrastructure as Code", "Monitoring & Observability",
                     "Computer Networking", "Cloud Computing", "Serverless"], "data"),
    **dict.fromkeys(["Dashboarding", "Data Visualization", "MIS Reporting", "KPI Tracking"],
                    "viz"),
}


def template_text(item: PlanWeek, role: str) -> None:
    s, span = item.skill, ("these two weeks" if len(item.weeks) > 1 else "this week")
    group = GROUP_OVERRIDES.get(s) or CATEGORY_GROUP.get(_categories().get(s, ""), "data")
    goal, practice, project = CATEGORY_TEXT[group]
    fill = {"s": s, "r": role, "p": ROLE_PROJECTS.get(role, "a small portfolio project")}
    item.goal = goal.format(**fill)
    item.tasks = [
        f"Work through the beginner part of the free resource below ({span}).",
        practice.format(**fill),
        f"Read 2 live {role} postings that ask for {s}: note what they expect you to do with it.",
    ]
    item.project = project.format(**fill)


# --------------------------------------------------------------------------- gemini
RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "skill": {"type": "STRING"},
            "goal": {"type": "STRING"},
            "tasks": {"type": "ARRAY", "items": {"type": "STRING"}},
            "project": {"type": "STRING"},
        },
        "required": ["skill", "goal", "tasks", "project"],
    },
}


def build_prompt(items: list[PlanWeek], role: str, have: list[str], years: float,
                 hours_per_week: int) -> str:
    level = "a fresher (no full-time experience)" if years < 1 else f"about {years:g} years in"
    lines = "\n".join(f"- weeks {'-'.join(map(str, it.weeks))}: {it.skill}" for it in items)
    return (
        f"You are a practical career mentor in India. Write a study plan for someone "
        f"targeting {role} jobs. They are {level} and can study {hours_per_week} hours a week.\n"
        f"Skills they already have: {', '.join(have[:25]) or 'none listed'}.\n\n"
        f"The schedule is FIXED; do not add, remove or reorder skills:\n{lines}\n\n"
        "For EACH skill, in the same order, return: goal (one sentence), tasks (exactly 3 "
        "short, concrete steps using free material only), project (one sentence: a small "
        "portfolio project that combines this skill with skills they already have and suits "
        f"{role} work). Fit the effort to the hours. No URLs, no course names that cost "
        "money, no motivational filler. Reply only with the JSON array."
    )


class PlanError(RuntimeError):
    pass


def llm_enabled() -> bool:
    return (os.getenv("SKILLPULSE_LLM", "on").lower() not in ("off", "0", "false")
            and bool(get_settings().gemini_api_key))


# "-latest" aliases follow Google's current models, so a retired model name can't break the
# app (gemini-2.5-flash was retired for new keys). Lite first: short plan text doesn't need
# the bigger model, it's faster, and it stayed available when Flash returned "high demand".
DEFAULT_MODELS = ("gemini-flash-lite-latest", "gemini-flash-latest")
RETRY_NEXT_MODEL = {404, 429, 500, 503}


def models_to_try() -> tuple[str, ...]:
    chosen = os.getenv("GEMINI_MODEL")
    return (chosen, *[m for m in DEFAULT_MODELS if m != chosen]) if chosen else DEFAULT_MODELS


def call_gemini(prompt: str) -> list[dict]:
    key = get_settings().gemini_api_key
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "responseSchema": RESPONSE_SCHEMA, "temperature": 0.4},
    }
    status = None
    attempts = [(m, n) for m in models_to_try() for n in range(2)]   # each model twice
    for model, n in attempts:
        if n:
            time.sleep(1.5)          # "high demand" 503s are usually brief
        r = requests.post(GEMINI_URL.format(model=model), json=body, timeout=TIMEOUT,
                          headers={"x-goog-api-key": key})
        status = r.status_code
        if status == 200:
            break
        if status not in RETRY_NEXT_MODEL:
            raise PlanError(f"Gemini HTTP {status}")
        log.info("Gemini model %s returned %s (attempt %d)", model, status, n + 1)
    else:
        raise PlanError(f"Gemini HTTP {status} (all models)")
    try:
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except (KeyError, IndexError, ValueError) as e:
        raise PlanError("Gemini returned an unexpected format") from e


def apply_llm_text(items: list[PlanWeek], answer: list[dict]) -> None:
    """Validate the AI's answer against our schedule; raise PlanError if it doesn't fit."""
    if not isinstance(answer, list) or len(answer) != len(items):
        raise PlanError("Gemini changed the number of skills")
    for item, a in zip(items, answer, strict=True):
        if str(a.get("skill", "")).strip().lower() != item.skill.lower():
            raise PlanError("Gemini changed the schedule")
        tasks = [str(t).strip() for t in a.get("tasks", []) if str(t).strip()]
        goal, project = str(a.get("goal", "")).strip(), str(a.get("project", "")).strip()
        if len(tasks) < 2 or not goal or not project:
            raise PlanError("Gemini left parts of the plan empty")
        if any("http" in x.lower() for x in [goal, project, *tasks]):
            raise PlanError("Gemini added links")   # we only show our checked links
        item.goal, item.tasks, item.project = goal, tasks[:4], project


# --------------------------------------------------------------------------- main
def make_plan(missing: list[str], role: str, have: list[str], years: float = 0.0,
              total_weeks: int = 8, hours_per_week: int = 8, use_llm: bool | None = None
              ) -> LearningPlan:
    items, skipped = schedule(missing, total_weeks, hours_per_week)
    for it in items:
        it.link, it.link_label = resource_for(it.skill)
    if not items:
        return LearningPlan([], "template", "No missing skills to plan for.", skipped)

    use_llm = llm_enabled() if use_llm is None else use_llm
    note = "" if use_llm else "AI writing is switched off, so a standard template was used."
    if use_llm:
        try:
            apply_llm_text(items, call_gemini(build_prompt(items, role, have, years,
                                                           hours_per_week)))
            return LearningPlan(items, "gemini", "", skipped)
        except (PlanError, requests.RequestException) as e:
            log.warning("learning plan: falling back to template (%s)", e)
            note = "The AI writer wasn't available just now, so a standard template was used."
    for it in items:
        template_text(it, role)
    return LearningPlan(items, "template", note, skipped)
