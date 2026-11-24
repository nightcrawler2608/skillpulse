"""Measure how accurate skill extraction is, against your hand labels.

Run:  python scripts/evaluate_extraction.py [--no-embeddings]

Metrics (counted over every job-skill pair, "micro-averaged"):
  Precision = of the skills the extractor found, how many were really there
  Recall    = of the skills really there, how many the extractor found
  F1        = one number combining both (their harmonic mean)

Compares Layer A (dictionary) alone vs. Layer A + B at several thresholds, and
writes the results to reports/extraction_eval.md for the project report.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from datetime import date

from skillpulse.config import PROJECT_ROOT
from skillpulse.nlp.evalsets import SPLITS, labels_path, sample_path
from skillpulse.nlp.extractor import DictionaryExtractor
from skillpulse.nlp.taxonomy import default_skills

THRESHOLDS = [0.70, 0.75, 0.80, 0.85, 0.90]


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score(truth: list[set[str]], pred: list[set[str]]):
    tp = sum(len(t & p) for t, p in zip(truth, pred))
    fp = sum(len(p - t) for t, p in zip(truth, pred))
    fn = sum(len(t - p) for t, p in zip(truth, pred))
    return (*prf(tp, fp, fn), tp, fp, fn)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-embeddings", action="store_true")
    parser.add_argument("--split", choices=SPLITS, default="dev")
    parser.add_argument("--details", action="store_true",
                        help="print every wrong/missed skill per job (dev set only!)")
    args = parser.parse_args()
    SAMPLE, LABELS = sample_path(args.split), labels_path(args.split)
    REPORT = PROJECT_ROOT / "reports" / f"extraction_eval_{args.split}.md"

    if not LABELS.exists():
        print("No labels yet. Run:  streamlit run app/labeler.py")
        return 1
    with open(SAMPLE, encoding="utf-8", newline="") as f:
        texts = {r["job_id"]: r["text"] for r in csv.DictReader(f)}
    with open(LABELS, encoding="utf-8", newline="") as f:
        labels = list(csv.DictReader(f))

    ids = [r["job_id"] for r in labels]
    truth = [set(filter(None, r["skills"].split("|"))) for r in labels]
    other = Counter(o.strip().lower() for r in labels for o in r["other"].split(",") if o.strip())

    skills = default_skills()
    dictionary = DictionaryExtractor(skills)
    pred_a = [dictionary.extract(texts[i]) for i in ids]

    rows = [("Dictionary only (Layer A)", *score(truth, pred_a))]
    if not args.no_embeddings:
        from skillpulse.nlp.embedding_extractor import EmbeddingExtractor
        emb = EmbeddingExtractor(skills, threshold=0.0)
        cands = [emb.best_matches(texts[i]) for i in ids]   # encode once, reuse per threshold
        for th in THRESHOLDS:
            pred = [a | {s for _, s, sim in c if sim >= th} for a, c in zip(pred_a, cands)]
            rows.append((f"Dictionary + embeddings @ {th:.2f}", *score(truth, pred)))

    if args.details:
        if args.split == "test":
            print("Refusing --details on the test set: looking at test mistakes = tuning on it.")
            return 1
        for i, t, p in zip(ids, truth, pred_a):
            if t != p:
                ev = {m.skill: m.alias for m in dictionary.matches(texts[i])}
                print(f"\n[{i}] missed={sorted(t - p)} wrong={[(s, ev[s]) for s in sorted(p - t)]}")
                print("    " + texts[i][:600])

    # Per-skill errors for Layer A: what it misses / wrongly adds most often
    missed = Counter(s for t, p in zip(truth, pred_a) for s in t - p)
    extra = Counter(s for t, p in zip(truth, pred_a) for s in p - t)

    lines = [
        f"# Skill extraction evaluation: {args.split} set",
        "",
        (f"Date: {date.today()} · Jobs labelled: {len(labels)} · "
         f"Skills in dictionary: {len(skills)} · True job-skill pairs: {sum(map(len, truth))}"),
        "",
        "| Method | Precision | Recall | F1 | TP | FP | FN |",
        "|---|---|---|---|---|---|---|",
        *[f"| {n} | {p:.3f} | {r:.3f} | {f:.3f} | {tp} | {fp} | {fn} |"
          for n, p, r, f, tp, fp, fn in rows],
        "",
        "## Layer A: most missed skills (false negatives)",
        "",
        *[f"- {s}: {n}" for s, n in missed.most_common(10)],
        "",
        "## Layer A: most wrongly added skills (false positives)",
        "",
        *[f"- {s}: {n}" for s, n in extra.most_common(10)],
        "",
        "## Skills labellers needed that are not in the dictionary",
        "",
        *[f"- {s}: {n}" for s, n in other.most_common(20)],
    ]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved to {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
