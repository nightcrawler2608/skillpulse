from conftest import make_raw_job

from skillpulse.config import ADZUNA_RESULTS_PER_PAGE, CITIES, ROLES, planned_queries
from skillpulse.ingest.adzuna_client import BudgetExceeded
from skillpulse.ingest.collector import collect
from skillpulse.ingest.role_mapper import RoleMapper

N_QUERIES = len(planned_queries())   # main (role x city) + extra terms
MAPPER = RoleMapper(role_ids={r.name: i for i, r in enumerate(ROLES, 1)})


class FakeClient:
    def __init__(self, pages, budget=10_000):
        self.pages = pages          # function (what, where, page) -> list of raw jobs
        self.budget = budget
        self.calls = 0

    def search(self, what, where=None, page=1):
        if self.calls >= self.budget:
            raise BudgetExceeded("done")
        self.calls += 1
        return self.pages(what, where, page)


def test_same_job_from_different_queries_counted_once():
    # Every query returns the same single job.
    client = FakeClient(lambda *_: [make_raw_job(job_id="same")])
    result = collect(client, MAPPER)
    assert len(result.jobs) == 1
    assert result.raw_count == N_QUERIES


def test_short_page_skips_next_page():
    client = FakeClient(lambda *_: [])
    collect(client, MAPPER)
    assert client.calls == N_QUERIES   # only page 1 each


def test_full_page_fetches_page_two():
    def pages(what, where, page):
        n = ADZUNA_RESULTS_PER_PAGE if page == 1 else 3
        return [make_raw_job(job_id=f"{what}-{where}-{page}-{i}") for i in range(n)]
    client = FakeClient(pages)
    result = collect(client, MAPPER)
    assert client.calls == N_QUERIES * 2
    assert len(result.jobs) == N_QUERIES * (ADZUNA_RESULTS_PER_PAGE + 3)


def test_unmapped_and_rejected_are_counted():
    client = FakeClient(lambda what, where, page: [
        make_raw_job(job_id=f"{what}{where}a", title="Accountant"),
        make_raw_job(job_id=f"{what}{where}b", title=""),
    ])
    result = collect(client, MAPPER)
    assert result.unmapped == len(result.jobs)
    assert result.rejected == N_QUERIES


def test_budget_stops_run_but_keeps_jobs():
    client = FakeClient(lambda what, where, page: [make_raw_job(job_id=f"{what}{where}")],
                        budget=5)
    result = collect(client, MAPPER)
    assert len(result.jobs) == 5


def test_one_failing_query_does_not_stop_run():
    def pages(what, where, page):
        if what == ROLES[0].search_term and where == CITIES[0].adzuna_where:
            raise RuntimeError("boom")
        return [make_raw_job(job_id=f"{what}{where}")]
    result = collect(FakeClient(pages), MAPPER)
    assert len(result.failed_queries) == 1
    assert len(result.jobs) == N_QUERIES - 1


def test_extra_terms_run_after_main_searches_and_all_india_only():
    queries = planned_queries()
    main = len(ROLES) * len(CITIES)
    assert all(city.adzuna_where is None for _, city in queries[main:])
    assert {t for t, _ in queries[main:]} == {t for r in ROLES for t in r.extra_terms}


def test_budget_cut_drops_extras_not_main_searches():
    client = FakeClient(lambda *_: [], budget=len(ROLES) * len(CITIES))
    collect(client, MAPPER)
    assert client.calls == len(ROLES) * len(CITIES)   # every main search still ran
