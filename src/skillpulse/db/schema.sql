-- SkillPulse database schema.
-- Safe to run many times: everything uses IF NOT EXISTS.

CREATE EXTENSION IF NOT EXISTS vector;

-- The 10 standard roles we track
CREATE TABLE IF NOT EXISTS roles (
    id             SERIAL PRIMARY KEY,
    name           TEXT UNIQUE NOT NULL,
    search_term    TEXT NOT NULL,
    title_keywords TEXT[] NOT NULL
);

-- Skill dictionary (filled in Phase 2)
CREATE TABLE IF NOT EXISTS skills (
    id        SERIAL PRIMARY KEY,
    name      TEXT UNIQUE NOT NULL,
    category  TEXT NOT NULL,
    aliases   TEXT[] NOT NULL DEFAULT '{}',
    learn_url TEXT
);

-- One row per job posting
CREATE TABLE IF NOT EXISTS jobs (
    id            BIGSERIAL PRIMARY KEY,
    source        TEXT NOT NULL DEFAULT 'adzuna',
    source_job_id TEXT NOT NULL,
    dedupe_hash   TEXT NOT NULL,
    title         TEXT NOT NULL,
    role_id       INT REFERENCES roles(id),
    company       TEXT,
    city          TEXT,
    state         TEXT,
    category      TEXT,
    salary_min    NUMERIC,
    salary_max    NUMERIC,
    contract_type TEXT,
    contract_time TEXT,
    posted_at     TIMESTAMPTZ,
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    description   TEXT,            -- set to NULL after 30 days to save space
    url           TEXT,
    embedding     vector(384),     -- filled in Phase 4, NULL after 30 days
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (source, source_job_id)
);
CREATE INDEX IF NOT EXISTS jobs_role_active_idx ON jobs (role_id, is_active);
CREATE INDEX IF NOT EXISTS jobs_dedupe_idx      ON jobs (dedupe_hash);
CREATE INDEX IF NOT EXISTS jobs_posted_idx      ON jobs (posted_at);
CREATE INDEX IF NOT EXISTS jobs_embedding_idx   ON jobs USING hnsw (embedding vector_cosine_ops);

-- Which dictionary version was used to extract this job's skills (Phase 2).
-- When the dictionary changes, jobs with an old version are re-extracted.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skills_version TEXT;

-- Which skills each job mentions (filled in Phase 2)
CREATE TABLE IF NOT EXISTS job_skills (
    job_id   BIGINT REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INT    REFERENCES skills(id),
    method   TEXT NOT NULL,
    PRIMARY KEY (job_id, skill_id)
);

-- Pre-computed daily counts for the dashboard (filled in Phase 3)
CREATE TABLE IF NOT EXISTS skill_demand_daily (
    day        DATE NOT NULL,
    role_id    INT  REFERENCES roles(id),
    city       TEXT NOT NULL,
    skill_id   INT  REFERENCES skills(id),
    job_count  INT  NOT NULL,
    total_jobs INT  NOT NULL,
    PRIMARY KEY (day, role_id, city, skill_id)
);

-- One row per pipeline run (monitoring)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id           SERIAL PRIMARY KEY,
    started_at   TIMESTAMPTZ NOT NULL,
    finished_at  TIMESTAMPTZ,
    api_calls    INT,
    jobs_fetched INT,
    jobs_new     INT,
    jobs_unmapped INT,
    status       TEXT NOT NULL,
    error        TEXT
);

-- Anonymous user feedback and usage (Phase 6)
CREATE TABLE IF NOT EXISTS feedback (
    id         SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_id TEXT NOT NULL,
    role_id    INT REFERENCES roles(id),
    target     TEXT NOT NULL,
    job_id     BIGINT,
    rating     SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_events (
    id         SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_id TEXT NOT NULL,
    event      TEXT NOT NULL,
    role_id    INT
);
