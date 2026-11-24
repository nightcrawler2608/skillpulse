"""Collect jobs for every (role x city) from Adzuna, cleaned and de-duplicated in memory.

This part has no database code, so it can be tested with a fake API client.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from skillpulse.config import ADZUNA_PAGES_PER_QUERY, ADZUNA_RESULTS_PER_PAGE, planned_queries
from skillpulse.ingest.adzuna_client import BudgetExceeded
from skillpulse.ingest.cleaner import CleanJob, clean_job
from skillpulse.ingest.role_mapper import RoleMapper

log = logging.getLogger(__name__)


@dataclass
class CollectResult:
    jobs: list[CleanJob] = field(default_factory=list)
    raw_count: int = 0  # results returned by the API (incl. duplicates)
    rejected: int = 0  # unusable records (no id/title)
    unmapped: int = 0  # kept, but title didn't match any role
    failed_queries: list[str] = field(default_factory=list)


def collect(client, mapper: RoleMapper, queries=None) -> CollectResult:
    """Fetch, clean, de-duplicate and role-map jobs. `client` needs a .search() method.
    `queries` defaults to the full daily plan (see config.planned_queries)."""
    result = CollectResult()
    seen_ids: set[str] = set()

    # Main searches (every role x city) come first, extra terms last: if the call budget
    # runs out, it's the extras that get skipped.
    for term, city in queries if queries is not None else planned_queries():
        query = f"{term} @ {city.name}"
        for page in range(1, ADZUNA_PAGES_PER_QUERY + 1):
            try:
                raw_jobs = client.search(term, city.adzuna_where, page)
            except BudgetExceeded:
                log.warning("API budget used up, stopping early at %s", query)
                return result
            except Exception as e:  # noqa: BLE001 - one bad query shouldn't stop the run
                log.error("query failed: %s (%s)", query, e)
                result.failed_queries.append(query)
                break

            result.raw_count += len(raw_jobs)
            for raw in raw_jobs:
                job = clean_job(raw)
                if job is None:
                    result.rejected += 1
                    continue
                if job.source_job_id in seen_ids:
                    continue  # same job found by another query
                seen_ids.add(job.source_job_id)
                job.role_id = mapper.role_id(job.title)
                if job.role_id is None:
                    result.unmapped += 1
                result.jobs.append(job)

            # A short page means there are no more results; save the API call.
            if len(raw_jobs) < ADZUNA_RESULTS_PER_PAGE:
                break
    return result
