"""Find live jobs that fit a resume.

Two steps (a common "retrieve, then re-rank" design):
1. Retrieve: the database finds the 50 jobs whose embeddings are closest to the
   resume's (pgvector, cosine distance), within the chosen role.
2. Re-rank: combine two signals into a fit score:
     meaning  = how similar the texts are (cosine, rescaled to 0-1)
     skills   = smoothed share of the job's listed skills the resume already has:
                (matched + 0.5) / (listed + 1)   <- "Laplace smoothing"
                A job listing ONE skill you have isn't a 100% match; we're just less
                sure, so the score is pulled toward 50%. 1 of 1 -> 75%, 5 of 5 -> 92%,
                a job listing no skills -> 50% (no information either way).
     fit      = 50% meaning + 50% skills
3. Level: if we know the user's experience, multiply fit by a level factor so jobs
   asking for far more years sink (see seniority.py). To leave room for that, the
   database returns 100 candidates instead of 50.

The 50/50 weighting is a starting point; Precision@5 on hand-judged resumes
(scripts/evaluate_matching.py) is how we check whether it's any good.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from skillpulse.matching.embedder import to_pgvector
from skillpulse.matching.seniority import job_years, level_factor

CANDIDATES = 50
CANDIDATES_WITH_LEVEL = 100
# MiniLM cosine for related job/resume texts is typically ~0.15-0.65; map that to 0-1.
SIM_LOW, SIM_HIGH = 0.15, 0.65
W_MEANING = 0.5


def rescale_similarity(sim: float) -> float:
    return float(np.clip((sim - SIM_LOW) / (SIM_HIGH - SIM_LOW), 0.0, 1.0))


def smoothed_overlap(matched: int, listed: int, prior: float = 0.5, strength: float = 1.0) -> float:
    return (matched + prior * strength) / (listed + strength)


def fit_score(similarity: float, job_skills: set[str], user_skills: set[str],
              w_meaning: float = W_MEANING) -> tuple[float, float | None]:
    """Returns (fit 0-1, raw skill overlap 0-1 or None if the job lists no skills)."""
    meaning = rescale_similarity(similarity)
    matched = len(job_skills & user_skills)
    skills = smoothed_overlap(matched, len(job_skills))
    raw = matched / len(job_skills) if job_skills else None
    return w_meaning * meaning + (1 - w_meaning) * skills, raw


CANDIDATE_SQL = """
WITH c AS (
    SELECT id, title, company, city, posted_at, url, description,
           1 - (embedding <=> %(vec)s::vector) AS similarity
    FROM jobs
    WHERE is_active AND embedding IS NOT NULL AND role_id = %(role)s {city_filter}
    ORDER BY embedding <=> %(vec)s::vector
    LIMIT %(k)s
)
SELECT c.*, coalesce(array_agg(k.name) FILTER (WHERE k.name IS NOT NULL), '{{}}') AS skills
FROM c LEFT JOIN job_skills s ON s.job_id = c.id LEFT JOIN skills k ON k.id = s.skill_id
GROUP BY c.id, c.title, c.company, c.city, c.posted_at, c.url, c.description, c.similarity
"""


def recommend(conn, resume_vec: np.ndarray, user_skills: set[str], role_id: int,
              city: str | None = None, top: int = 10,
              w_meaning: float = W_MEANING, have_years: float | None = None) -> pd.DataFrame:
    """have_years=None switches the level step off (the original method)."""
    sql = CANDIDATE_SQL.format(city_filter="AND city = %(city)s" if city else "")
    k = CANDIDATES if have_years is None else CANDIDATES_WITH_LEVEL
    cur = conn.execute(sql, {"vec": to_pgvector(resume_vec), "role": role_id,
                             "city": city, "k": k})
    cols = [d.name for d in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=cols)
    if df.empty:
        return df
    scored = [fit_score(r.similarity, set(r.skills), user_skills, w_meaning)
              for r in df.itertuples()]
    df["fit"] = [s[0] for s in scored]
    df["skill_overlap"] = [s[1] for s in scored]
    # computed as a plain list: inside a pandas column "unknown" (None) would turn into NaN
    levels = [job_years(r.title, r.description if isinstance(r.description, str) else "")
              for r in df.itertuples()]
    df["job_years"] = levels
    if have_years is not None:
        df["fit"] = [f * level_factor(y, have_years) for f, y in zip(df["fit"], levels)]
    df["matched"] = [sorted(set(r.skills) & user_skills) for r in df.itertuples()]
    df["to_learn"] = [sorted(set(r.skills) - user_skills) for r in df.itertuples()]
    # The same ad is often posted once per city; show it once (best-ranked copy).
    df = df.sort_values("fit", ascending=False)
    df = df.drop_duplicates(subset=["title", "company"], keep="first")
    return df.head(top).reset_index(drop=True)
