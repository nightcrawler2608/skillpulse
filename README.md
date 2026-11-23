# SkillPulse

Live job-market intelligence and resume gap analyzer for freshers in India.

> 🚧 Work in progress. See [PLAN.md](PLAN.md) for the full plan and
> [docs/SETUP_ACCOUNTS.md](docs/SETUP_ACCOUNTS.md) to set up the free accounts.

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then fill in your keys
python scripts/check_setup.py
```

## Data pipeline (Phase 1)

```powershell
python -m skillpulse.db.migrate              # create tables + load roles (safe to re-run)
python pipelines/daily_ingest.py --dry-run   # fetch + clean only, prints a summary
python pipelines/daily_ingest.py             # full run: saves new jobs to the database
pytest -q                                    # run the tests
```

The pipeline runs automatically every night at 02:00 IST via
[.github/workflows/daily_ingest.yml](.github/workflows/daily_ingest.yml) once the repo is on
GitHub and these **repository secrets** are added (Settings → Secrets and variables → Actions):
`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `DATABASE_URL`.

**Flow:** Adzuna API → clean (HTML, cities, salaries) → de-duplicate (job id + title/company/city
hash) → map title to one of 10 roles → save to Postgres → expire jobs older than 30 days → log the
run in `pipeline_runs`.
