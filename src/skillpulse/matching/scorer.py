"""Match score: how well a resume covers what employers ask for.

How it works, in plain language:
1. Take the top 30 skills for the chosen role (from real postings), each with its
   "weight" = the share of postings that mention it. A skill in 40% of postings
   matters more than one in 5%.
2. Score = (total weight of the skills you HAVE) / (total weight of all 30) x 100.
3. Missing skills are ranked by weight. For each one we also show how many points
   your score would gain by learning it ("what-if").

Example: top skills SQL (0.5), Excel (0.3), Tableau (0.2). You have SQL and Excel:
score = (0.5 + 0.3) / (0.5 + 0.3 + 0.2) x 100 = 80. Learning Tableau adds +20.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

TOP_N = 30


@dataclass
class SkillGap:
    skill: str
    share: float        # share of postings mentioning it (0-1)
    gain: float = 0.0   # score points gained by adding it


@dataclass
class MatchResult:
    score: float                                  # 0-100
    have: list[SkillGap] = field(default_factory=list)
    missing: list[SkillGap] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)  # user skills outside the top list
    postings: int = 0                             # sample size behind the weights


def score_resume(user_skills: set[str], demand: pd.DataFrame, postings: int = 0) -> MatchResult:
    """demand: DataFrame with columns skill, share (most-demanded first)."""
    top = demand.nlargest(TOP_N, "share")[["skill", "share"]]
    total = float(top["share"].sum())
    if total == 0:
        return MatchResult(score=0.0, extra=sorted(user_skills), postings=postings)
    have = [SkillGap(r.skill, r.share) for r in top.itertuples() if r.skill in user_skills]
    missing = [SkillGap(r.skill, r.share, gain=100 * r.share / total)
               for r in top.itertuples() if r.skill not in user_skills]
    score = 100 * sum(g.share for g in have) / total
    extra = sorted(user_skills - set(top["skill"]))
    return MatchResult(round(score, 1), have, missing, extra, postings)


@dataclass
class RoleFit:
    role: str
    score: float
    postings: int
    next_skill: str | None      # the single most valuable skill to add for this role


MIN_POSTINGS_FOR_RANKING = 20   # roles with fewer postings would be ranked on noise


def rank_roles(user_skills: set[str], demand_by_role: dict[str, tuple[pd.DataFrame, int]],
               skip: frozenset[str] = frozenset()) -> list[RoleFit]:
    """Score one set of skills against every role (same method as the match score), best first.

    demand_by_role: role -> (demand DataFrame, postings). Roles with too few postings are left
    out rather than ranked on noise. `skip` = skills not worth suggesting (e.g. soft skills).
    """
    fits = []
    for role, (demand, postings) in demand_by_role.items():
        if postings < MIN_POSTINGS_FOR_RANKING or demand.empty:
            continue
        res = score_resume(user_skills, demand, postings)
        nxt = next((g.skill for g in res.missing if g.skill not in skip), None)
        fits.append(RoleFit(role, res.score, postings, nxt))
    return sorted(fits, key=lambda f: -f.score)
