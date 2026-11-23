from conftest import make_raw_job

from skillpulse.ingest.cleaner import clean_job, clean_text, make_dedupe_hash, normalize_city


def test_clean_text_strips_html_and_spaces():
    assert clean_text("  <b>SQL</b>&amp;\n\n Python ") == "SQL & Python"
    assert clean_text("") is None
    assert clean_text(None) is None


def test_clean_job_basic_fields(raw_job):
    job = clean_job(raw_job)
    assert job.title == "Data Analyst"
    assert job.company == "Acme"
    assert job.city == "Bengaluru"          # 'Bangalore' normalised
    assert job.state == "Karnataka"
    assert job.description == "Looking for SQL & Excel skills."
    assert job.salary_min == 400000
    assert job.posted_at.year == 2026


def test_predicted_salary_is_dropped():
    job = clean_job(make_raw_job(salary_is_predicted="1"))
    assert job.salary_min is None and job.salary_max is None


def test_unusable_jobs_rejected():
    assert clean_job(make_raw_job(title="")) is None
    assert clean_job(make_raw_job(job_id=None)) is None


def test_ncr_suburbs_map_to_delhi_ncr():
    assert normalize_city(["India", "Haryana", "Gurgaon"], "Gurgaon, Haryana")[0] == "Delhi NCR"
    assert normalize_city(["India", "Uttar Pradesh", "Noida"], None)[0] == "Delhi NCR"


def test_unknown_city_keeps_most_specific_name():
    assert normalize_city(["India", "Kerala", "Kochi"], "Kochi")[0] == "Kochi"
    assert normalize_city(["India"], "India") == (None, None)


def test_state_only_location_has_no_city():
    assert normalize_city(["India", "Karnataka"], "Karnataka") == (None, "Karnataka")


def test_dedupe_hash_ignores_case_and_spacing():
    a = make_dedupe_hash("Data  Analyst", "ACME", "Pune")
    b = make_dedupe_hash("data analyst", "acme", "pune")
    assert a == b
    assert a != make_dedupe_hash("Data Analyst", "Acme", "Mumbai")
