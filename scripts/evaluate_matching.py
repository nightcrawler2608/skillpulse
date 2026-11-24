"""Measure job-matching quality with Precision@5, against simple baselines.

Precision@5 = of the top 5 jobs a method recommends for a resume, how many a person
judges relevant ("yes, this person could sensibly apply").

A number on its own means little, so we compare 4 methods on the same resumes:
    hybrid   the app's method: 50% meaning + 50% skill overlap
    meaning  embeddings only (100% meaning)
    skills   skill overlap only (re-ranks the same 50 nearest jobs)
    newest   the 5 newest postings for the role (what a plain job board shows)
    hybrid+level  hybrid, then jobs asking for far more experience sink (seniority.py)
    full     hybrid+level (more level words, date ranges, internships) + stack check

Adding a method later is incremental: re-run --prepare and only the new method runs;
jobs nobody judged yet are added to the sheet with an empty "relevant" cell.

Fair judging ("pooling", as in search-engine evaluation): every job that ANY method
put in its top 5 goes into one shuffled sheet, with no rank, score or method shown.
You judge each (resume, job) pair once; each method is then scored from the same
judgments. You can't favour the app because you don't know which method picked what.

Steps:
1. Put resumes in data/eval/eval_resumes/ as PDF or TXT (r01.pdf, r02.txt, ...).
   That folder is git-ignored: real resumes never go to GitHub. Get permission and
   remove names, phone numbers and emails first.
2. List them in data/eval/eval_resumes/queries.csv:
       file,role
       r01.pdf,Data Analyst
3. python scripts/evaluate_matching.py --prepare
   -> data/eval/matching_judgments.csv (one row per resume x job, shuffled)
4. Fill the "relevant" column with 1 or 0. Rule of thumb for 1:
   the job is the target role (or very close), the level fits (a fresher resume vs.
   a 0-3 years job), and the person has at least some of the job's core skills.
5. python scripts/evaluate_matching.py
   -> Precision@5 for each method, saved to reports/matching_eval.md
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from datetime import date

from skillpulse.analytics import market
from skillpulse.config import PROJECT_ROOT
from skillpulse.db.connection import get_connection
from skillpulse.matching.embedder import embed_resume
from skillpulse.matching.recommender import recommend
from skillpulse.matching.resume_parser import clean_text, pdf_to_text
from skillpulse.matching.resume_skills import resume_skills
from skillpulse.matching.seniority import resume_years
from skillpulse.nlp.extractor import DictionaryExtractor

EVAL = PROJECT_ROOT / "data" / "eval"
RESUMES = EVAL / "eval_resumes"
QUERIES = RESUMES / "queries.csv"
JUDGMENTS = EVAL / "matching_judgments.csv"
RUNS = EVAL / "matching_runs.json"          # which method ranked which jobs (hidden from judge)
REPORT = PROJECT_ROOT / "reports" / "matching_eval.md"
K = 5
METHODS: dict[str, dict | None] = {
    "hybrid": {"w": 0.5},
    "meaning": {"w": 1.0},
    "skills": {"w": 0.0},
    "newest": None,
    "hybrid+level": {"w": 0.5, "level": True},   # hybrid, then down-rank jobs above your level
    "full": {"w": 0.5, "level": True, "stack": True},  # + level v2, internships, stack
}
SNIPPET = 350

NEWEST_SQL = """
SELECT id, title, company FROM jobs
WHERE is_active AND role_id = %s
ORDER BY posted_at DESC NULLS LAST, id DESC
LIMIT 50
"""

DETAILS_SQL = """
SELECT j.id, j.title, j.company, j.city, left(j.description, %s) AS snippet,
       coalesce(string_agg(k.name, ', ' ORDER BY k.name), '') AS skills
FROM jobs j LEFT JOIN job_skills s ON s.job_id = j.id LEFT JOIN skills k ON k.id = s.skill_id
WHERE j.id = ANY(%s)
GROUP BY j.id
"""


def read_resume(name: str) -> str:
    path = RESUMES / name
    if path.suffix.lower() == ".pdf":
        return pdf_to_text(path.read_bytes())
    return clean_text(path.read_text(encoding="utf-8"))


def newest(conn, role_id: int, k: int = K) -> list[int]:
    """Baseline: newest postings, one per (title, company) like the app does."""
    seen, ids = set(), []
    for jid, title, company in conn.execute(NEWEST_SQL, (role_id,)).fetchall():
        if (title, company) not in seen:
            seen.add((title, company))
            ids.append(jid)
        if len(ids) == k:
            break
    return ids


def run_method(conn, method: str, text: str, vec, skills: set[str], role_id: int) -> list[int]:
    spec = METHODS[method]
    if spec is None:
        return newest(conn, role_id)
    years = resume_years(text) if spec.get("level") else None
    jobs = recommend(conn, vec, skills, role_id, top=K, w_meaning=spec["w"], have_years=years,
                     stack_check=spec.get("stack", False))
    return [int(x) for x in jobs["id"]]


def prepare(seed: int = 7) -> int:
    """Incremental: methods already in the runs file keep their frozen results and
    judgments; only new methods are run, and only never-judged jobs are added."""
    if not QUERIES.exists():
        print(f"Create {QUERIES} first (see the instructions at the top of this script).")
        return 1
    with open(QUERIES, encoding="utf-8-sig", newline="") as f:
        queries = list(csv.DictReader(f))
    runs: dict[str, dict[str, list[int]]] = (
        json.loads(RUNS.read_text(encoding="utf-8")) if RUNS.exists() else {})
    rows: list[dict] = []
    if JUDGMENTS.exists():
        with open(JUDGMENTS, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    judged = {(r["resume"], int(r["job_id"])) for r in rows}
    ex = DictionaryExtractor()
    new: dict[tuple[str, int], str] = {}          # (resume, job_id) -> role, not yet in sheet
    with get_connection() as conn:
        roles = {n: i for i, n in market.roles(conn)}
        for q in queries:
            if q["role"] not in roles:
                print(f"{q['file']}: unknown role {q['role']!r}. Use one of: {', '.join(roles)}")
                return 1
            todo = [m for m in METHODS if m not in runs.get(q["file"], {})]
            if not todo:
                continue
            text = read_resume(q["file"])
            vec, skills, role_id = embed_resume(text), resume_skills(text, ex), roles[q["role"]]
            runs.setdefault(q["file"], {})
            for method in todo:
                runs[q["file"]][method] = run_method(conn, method, text, vec, skills, role_id)
                for jid in runs[q["file"]][method]:
                    if (q["file"], jid) not in judged:
                        new[(q["file"], jid)] = q["role"]
            print(f"{q['file']}: ran {', '.join(todo)}; "
                  f"{sum(1 for r, _ in new if r == q['file'])} new jobs to judge")
        details = {r[0]: r for r in conn.execute(
            DETAILS_SQL, (SNIPPET, list({jid for _, jid in new}))).fetchall()} if new else {}
    added = []
    for (resume, jid), role in new.items():
        _, title, company, city, snippet, skills = details[jid]
        added.append({"resume": resume, "role": role, "job_id": jid, "title": title,
                      "company": company or "", "city": city or "", "job_skills": skills,
                      "snippet": " ".join((snippet or "").split()), "relevant": ""})
    random.Random(seed).shuffle(added)
    rows = sorted(rows + added, key=lambda r: r["resume"])   # stable: shuffled inside
    if rows:
        with open(JUDGMENTS, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    RUNS.write_text(json.dumps(runs, indent=1), encoding="utf-8")
    print(f"\n{len(added)} new rows to judge (empty 'relevant' cells) in {JUDGMENTS}")
    return 0


def precision_at_k(ranked: list[int], judged: dict[int, int], k: int = K) -> float:
    """Unjudged jobs can't occur (every top-k job is pooled). Fewer than k results count
    as misses, so a method can't look good by returning less."""
    return sum(judged.get(j, 0) for j in ranked[:k]) / k


def evaluate() -> int:
    if not (JUDGMENTS.exists() and RUNS.exists()):
        print("Run with --prepare first.")
        return 1
    with open(JUDGMENTS, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if any(r["relevant"].strip() not in ("0", "1") for r in rows):
        print("Some 'relevant' cells are empty or not 0/1. Please fill them all in.")
        return 1
    judged: dict[str, dict[int, int]] = {}
    for r in rows:
        judged.setdefault(r["resume"], {})[int(r["job_id"])] = int(r["relevant"])
    runs = json.loads(RUNS.read_text(encoding="utf-8"))
    per = {name: {m: precision_at_k(ids, judged[name]) for m, ids in methods.items()}
           for name, methods in runs.items()}
    mean = {m: sum(p[m] for p in per.values()) / len(per) for m in METHODS}
    wins = {m: sum(p["hybrid"] > p[m] for p in per.values()) for m in METHODS if m != "hybrid"}
    losses = {m: sum(p["hybrid"] < p[m] for p in per.values()) for m in METHODS if m != "hybrid"}
    lines = [f"# Job matching evaluation ({date.today()})", "",
             (f"Resumes: {len(per)} · judged pairs: {len(rows)} · metric: Precision@{K} "
              "(pooled, blind judging)"), "",
             "| Method | Precision@5 | Hybrid better / worse on |", "|---|---|---|",
             *[f"| {m} | **{mean[m]:.2f}** | "
               f"{'—' if m == 'hybrid' else f'{wins[m]} / {losses[m]} resumes'} |"
               for m in METHODS],
             "", "| Resume | " + " | ".join(METHODS) + " |", "|---" * (len(METHODS) + 1) + "|",
             *[f"| {n} | " + " | ".join(f"{p[m]:.1f}" for m in METHODS) + " |"
               for n, p in sorted(per.items())]]
    REPORT.parent.mkdir(exist_ok=True)
    notes = REPORT.with_name(REPORT.stem + "_notes.md")   # hand-written findings, kept
    extra = "\n" + notes.read_text(encoding="utf-8") if notes.exists() else ""
    REPORT.write_text("\n".join(lines) + "\n" + extra, encoding="utf-8")
    print("\n".join(lines))
    return 0


def use_set(name: str) -> None:
    """--set synthetic reads data/eval/synthetic_resumes/ and writes *_synthetic files,
    so a trial run on made-up resumes never mixes with the real evaluation."""
    global RESUMES, QUERIES, JUDGMENTS, RUNS, REPORT
    RESUMES = EVAL / f"{name}_resumes"
    QUERIES = RESUMES / "queries.csv"
    JUDGMENTS = EVAL / f"matching_judgments_{name}.csv"
    RUNS = EVAL / f"matching_runs_{name}.json"
    REPORT = PROJECT_ROOT / "reports" / f"matching_eval_{name}.md"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--set", choices=["eval", "synthetic", "heldout"], default="eval",
                    help="eval = real resumes (default); synthetic = made-up set used for "
                         "tuning; heldout = made-up set kept untouched until the final check")
    args = ap.parse_args()
    if args.set != "eval":
        use_set(args.set)
    sys.exit(prepare() if args.prepare else evaluate())
