"""Talks to the Adzuna job search API.

Two safety features:
- Call budget: the client refuses to make more calls than we allow per run,
  so we can never blow through the free quota by accident.
- Retries: if Adzuna is busy (HTTP 429) or has a temporary error (5xx), we
  wait a little and try again, waiting longer each time ("exponential backoff").
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests

from skillpulse.config import (
    ADZUNA_COUNTRY,
    ADZUNA_MAX_CALLS_PER_DAY,
    ADZUNA_RESULTS_PER_PAGE,
    get_settings,
)

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
RETRY_STATUS = {429, 500, 502, 503, 504}


class BudgetExceeded(RuntimeError):
    """Raised when a run tries to use more API calls than allowed."""


class AdzunaError(RuntimeError):
    """Raised when Adzuna returns an error we can't recover from."""


@dataclass
class AdzunaClient:
    app_id: str
    app_key: str
    max_calls: int = ADZUNA_MAX_CALLS_PER_DAY
    max_retries: int = 3
    backoff_seconds: float = 2.0
    min_interval: float = 1.0       # pause between calls, stays under per-minute limits
    timeout: float = 30.0
    session: requests.Session = field(default_factory=requests.Session)
    calls_made: int = 0
    _last_call: float = 0.0

    @classmethod
    def from_settings(cls, **kwargs) -> AdzunaClient:
        s = get_settings()
        s.require("adzuna_app_id", "adzuna_app_key")
        return cls(app_id=s.adzuna_app_id, app_key=s.adzuna_app_key, **kwargs)

    def search(self, what: str, where: str | None = None, page: int = 1) -> list[dict]:
        """Return one page of job results (a list of raw job dicts)."""
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": ADZUNA_RESULTS_PER_PAGE,
            "what": what,
            "max_days_old": 3,          # only recent postings
            "sort_by": "date",
            "content-type": "application/json",
        }
        if where:
            params["where"] = where
        url = BASE_URL.format(country=ADZUNA_COUNTRY, page=page)

        for attempt in range(self.max_retries + 1):
            if self.calls_made >= self.max_calls:
                raise BudgetExceeded(f"API call budget of {self.max_calls} used up")
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            self.calls_made += 1
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as e:
                if attempt == self.max_retries:
                    raise AdzunaError(f"network error: {type(e).__name__}") from e
            else:
                if response.status_code == 200:
                    return response.json().get("results", [])
                if response.status_code not in RETRY_STATUS or attempt == self.max_retries:
                    # Never include the URL in errors: it contains the API key.
                    raise AdzunaError(f"HTTP {response.status_code} for what={what!r}")
            time.sleep(self.backoff_seconds * (2 ** attempt))
        return []  # unreachable, keeps type checkers happy
