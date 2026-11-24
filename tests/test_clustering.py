import random

from skillpulse.analytics.clustering import closest_kind, cluster_jobs

GROUPS = {
    "java": ["Java", "Spring Boot", "Microservices"],
    "react": ["React", "JavaScript", "TypeScript"],
    "dotnet": [".NET", "C#", "Angular"],
}


def make_jobs(per_group=20, seed=1):
    rng = random.Random(seed)
    skills, titles = [], []
    for name, core in GROUPS.items():
        for _ in range(per_group):
            s = [x for x in core if rng.random() < 0.85]
            if len(s) < 2:
                s = core[:2]                         # every job lists 2+ distinct skills
            if rng.random() < 0.3:
                s.append("Git")                     # shared noise skill
            skills.append(s)
            titles.append(f"{name} developer")
    return skills, titles


def test_recovers_planted_groups_and_names_them():
    res = cluster_jobs(*make_jobs())
    assert res is not None and len(res.kinds) == 3 and res.silhouette > 0.3
    names = {kd.skills[0][0] for kd in res.kinds}
    assert names <= {s for core in GROUPS.values() for s in core}
    assert all("Git" not in kd.name for kd in res.kinds)   # common-everywhere skill doesn't name


def test_too_few_jobs_returns_none():
    skills, titles = make_jobs(per_group=5)                 # 15 jobs < 40
    assert cluster_jobs(skills, titles) is None


def test_no_distinct_kinds_returns_empty_result():
    skills = [["SQL", "Excel"]] * 45                       # everyone asks for the same mix
    res = cluster_jobs(skills, ["Data Analyst"] * 45)
    assert res is not None and res.kinds == [] and res.n_jobs == 45


def test_single_skill_jobs_are_ignored():
    skills, titles = make_jobs()
    skills += [["Java"]] * 50
    titles += ["x"] * 50
    res = cluster_jobs(skills, titles)
    assert res.n_jobs == 60 and res.n_total == 110


def test_closest_kind():
    res = cluster_jobs(*make_jobs())
    i = closest_kind(res, {"React", "TypeScript"})
    assert "React" in [s for s, _ in res.kinds[i].skills]
    assert closest_kind(res, {"Excel"}) is None
