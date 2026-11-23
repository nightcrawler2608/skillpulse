# SkillPulse — Complete Project Plan

> Live job-market intelligence + resume gap analyzer for freshers in India.
> Budget: **₹0**. Every tool below has a free tier that needs **no credit card**.

---

## 1. Problem statement (for submission)

Fresh graduates in India apply to hundreds of jobs without knowing which skills the market
currently demands, or how far their own profile is from a target role. Job portals list
openings but do not analyse them. **SkillPulse** is a live, AI-powered platform that:

1. collects real job postings automatically every day,
2. uses NLP to extract and track in-demand skills by role, city and time,
3. compares a user's resume against live market demand to produce a match score,
   a ranked list of missing skills, matching jobs, and a personalised learning plan.

**Objectives (measurable):**

| # | Objective | Success measure |
|---|-----------|-----------------|
| O1 | Automated daily data pipeline | Runs daily with no manual work; 20,000+ postings collected |
| O2 | Accurate skill extraction | Recall ≥ 0.80, Precision ≥ 0.85 on 150 hand-labelled postings |
| O3 | Relevant job matching | Precision@5 ≥ 0.70 on 30 test resumes |
| O4 | Publicly usable product | Live URL, used by 100+ real users |
| O5 | Privacy by design | Zero resumes stored |

---

## 2. Tech stack (all free)

| Layer | Tool | Free limit (verify at signup — free tiers change) | Why this one |
|-------|------|------------------------------------|--------------|
| Language | Python 3.11+ | — | Industry standard for DS |
| Job data | **Adzuna API** (India endpoint `in`) | ~250 calls/day, 50 jobs per call | Official API → legal, no scraping |
| Historical data (EDA only) | Kaggle job-postings dataset | Free download | Extra data for analysis and labelling |
| Skill list | **O\*NET Technology Skills** + hand-curated aliases | Public domain | Credible, citable source |
| Data handling | pandas, numpy | — | Cleaning, aggregation |
| NLP | spaCy (`PhraseMatcher`) | — | Fast dictionary matching |
| Embeddings | `sentence-transformers` → `all-MiniLM-L6-v2` (384-dim) | Runs on CPU | Semantic similarity, small model |
| ML | scikit-learn | — | Clustering, evaluation metrics |
| Database | **Neon PostgreSQL** + `pgvector` extension | 0.5 GB storage | Real SQL DB + vector search |
| Scheduler | **GitHub Actions** (cron) | Unlimited minutes on **public** repo | Runs the daily pipeline for free |
| LLM | **Google Gemini API** (Flash model, AI Studio key) | Free daily quota | Writes the learning plan |
| Resume parsing | `pdfplumber` | — | Extract text from PDF |
| Web app | **Streamlit** | — | Quick to build DS-style UI |
| Charts | Plotly | — | Interactive charts |
| Hosting | **Hugging Face Spaces** (CPU basic) | 2 vCPU, 16 GB RAM, sleeps when idle | Enough RAM for the embedding model |
| Code + CI | GitHub (public repo) | Free | Portfolio + automated tests |
| Tests | pytest, ruff | — | Code quality |

**Why not Render/Railway for hosting?** Render's free tier has 512 MB RAM, which is too small for
PyTorch + the embedding model. HF Spaces gives 16 GB for free.

**Why Neon over Supabase?** A free Supabase project pauses after 7 days with no activity. Neon
scales to zero and wakes up automatically. Both support pgvector, so you can switch later.

---

## 3. System architecture

```
┌─────────────────────────── OFFLINE (runs daily, GitHub Actions) ───────────────────────────┐
│                                                                                            │
│  Adzuna API ──► [1. Fetch] ──► [2. Clean & dedupe] ──► [3. Map title → role]               │
│                                                              │                             │
│                                                              ▼                             │
│                 [6. Aggregate daily skill counts] ◄── [5. Embed text] ◄── [4. Extract skills]│
│                              │                              │                   │          │
└──────────────────────────────┼──────────────────────────────┼───────────────────┼──────────┘
                               ▼                              ▼                   ▼
                    ┌──────────────────────────── Neon PostgreSQL + pgvector ───────────────┐
                    │ jobs · skills · job_skills · skill_demand_daily · pipeline_runs ·     │
                    │ feedback · usage_events                                              │
                    └───────────────────────────────────────▲──────────────────────────────┘
                                                            │ SQL reads / vector search
┌─────────────────────────── ONLINE (Hugging Face Space, Streamlit) ─────────────────────────┐
│                                                                                            │
│  Page 1: Market Dashboard   → top skills, rising/falling skills, city & salary views       │
│  Page 2: Resume Analyzer    → upload PDF → extract skills → score → gaps → top jobs        │
│                                └──► Gemini API → week-by-week learning plan                │
│  Page 3: Role Explorer      → clusters ("3 kinds of Data Analyst jobs")                    │
│  Page 4: About & Methodology→ evaluation numbers, privacy statement                        │
│                                                                                            │
│  Resume never leaves memory. Only anonymous events + ratings are saved.                   │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Key design idea:** the code is split into a **core Python package** (`src/skillpulse/`) that does all
the logic, plus two thin entry points: the daily pipeline script and the Streamlit app. The same
skill extractor is used for job postings and resumes, so the comparison is fair. Adding a FastAPI
layer later only means wrapping the core package.

---

## 4. Data flow in detail

### 4a. Daily pipeline (every day at 02:00 IST)

| Step | What happens | Plain-language meaning |
|------|--------------|------------------------|
| 1. Fetch | For each (role keyword × city): call Adzuna, 2 pages × 50 results | 10 roles × 7 cities × 2 pages = **140 calls/day** (under the limit) |
| 2. Clean | Strip HTML, normalise city names, parse salary, drop postings with missing title | Make messy data uniform |
| 3. Dedupe | Skip if `source_job_id` exists; also hash(title+company+city) to catch reposts | Don't count the same job twice |
| 4. Role mapping | Rules + keywords: "Jr. Data Analyst - Fresher" → `Data Analyst` | Group job titles into 10 standard roles |
| 5. Skill extraction | Layer A: dictionary/alias match. Layer B: embedding match of noun phrases to canonical skills (similarity ≥ threshold) | Find skills even when written differently ("MS Excel" = "Excel") |
| 6. Embedding | Encode `title + description` → 384 numbers | Enables "find similar jobs" |
| 7. Store | Insert into `jobs`, `job_skills` | Save results |
| 8. Aggregate | Recompute `skill_demand_daily` for today | Pre-computed counts so the dashboard is fast |
| 9. Housekeeping | Mark jobs older than 30 days inactive, delete their embedding + description | Stay under 0.5 GB |
| 10. Log | Write a row to `pipeline_runs` (counts, duration, errors) | Monitoring, which shows MLOps thinking |

**Note:** the Adzuna API returns a **shortened description** (snippet), not the full posting. We
combine title + snippet + category for extraction. This is a known limitation, and you should
document it honestly in the report.

### 4b. Resume analysis (when a user uploads)

```
PDF ─► pdfplumber text ─► same skill extractor ─► user_skills
                       └─► embed resume text ─► resume_vector
role chosen by user ─► top-30 demanded skills for that role (last 30 days, from DB)

match_score   = Σ weight(skill) for skills user has  /  Σ weight(skill) for top-30 skills  × 100
                where weight = share of role's postings that mention the skill
missing_skills = top-30 skills not in user_skills, ranked by weight
top_jobs      = pgvector cosine search: 10 nearest active jobs of that role to resume_vector
learning_plan = Gemini(prompt with missing skills + role)  → fallback template if quota hit
```

Then the resume text and vector are **discarded**.

### 4c. Storage budget (fits within 0.5 GB)

~1,000 new unique jobs/day × 30 active days = 30,000 rows × ~2.5 KB (text + vector) ≈ **75 MB**.
Older jobs keep only metadata + skill links (~0.3 KB each) → ~100 MB/year. Aggregates are tiny.

---

## 5. Database schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE roles (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,          -- 'Data Analyst'
    search_term TEXT NOT NULL,                 -- query sent to Adzuna
    title_keywords TEXT[] NOT NULL             -- used for role mapping
);

CREATE TABLE skills (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,          -- canonical: 'Microsoft Excel'
    category    TEXT NOT NULL,                 -- language / tool / cloud / soft / concept
    aliases     TEXT[] NOT NULL DEFAULT '{}',  -- 'excel', 'ms excel', 'spreadsheets'
    learn_url   TEXT                           -- free resource for the learning plan
);

CREATE TABLE jobs (
    id            BIGSERIAL PRIMARY KEY,
    source        TEXT NOT NULL DEFAULT 'adzuna',
    source_job_id TEXT NOT NULL,
    dedupe_hash   TEXT NOT NULL,
    title         TEXT NOT NULL,
    role_id       INT REFERENCES roles(id),
    company       TEXT,
    city          TEXT,
    salary_min    NUMERIC,
    salary_max    NUMERIC,
    contract_type TEXT,
    posted_at     TIMESTAMPTZ,
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    description   TEXT,                        -- nulled after 30 days
    url           TEXT,
    embedding     vector(384),                 -- nulled after 30 days
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (source, source_job_id)
);
CREATE INDEX ON jobs (role_id, is_active);
CREATE INDEX ON jobs (dedupe_hash);
CREATE INDEX ON jobs USING hnsw (embedding vector_cosine_ops);

CREATE TABLE job_skills (
    job_id   BIGINT REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INT    REFERENCES skills(id),
    method   TEXT NOT NULL,                    -- 'dictionary' or 'embedding'
    PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE skill_demand_daily (
    day       DATE NOT NULL,
    role_id   INT  REFERENCES roles(id),
    city      TEXT NOT NULL,                   -- 'ALL' for national total
    skill_id  INT  REFERENCES skills(id),
    job_count INT  NOT NULL,                   -- postings mentioning this skill
    total_jobs INT NOT NULL,                   -- postings for this role/city/day
    PRIMARY KEY (day, role_id, city, skill_id)
);

CREATE TABLE pipeline_runs (
    id           SERIAL PRIMARY KEY,
    started_at   TIMESTAMPTZ NOT NULL,
    finished_at  TIMESTAMPTZ,
    api_calls    INT, jobs_fetched INT, jobs_new INT,
    status       TEXT NOT NULL,                -- 'success' / 'failed'
    error        TEXT
);

CREATE TABLE feedback (                        -- anonymous
    id         SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_id TEXT NOT NULL,                  -- random per browser session
    role_id    INT REFERENCES roles(id),
    target     TEXT NOT NULL,                  -- 'job_match' / 'gap_list' / 'plan'
    job_id     BIGINT,
    rating     SMALLINT NOT NULL               -- 1..5 or +1/-1
);

CREATE TABLE usage_events (                    -- anonymous
    id         SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_id TEXT NOT NULL,
    event      TEXT NOT NULL,                  -- 'page_view' / 'resume_analyzed' ...
    role_id    INT
);
```

**ER summary:** `roles 1─* jobs`, `jobs *─* skills` (through `job_skills`),
`skill_demand_daily` is a pre-computed summary of `job_skills` by day/role/city.

---

## 6. Folder structure

```
specialisation_project/
├── PLAN.md                      ← this file
├── README.md                    ← portfolio-quality README (Phase 7)
├── requirements.txt
├── .env.example                 ← names of secrets, never real values
├── .gitignore
├── src/skillpulse/
│   ├── config.py                ← reads env vars, roles, cities
│   ├── db/        schema.sql, connection.py, repository.py
│   ├── ingest/    adzuna_client.py, cleaner.py, role_mapper.py
│   ├── nlp/       taxonomy.py, extractor.py, embedder.py
│   ├── analytics/ trends.py, clustering.py
│   ├── matching/  resume_parser.py, scorer.py, recommender.py
│   └── llm/       planner.py    ← Gemini + fallback template
├── pipelines/daily_ingest.py    ← entry point for GitHub Actions
├── app/
│   ├── Home.py                  ← Streamlit entry
│   └── pages/ 1_Market.py, 2_Resume_Analyzer.py, 3_Role_Explorer.py, 4_About.py
├── data/
│   ├── skills/skills.csv        ← taxonomy + aliases
│   └── eval/labeled_jobs.csv, eval_resumes/ (anonymised)
├── notebooks/ 01_eda.ipynb, 02_extraction_eval.ipynb, 03_matching_eval.ipynb
├── tests/                       ← pytest
└── .github/workflows/ daily_ingest.yml, ci.yml, deploy_space.yml
```

---

## 7. Phases

Each phase ends with something **working and demoable**. Don't start a phase until the previous
one's "Done when" is true.

### Phase 0 — Setup & accounts (Week 1)
- **You:** create free accounts: GitHub, Adzuna developer, Neon, Hugging Face, Google AI Studio.
  Put keys in a local `.env` file. **Never paste keys into chat or commit them.**
- **Claude:** repo skeleton, virtual env, requirements, `.gitignore`, `.env.example`, config module.
- **Decide:** final list of 10 roles and 7 cities (defaults in §8).
- **Done when:** `python -c "import skillpulse"` works and a test query to Neon and Adzuna succeeds.

### Phase 1 — Data pipeline (Weeks 2–3) ⚠ start early
- Adzuna client with retry + rate-limit handling; cleaner; dedupe; role mapper.
- Create DB schema; seed `roles`.
- `daily_ingest.py` + GitHub Actions cron + `pipeline_runs` logging.
- **Why early:** trend charts need **weeks of history**. Every day the pipeline isn't running is
  data you can never get back.
- **Done when:** the Action has run 3 days in a row on its own, and the DB has 2,000+ jobs.

### Phase 2 — Skill taxonomy & extraction (Weeks 4–5)
- Build `skills.csv` (~300 skills with aliases) from O*NET + manual curation.
- Layer A: spaCy PhraseMatcher. Layer B: embedding matcher.
- **You:** hand-label skills in 150 postings (~6 hours; a labelling helper script makes it faster).
- Evaluation notebook: precision/recall/F1 for A vs A+B. Tune the threshold.
- Back-fill skills for all stored jobs.
- **Done when:** extraction metrics are recorded and meet O2 (or the gap is explained).

### Phase 3 — Analytics & market dashboard (Week 6)
- Aggregation job → `skill_demand_daily`.
- Trends: skill share over time, rising/falling (compare last 14 days vs previous 14).
- Streamlit Market page: role/city filters, top skills bar chart, trend lines, salary ranges.
- EDA notebook (good material for the report).
- **Done when:** the dashboard runs locally on real data.

### Phase 4 — Resume analyzer & job matching (Weeks 7–8)
- PDF parsing, resume skill extraction, match score, gap list.
- Job embeddings + pgvector top-10 search.
- Resume Analyzer page with clear visuals (score gauge, have/missing chips, job cards).
- **You:** collect 30 resumes from friends (with permission, names removed) and rate the top-5 matches.
- **Done when:** Precision@5 has been measured on the 30 resumes.

### Phase 5 — AI learning plan + role clustering (Week 9)
- Gemini prompt → structured weekly plan; fallback template if quota or network fails.
- KMeans on job skill vectors per role, choose k by silhouette score, name clusters by top skills.
- Role Explorer page.
- **Done when:** both features work, and the app still works with the LLM turned off.

### Phase 6 — Deploy, feedback & monitoring (Week 10)
- Deploy to Hugging Face Spaces via GitHub Action; secrets stored in Space settings.
- Feedback buttons + anonymous usage events.
- About page: methodology, metrics, privacy statement.
- CI: ruff + pytest on every push.
- **Done when:** the public URL works on a phone and a friend can use it without help.

### Phase 7 — Users, evaluation & documentation (Weeks 11–12)
- Share with classmates/college groups; collect 100+ uses.
- Final evaluation: extraction metrics, Precision@5, user ratings, pipeline uptime.
- README with screenshots, architecture, metrics; project report; PPT; 3-minute demo video.
- **Done when:** submission package is complete.

### Optional stretch (only if ahead of schedule)
- FastAPI REST layer (`/analyze`, `/skills/trending`) in a second Docker Space.
- Hinglish/regional job titles, salary prediction model, weekly email digest.

---

## 8. Default configuration (change in Phase 0 if you like)

**Roles (10):** Data Analyst, Data Scientist, Machine Learning Engineer, Data Engineer,
Business Analyst, Software Engineer, Frontend Developer, Backend Developer,
Full Stack Developer, DevOps / Cloud Engineer.

**Cities (7):** Bengaluru, Hyderabad, Pune, Chennai, Mumbai, Delhi NCR, Remote/All India.

---

## 9. Time estimate (honest)

| Item | Effort |
|------|--------|
| Code writing (Claude writes it, you review) | ~15–20 working sessions across all phases |
| Your work: accounts, labelling, testing, understanding code | ~60–80 hours total |
| Calendar time that can't be shortened | ~4–6 weeks of data collection for meaningful trends |
| **Realistic total** | **10–12 weeks** at ~8–10 hours/week; **6–8 weeks** if you work daily |

The code isn't the bottleneck. **Data accumulating, labelling, and real users** are. That's why
Phase 1 starts as soon as possible.

---

## 10. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Adzuna gives only description snippets | Use title + snippet + category; document as a limitation; Kaggle data for extra EDA |
| Free-tier limits change | Config-driven limits; LLM has a fallback; DB easily swapped (plain Postgres) |
| HF Space sleeps when idle (~30–60 s cold start) | Show a loading message; it's free tier, mention in README |
| GitHub disables scheduled Actions after 60 days with no repo activity | Regular commits; re-enable button; note in runbook |
| API key leaked | `.env` in `.gitignore`; GitHub/HF secrets only; pre-commit secret check |
| Poor extraction accuracy | Two-layer extractor + measured threshold tuning |
| Viva: "did you write this?" | Review every phase's code with Claude; keep a learning log |

---

## 11. What I need from you to start Phase 0

1. Confirm the roles and cities in §8 (or change them).
2. Create the five free accounts (GitHub, Adzuna, Neon, Hugging Face, Google AI Studio).
   I'll give click-by-click steps; you keep the keys and put them in `.env` yourself.
3. Say "start Phase 0".
