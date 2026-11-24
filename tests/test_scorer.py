import pandas as pd
import pytest

from skillpulse.matching.resume_parser import ResumeError, clean_text, pdf_to_text
from skillpulse.matching.scorer import score_resume

DEMAND = pd.DataFrame({"skill": ["SQL", "Excel", "Tableau"], "share": [0.5, 0.3, 0.2]})


def test_score_example_from_docstring():
    r = score_resume({"SQL", "Microsoft Excel", "Excel"}, DEMAND)
    assert r.score == 80.0
    assert [g.skill for g in r.missing] == ["Tableau"]
    assert r.missing[0].gain == pytest.approx(20.0)
    assert r.extra == ["Microsoft Excel"]       # skills not in the top list


def test_score_bounds():
    assert score_resume(set(), DEMAND).score == 0
    assert score_resume({"SQL", "Excel", "Tableau"}, DEMAND).score == 100


def test_missing_ranked_by_demand():
    r = score_resume({"Tableau"}, DEMAND)
    assert [g.skill for g in r.missing] == ["SQL", "Excel"]


def test_empty_demand_is_safe():
    r = score_resume({"SQL"}, pd.DataFrame({"skill": [], "share": []}))
    assert r.score == 0 and r.extra == ["SQL"]


def test_resume_rules_ai_and_implications():
    from skillpulse.matching.resume_skills import resume_skills
    from skillpulse.nlp.extractor import DictionaryExtractor
    ex = DictionaryExtractor()
    s = resume_skills("Built LLM apps with LangChain on AWS", ex)
    assert {"Artificial Intelligence", "Cloud Computing", "Large Language Models"} <= s
    assert "Artificial Intelligence" in resume_skills("M.Tech in AI", ex)
    assert "Artificial Intelligence" not in resume_skills("Excel and SQL reporting", ex)


def test_mojibake_repair():
    from skillpulse.ingest.cleaner import clean_text as clean_job_text
    assert clean_job_text("Power BI Developer(12 PM â 9 PM)") == "Power BI Developer(12 PM – 9 PM)"
    assert clean_job_text("CafÃ© analyst") == "Café analyst"


def test_clean_text_squeezes_blank_lines():
    assert clean_text("SQL  \n\n\n  Python") == "SQL\nPython"


def test_rejects_non_pdf():
    with pytest.raises(ResumeError):
        pdf_to_text(b"hello, not a pdf")
