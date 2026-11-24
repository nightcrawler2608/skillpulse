"""Measure job-matching quality with Precision@5.

Precision@5 = of the top 5 jobs we recommend for a resume, how many are actually
relevant (a person judging them would say "yes, this person should apply").

Steps:
1. Put resumes in data/eval/eval_resumes/ as PDF or TXT, named r01.pdf, r02.txt, ...
   (that folder is git-ignored: real resumes never go to GitHub). Ask permission
   from friends, and remove names and phone numbers first.
2. List them with their target role in data/eval/eval_resumes/queries.csv:
       file,role
       r01.pdf,Data Analyst
3. python scripts/evaluate_matching.py --prepare
   -> writes data/eval/matching_judgments.csv with the top 5 jobs for each resume
4. Open that CSV and fill the "relevant" column with 1 (relevant) or 0 (not).
5. python scripts/evaluate_matching.py
   -> prints Precision@5 per resume and the average, and saves reports/matching_eval.md
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date

from skillpulse.analytics import market
from skillpulse.config import PROJECT_ROOT
from skillpulse.db.connection import get_connection
from skillpulse.matching.embedder import embed_resume
from skillpulse.matching.recommender import recommend
from skillpulse.matching.resume_parser import clean_text, pdf_to_text
from skillpulse.matching.resume_skills import resume_skills
from skillpulse.nlp.extractor import DictionaryExtractor

RESUMES = PROJECT_ROOT / "data" / "eval" / "eval_resumes"
QUERIES = RESUMES / "queries.csv"
JUDGMENTS = PROJECT_ROOT / "data" / "eval" / "matching_judgments.csv"
REPORT = PROJECT_ROOT / "reports" / "matching_eval.md"
K = 5


def read_resume(name: str) -> str:
    path = RESUMES / name
    if path.suffix.lower() == ".pdf":
        return pdf_to_text(path.read_bytes())
    return clean_text(path.read_text(encoding="utf-8"))


def prepare() -> int:
    if not QUERIES.exists():
        print(f"Create {QUERIES} first (see the instructions at the top of this script).")
        return 1
    with open(QUERIES, encoding="utf-8", newline="") as f:
        queries = list(csv.DictReader(f))
    ex = DictionaryExtractor()
    rows = []
    with get_connection() as conn:
        roles = {n: i for i, n in market.roles(conn)}
        for q in queries:
            text = read_resume(q["file"])
            jobs = recommend(conn, embed_resume(text), resume_skills(text, ex), roles[q["role"]],
                             top=K)
            for rank, j in enumerate(jobs.itertuples(), 1):
                rows.append({"resume": q["file"], "role": q["role"], "rank": rank,
                             "job_id": j.id, "title": j.title, "company": j.company,
                             "fit": round(j.fit, 3), "relevant": ""})
            print(f"{q['file']}: {len(jobs)} jobs")
    with open(JUDGMENTS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nNow fill the 'relevant' column (1/0) in {JUDGMENTS}")
    return 0


def evaluate() -> int:
    if not JUDGMENTS.exists():
        print("Run with --prepare first.")
        return 1
    with open(JUDGMENTS, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if any(r["relevant"].strip() not in ("0", "1") for r in rows):
        print("Some 'relevant' cells are empty or not 0/1. Please fill them all in.")
        return 1
    per = {}
    for r in rows:
        per.setdefault(r["resume"], []).append(int(r["relevant"]))
    p_at_k = {name: sum(v[:K]) / K for name, v in per.items()}
    mean = sum(p_at_k.values()) / len(p_at_k)
    lines = [f"# Job matching evaluation ({date.today()})", "",
             f"Resumes: {len(p_at_k)} · Precision@{K}: **{mean:.2f}**", "",
             "| Resume | Precision@5 |", "|---|---|",
             *[f"| {n} | {p:.2f} |" for n, p in sorted(p_at_k.items())]]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    sys.exit(prepare() if ap.parse_args().prepare else evaluate())
