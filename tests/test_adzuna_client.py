import pytest

from skillpulse.ingest.adzuna_client import AdzunaClient, AdzunaError, BudgetExceeded


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeSession:
    """Returns the given responses in order and records the params sent."""
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return self.responses.pop(0)


def make_client(*responses, max_calls=10):
    return AdzunaClient("my-id", "SECRET-KEY", max_calls=max_calls,
                        backoff_seconds=0, min_interval=0, session=FakeSession(*responses))


def test_returns_results_and_counts_calls():
    c = make_client(FakeResponse(200, {"results": [{"id": "1"}]}))
    assert c.search("data analyst", "Pune") == [{"id": "1"}]
    assert c.calls_made == 1
    url, params = c.session.calls[0]
    assert "/jobs/in/search/1" in url
    assert params["where"] == "Pune"


def test_no_where_param_for_all_india():
    c = make_client(FakeResponse(200, {"results": []}))
    c.search("data analyst", None)
    assert "where" not in c.session.calls[0][1]


def test_retries_when_rate_limited():
    c = make_client(FakeResponse(429), FakeResponse(200, {"results": [{"id": "2"}]}))
    assert c.search("x") == [{"id": "2"}]
    assert c.calls_made == 2


def test_gives_up_on_client_error_without_leaking_key():
    c = make_client(FakeResponse(401))
    with pytest.raises(AdzunaError) as e:
        c.search("x")
    assert "SECRET-KEY" not in str(e.value)


def test_budget_is_enforced():
    c = make_client(FakeResponse(200), max_calls=1)
    c.search("x")
    with pytest.raises(BudgetExceeded):
        c.search("x")
