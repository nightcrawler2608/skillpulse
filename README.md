# SkillPulse

Live job-market intelligence and resume gap analyzer for freshers in India.

> 🚧 Work in progress. See [PLAN.md](PLAN.md) for the full plan and
> [docs/SETUP_ACCOUNTS.md](docs/SETUP_ACCOUNTS.md) to set up the free accounts.

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
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

## Resume analyzer (Phase 4)

```powershell
python pipelines/embed_jobs.py              # embeddings for new jobs (also runs nightly)
python scripts/evaluate_matching.py --prepare   # Precision@5 workflow (see script header)
```

- **Resume reading:** PDF (pdfplumber) or pasted text, in memory only, never stored.
- **Skills:** same dictionary as jobs, plus resume-only rules (plain "AI" counts; ML/LLM → AI,
  AWS/Azure/GCP → Cloud Computing). Users can add or remove skills before scoring.
- **Match score:** weighted coverage of the role's top 30 skills (weight = share of postings),
  with "what-if" points for each missing skill.
- **Job matches:** pgvector retrieves the 50 nearest jobs by meaning (all-MiniLM-L6-v2
  embeddings), then re-ranks: 50% meaning + 50% Laplace-smoothed skill overlap.

## Learning plan + Role Explorer (Phase 5)

- **Learning plan** (Resume analyzer → "Make my plan"): our code picks the skills (most score
  points first) and the schedule (1–2 weeks each, by size and hours per week); Gemini only words
  each week (goal, 3 tasks, mini project) as validated JSON. Links come from a hand-checked list
  ([data/skills/resources.csv](data/skills/resources.csv)), never from the AI. If Gemini is off
  (`SKILLPULSE_LLM=off`), missing a key, busy or invalid, a template writes the same plan. Only
  skill names, role, experience and hours are sent to Google, never resume text.
- **Role Explorer:** KMeans on each role's job skill lists (jobs with 2+ skills), k = 2–4 chosen
  by silhouette score, kinds named by skills that are common in the group *and* rarer in the
  role. The silhouette is shown on the page; roles with too little data say so.

## Online + feedback (Phase 6)

- Hosted free on Streamlit Community Cloud from this repo (`app/main.py`, deps in`n  [app/requirements.txt](app/requirements.txt)); setup in [docs/DEPLOY.md](docs/DEPLOY.md). Hugging Face`n  Docker Spaces now need a paid plan; the `Dockerfile` still works on any Docker host.
- The website connects as a limited database user (`python -m skillpulse.db.app_role`): read
  everything, insert only anonymous `feedback` and `usage_events`.
- 👍/👎 on the score, each job match, the plan and the Role Explorer; anonymous page and
  action counts (random per-tab ID, no cookies, no resume data). About page with methodology,
  accuracy and privacy. AI plans are limited to 5 per visit to share the free Gemini quota.

**Matching quality (synthetic trial, 20 held-out resumes, blind judging):** Precision@5 0.48 →
0.80 after adding an experience-level step and growing the job pool. Real-resume evaluation is
still to do. See [reports/matching_eval_heldout.md](reports/matching_eval_heldout.md).

**Job collection:** every role × city, plus 21 extra All-India search terms ("react developer",
"python developer", ...) that run last inside the daily cap. Lower the cap without code changes
via `ADZUNA_MAX_CALLS_PER_DAY` (in `.env`, or as a GitHub repository variable). After editing
role keywords, `python pipelines/remap_roles.py` re-maps stored jobs (also runs nightly).

**Flow:** Adzuna API → clean (HTML, cities, salaries) → de-duplicate (job id + title/company/city
hash) → map title to one of 10 roles → save to Postgres → expire jobs older than 30 days → log the
run in `pipeline_runs`.
