"""Phase 0 health check: are all free services reachable with your keys?

Run:  python scripts/check_setup.py

It never prints your keys. Each service shows one of:
  OK       - working
  MISSING  - key not in .env yet (follow docs/SETUP_ACCOUNTS.md)
  FAIL     - key present but the service rejected it / could not connect
"""

from __future__ import annotations

import sys

import requests

from skillpulse.config import (
    ADZUNA_COUNTRY,
    CITIES,
    ROLES,
    get_settings,
    planned_daily_calls,
)

TIMEOUT = 20  # seconds


def check_adzuna(s) -> tuple[str, str]:
    if not (s.adzuna_app_id and s.adzuna_app_key):
        return "MISSING", "ADZUNA_APP_ID / ADZUNA_APP_KEY not set"
    url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
    params = {
        "app_id": s.adzuna_app_id,
        "app_key": s.adzuna_app_key,
        "results_per_page": 1,
        "what": "data analyst",
        "content-type": "application/json",
    }
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        return "FAIL", f"network error: {type(e).__name__}"
    if r.status_code != 200:
        return "FAIL", f"HTTP {r.status_code} (check app id/key)"
    data = r.json()
    count = data.get("count", 0)
    results = data.get("results", [])
    sample = results[0].get("title", "?") if results else "no results"
    return "OK", f"{count:,} 'data analyst' jobs in India. Sample: {sample!r}"


def check_database(s) -> tuple[str, str]:
    if not s.database_url:
        return "MISSING", "DATABASE_URL not set"
    try:
        from skillpulse.db.connection import get_connection

        with get_connection() as conn:
            version = conn.execute("SELECT version()").fetchone()[0]
            has_vector = conn.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
            ).fetchone()[0]
    except Exception as e:  # noqa: BLE001 - we want to report any failure
        return "FAIL", f"{type(e).__name__}: {str(e).splitlines()[0][:150]}"
    short_version = " ".join(version.split()[:2])
    vector_msg = "pgvector available" if has_vector else "pgvector NOT available"
    status = "OK" if has_vector else "FAIL"
    return status, f"{short_version}, {vector_msg}"


def check_gemini(s) -> tuple[str, str]:
    if not s.gemini_api_key:
        return "MISSING", "GEMINI_API_KEY not set"
    try:
        r = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": s.gemini_api_key},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        return "FAIL", f"network error: {type(e).__name__}"
    if r.status_code != 200:
        return "FAIL", f"HTTP {r.status_code} (check key)"
    names = [m["name"].removeprefix("models/") for m in r.json().get("models", [])]
    flash = [n for n in names if "flash" in n]
    return "OK", f"{len(names)} models available, e.g. {', '.join(flash[:3]) or names[:3]}"


def check_huggingface(s) -> tuple[str, str]:
    if not s.hf_token:
        return "MISSING", "HF_TOKEN not set (only needed in Phase 6)"
    try:
        r = requests.get(
            "https://huggingface.co/api/whoami-v2",
            headers={"Authorization": f"Bearer {s.hf_token}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        return "FAIL", f"network error: {type(e).__name__}"
    if r.status_code != 200:
        return "FAIL", f"HTTP {r.status_code} (check token)"
    return "OK", f"logged in as {r.json().get('name', '?')}"


def main() -> int:
    s = get_settings()
    print("\nSkillPulse setup check")
    print(f"Tracking {len(ROLES)} roles x {len(CITIES)} cities "
          f"= {planned_daily_calls()} Adzuna calls per daily run\n")

    checks = [
        ("Adzuna API", check_adzuna),
        ("Neon database", check_database),
        ("Gemini API", check_gemini),
        ("Hugging Face", check_huggingface),
    ]
    failed = False
    for name, fn in checks:
        status, msg = fn(s)
        print(f"  [{status:<7}] {name:<14} {msg}")
        failed |= status != "OK"

    print()
    if failed:
        print("Not everything is ready yet. See docs/SETUP_ACCOUNTS.md.")
        return 1
    print("All services ready. Phase 0 complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
