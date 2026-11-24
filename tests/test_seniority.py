import pytest

from skillpulse.matching.seniority import (
    job_years,
    level_factor,
    nearest_choice,
    resume_years,
    years_in_text,
)


@pytest.mark.parametrize("text, years", [
    ("Experience: 4 to 7 years", 4),
    ("We need 3+ years of Python", 3),
    ("minimum 5 yrs in data", 5),
    ("2-4 years; 6 years preferred", 2),        # lowest stated requirement
    ("Founded 100 years ago", None),            # outside 1-20
    ("no numbers here", None),
])
def test_years_in_text(text, years):
    assert years_in_text(text) == years


@pytest.mark.parametrize("title, text, years", [
    ("Senior Data Scientist", "", 5),
    ("Sr. Software Engineer", "", 5),
    ("Lead AI Engineer", "", 8),
    ("Data Science Lead, VP", "", 8),
    ("Machine Learning Engineer III", "", 4),
    ("Software Engineer II", "", 2),
    ("Senior Data Scientist", "Requires 3+ years", 3),   # stated years beat the title
    ("Data Engineer (AWS Glue, 2-4 yrs)", "", 2),         # years in the title count
    ("Associate Business Analyst", "", 0),
    ("Senior Associate - Full stack", "", 5),             # 'Senior' wins over 'Associate'
    ("Software Developer", "Freshers can apply", 0),
    ("Data Analyst", "Work with our interns and analysts", None),  # 'interns' is not a level
    ("Data Analyst", "", None),                           # no signal -> unknown
])
def test_job_years(title, text, years):
    assert job_years(title, text) == years


def test_resume_years_reads_experience_phrases_only():
    assert resume_years("Data analyst with 1.5 years of experience") == 1.5
    assert resume_years("Data Engineer, an IT firm (3 years) - built pipelines") == 3
    assert resume_years("Analyst (18 months) - dashboards") == 1.5
    assert resume_years("Cleaned 2 years of store sales in Excel") == 0.0   # not experience
    assert resume_years("Final-year student, B.Tech 2026") == 0.0


def test_level_factor():
    assert level_factor(None, 0) == 1.0          # unknown level: no penalty
    assert level_factor(1, 0) == 1.0             # 1 year above is fine
    assert level_factor(3, 0) == pytest.approx(0.7)
    assert level_factor(8, 0) == 0.3             # floor
    assert level_factor(2, 5) == 1.0             # over-qualified: no penalty


def test_nearest_choice():
    assert nearest_choice(0.2) == "Fresher (0 years)"
    assert nearest_choice(1.5) in ("About 1 year", "About 2 years")
    assert nearest_choice(3.0) == "3-4 years"


def test_more_level_words():
    assert job_years("Machine Learning Advisor", "") == 8
    assert job_years("Machine Learning Engineer - (Founding ML Hire)", "") == 5
    assert job_years("BUSINESS ANALYST L4", "") == 5
    assert job_years("Specialist DevOps Engineer", "") == 3
    assert job_years("Data Engineer", "We are looking for an experienced Azure engineer") == 3
    assert job_years("Data Engineer", "Our experienced team builds pipelines") is None


def test_internship_title():
    from skillpulse.matching.seniority import is_internship
    assert is_internship("Full Stack Intern") and is_internship("Data Internship")
    assert not is_internship("Internal Tools Engineer")


def test_resume_years_from_date_ranges():
    from datetime import date
    today = date(2026, 11, 24)
    assert resume_years("Data Analyst, Jul 2023 - Present", today) == pytest.approx(3.4, abs=0.1)
    assert resume_years("Intern, Jun 2026 - Aug 2026", today) == pytest.approx(0.25, abs=0.06)  # 1 decimal
    assert resume_years("ML Engineer since Mar 2023", today) == pytest.approx(3.7, abs=0.1)
    assert resume_years("B.Tech, 2022 - 2026", today) == 0.0     # education years don't count
