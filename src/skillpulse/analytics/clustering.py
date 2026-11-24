"""Role Explorer: the different "kinds" of jobs inside one role.

Example: Machine Learning Engineer postings split into classic ML, AI-agent and GenAI/LLM
jobs. Knowing which kind you're aiming for tells you which skills to learn first.

Method, in plain language:
1. Each job becomes a row of 0/1 values: does it ask for skill X? (soft skills like
   "Teamwork" are left out; only jobs listing 2+ skills are used, since a job listing
   one skill can't show which skills go together).
2. KMeans groups jobs whose skill lists look alike, for k = 2, 3, 4 groups.
3. We keep the k with the best silhouette score: how much closer each job is to its own
   group than to the next one (-1 to 1; above 0.5 = clear groups, 0.25-0.5 = some
   overlap, below 0.25 = heavy overlap). Groups smaller than 6 jobs aren't allowed.
4. Each group is named by the skills that are common in it AND more common than in the
   role overall (share x log(1 + lift)), so "Machine Learning" doesn't name every group.

Honesty rules: needs 40+ usable jobs, and the silhouette score is always shown.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

MIN_JOBS = 40
MIN_SKILLS_PER_JOB = 2
MIN_CLUSTER_SIZE = 6
K_RANGE = (2, 3, 4)
NAME_MIN_SHARE = 0.25


@dataclass
class JobKind:
    size: int
    share: float                                   # of the clustered jobs
    skills: list[tuple[str, float]]                # defining skills with their share
    titles: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return " · ".join(s for s, _ in self.skills[:3]) or "General"


@dataclass
class RoleClusters:
    kinds: list[JobKind]
    silhouette: float
    n_jobs: int                                    # jobs clustered
    n_total: int                                   # all active jobs in the role

    @property
    def strength(self) -> str:
        s = round(self.silhouette, 2)            # the same number the page shows
        if s >= 0.5:
            return "clear"
        return "some overlap" if s >= 0.25 else "heavy overlap"


def cluster_jobs(skills: list[list[str]], titles: list[str], seed: int = 0
                 ) -> RoleClusters | None:
    """skills[i] = skill names of job i (soft skills already removed)."""
    n_total = len(skills)
    keep = [i for i, s in enumerate(skills) if len(set(s)) >= MIN_SKILLS_PER_JOB]
    if len(keep) < MIN_JOBS:
        return None
    rows = [set(skills[i]) for i in keep]
    vocab = sorted(set().union(*rows))
    X = np.array([[v in r for v in vocab] for r in rows], dtype=float)

    best = None
    for k in K_RANGE:
        labels = KMeans(n_clusters=k, n_init=20, random_state=seed).fit_predict(X)
        if np.bincount(labels, minlength=k).min() < MIN_CLUSTER_SIZE:
            continue
        sil = float(silhouette_score(X, labels))
        if best is None or sil > best[0]:
            best = (sil, k, labels)
    if best is None:   # enough jobs, but every grouping had a tiny group: no clear kinds
        return RoleClusters([], 0.0, len(keep), n_total)
    sil, k, labels = best

    base = X.mean(axis=0)
    kept_titles = [titles[i] for i in keep]
    kinds = []
    for c in range(k):
        m = labels == c
        share = X[m].mean(axis=0)
        score = share * np.log1p(share / np.maximum(base, 1e-9))
        order = [i for i in np.argsort(-score) if share[i] >= NAME_MIN_SHARE][:6]
        examples = list(dict.fromkeys(t for t, mm in zip(kept_titles, m, strict=True) if mm))
        kinds.append(JobKind(int(m.sum()), float(m.mean()),
                             [(vocab[i], float(share[i])) for i in order], examples[:4]))
    kinds.sort(key=lambda kd: -kd.size)
    return RoleClusters(kinds, round(sil, 3), len(keep), n_total)


JOBS_SQL = """
SELECT j.title,
       coalesce(array_agg(k.name) FILTER (WHERE k.name IS NOT NULL AND k.category <> 'soft'),
                '{}') AS skills
FROM jobs j
LEFT JOIN job_skills s ON s.job_id = j.id
LEFT JOIN skills k ON k.id = s.skill_id
WHERE j.is_active AND j.role_id = %s
GROUP BY j.id, j.title
"""


def role_clusters(conn, role_id: int) -> RoleClusters | None:
    df = pd.DataFrame(conn.execute(JOBS_SQL, (role_id,)).fetchall(), columns=["title", "skills"])
    if df.empty:
        return None
    return cluster_jobs([list(s) for s in df.skills], df.title.tolist())


def closest_kind(result: RoleClusters, user_skills: set[str]) -> int | None:
    """Index of the kind whose defining skills the user covers best (weighted by share)."""
    scores = []
    for kd in result.kinds:
        total = sum(sh for _, sh in kd.skills) or 1.0
        scores.append(sum(sh for s, sh in kd.skills if s in user_skills) / total)
    return int(np.argmax(scores)) if scores and max(scores) > 0 else None
