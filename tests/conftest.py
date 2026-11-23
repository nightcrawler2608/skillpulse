import pytest


def make_raw_job(job_id="1", title="Data Analyst", company="Acme",
                 area=("India", "Karnataka", "Bangalore"), **extra):
    """A fake job in the same shape the Adzuna API returns."""
    job = {
        "id": job_id,
        "title": title,
        "company": {"display_name": company},
        "location": {"area": list(area), "display_name": area[-1]},
        "category": {"label": "IT Jobs"},
        "description": "Looking for <strong>SQL</strong> &amp; Excel skills.",
        "created": "2026-11-20T08:30:00Z",
        "salary_min": 400000,
        "salary_max": 600000,
        "salary_is_predicted": "0",
        "redirect_url": "https://example.com/job/1",
    }
    job.update(extra)
    return job


@pytest.fixture
def raw_job():
    return make_raw_job()
