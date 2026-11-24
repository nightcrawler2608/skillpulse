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

## Skill extraction (Phase 2)

```powershell
pip install -e ".[nlp,app,dev]"                  # adds sentence-transformers + Streamlit
python pipelines/extract_skills.py               # find skills in stored jobs (also runs nightly)
python scripts/make_eval_sample.py               # once: pick 144 jobs to hand-label
streamlit run app/labeler.py                     # label them (job text only, no hints)
python scripts/evaluate_extraction.py            # precision / recall / F1 -> reports/
```

- **Dictionary:** [data/skills/skills.csv](data/skills/skills.csv), 249 skills with alternative spellings.
  Ambiguous words ("R", "Excel", "Spark", "Go") only count in their exact, unambiguous form.
- **Layer A (dictionary):** exact matching with word boundaries ("Java" ≠ "JavaScript", "SQL" ≠ "MySQL").
- **Layer B (embeddings):** `all-MiniLM-L6-v2` compares 2–3 word phrases with skill names by meaning.
  The evaluation decides whether it's worth keeping and at what threshold.

**Accuracy (held-out test set, 90 jobs):** precision 0.936, recall 0.860, F1 0.896.
See [reports/](reports/).

## Web app (Phase 3)

```powershell
python pipelines/aggregate.py --all     # build the daily skill-demand table (also runs nightly)
streamlit run app/main.py               # open http://localhost:8501
```

- **Home:** live "trending skills" ribbon, data freshness, what the app does.
- **Market dashboard:** top skills by role × city × time window, skill demand over time,
  rising/cooling skills (once 28 days of data exist), where the jobs are, advertised salary
  (only when ≥ 8 postings list pay), plus the numbers as a table.
- Every figure shows its sample size; small samples get a warning.

**Flow:** Adzuna API → clean (HTML, cities, salaries) → de-duplicate (job id + title/company/city
hash) → map title to one of 10 roles → save to Postgres → expire jobs older than 30 days → log the
run in `pipeline_runs`.
