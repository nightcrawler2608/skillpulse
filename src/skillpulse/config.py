"""Central configuration.

Two kinds of settings live here:
1. Secrets (API keys, DB URL) -> read from environment variables / the .env file.
2. Project choices (which roles and cities we track) -> plain Python constants,
   so they are versioned in git and easy to change in one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Project root = two folders above this file (src/skillpulse/config.py -> project root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from the project root if it exists. Real environment variables
# (e.g. GitHub Actions secrets) take priority over the file.
load_dotenv(PROJECT_ROOT / ".env", override=False)


# ---------------------------------------------------------------------------
# Roles we track
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Role:
    name: str                       # standard name shown in the app
    search_term: str                # what we send to the Adzuna API
    title_keywords: tuple[str, ...]  # used later to map messy job titles to this role


ROLES: tuple[Role, ...] = (
    Role("Data Analyst", "data analyst",
         ("data analyst", "analytics", "mis analyst", "power bi", "bi analyst",
          "bi developer", "reporting analyst")),
    Role("Data Scientist", "data scientist", ("data scientist", "data science")),
    Role("Machine Learning Engineer", "machine learning engineer",
         ("machine learning", "ml engineer", "ai engineer", "deep learning")),
    Role("Data Engineer", "data engineer", ("data engineer", "etl", "big data")),
    Role("Business Analyst", "business analyst", ("business analyst",)),
    Role("Software Engineer", "software engineer",
         ("software engineer", "software developer", "sde")),
    Role("Frontend Developer", "frontend developer",
         ("frontend", "front end", "front-end", "react developer", "ui developer")),
    Role("Backend Developer", "backend developer",
         ("backend", "back end", "back-end", "java developer", "python developer",
          "node developer")),
    Role("Full Stack Developer", "full stack developer",
         ("full stack", "fullstack", "full-stack", "mern")),
    Role("DevOps / Cloud Engineer", "devops engineer",
         ("devops", "cloud engineer", "site reliability", "sre", "platform engineer")),
)


# ---------------------------------------------------------------------------
# Cities we track
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class City:
    name: str                # standard name shown in the app
    adzuna_where: str | None  # value for Adzuna's "where" parameter (None = all of India)


CITIES: tuple[City, ...] = (
    City("Bengaluru", "Bangalore"),
    City("Hyderabad", "Hyderabad"),
    City("Pune", "Pune"),
    City("Chennai", "Chennai"),
    City("Mumbai", "Mumbai"),
    City("Delhi NCR", "Delhi"),
    City("All India", None),
)


# ---------------------------------------------------------------------------
# Pipeline limits (kept well under Adzuna's free quota of ~250 calls/day)
# ---------------------------------------------------------------------------
ADZUNA_COUNTRY = "in"
ADZUNA_RESULTS_PER_PAGE = 50
ADZUNA_PAGES_PER_QUERY = 2
ADZUNA_MAX_CALLS_PER_DAY = 200   # safety cap below the free limit
ACTIVE_JOB_DAYS = 30             # jobs older than this are marked inactive


def planned_daily_calls() -> int:
    """How many API calls one full daily run will make."""
    return len(ROLES) * len(CITIES) * ADZUNA_PAGES_PER_QUERY


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------
class MissingSettingError(RuntimeError):
    """Raised when a required secret is not set."""


@dataclass(frozen=True)
class Settings:
    adzuna_app_id: str | None
    adzuna_app_key: str | None
    database_url: str | None
    gemini_api_key: str | None
    hf_token: str | None

    @classmethod
    def from_env(cls) -> Settings:
        def get(name: str) -> str | None:
            value = os.getenv(name, "").strip()
            return value or None

        return cls(
            adzuna_app_id=get("ADZUNA_APP_ID"),
            adzuna_app_key=get("ADZUNA_APP_KEY"),
            database_url=get("DATABASE_URL"),
            gemini_api_key=get("GEMINI_API_KEY"),
            hf_token=get("HF_TOKEN"),
        )

    def require(self, *names: str) -> None:
        """Fail with a clear message if any of the given settings are missing."""
        missing = [n for n in names if getattr(self, n) is None]
        if missing:
            env_names = ", ".join(n.upper() for n in missing)
            raise MissingSettingError(
                f"Missing setting(s): {env_names}. Add them to your .env file "
                f"(see .env.example and docs/SETUP_ACCOUNTS.md)."
            )


def get_settings() -> Settings:
    return Settings.from_env()
