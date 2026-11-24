"""Find skills in stored jobs and save them to job_skills.

Run:
    python pipelines/extract_skills.py                 # dictionary only (fast, used nightly)
    python pipelines/extract_skills.py --embeddings    # + meaning-based Layer B

Only processes jobs that are new, or were processed with an older version of
the skill dictionary, so it is cheap to run every night.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter

from skillpulse.db import repository as repo
from skillpulse.db.connection import get_connection
from skillpulse.nlp.extractor import DictionaryExtractor, HybridExtractor, job_text
from skillpulse.nlp.taxonomy import default_skills, taxonomy_version


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract skills from stored jobs")
    parser.add_argument("--embeddings", action="store_true", help="also use Layer B")
    parser.add_argument("--threshold", type=float, help="Layer B similarity threshold")
    args = parser.parse_args()

    skills = default_skills()
    version = taxonomy_version()
    embedding = None
    if args.embeddings:
        from skillpulse.nlp.embedding_extractor import DEFAULT_THRESHOLD, EmbeddingExtractor
        embedding = EmbeddingExtractor(skills, threshold=args.threshold or DEFAULT_THRESHOLD)
        version += "+emb"
    extractor = HybridExtractor(DictionaryExtractor(skills), embedding)

    started = time.time()
    total_jobs = total_links = 0
    counts: Counter[str] = Counter()
    with get_connection() as conn:
        skill_ids = repo.sync_skills(conn, skills)
        while True:
            batch = repo.jobs_needing_skills(conn, version, limit=1000)
            if not batch:
                break
            results = []
            for job_id, title, description in batch:
                found = extractor.matches(job_text(title, description))
                counts.update(m.skill for m in found)
                results.append((job_id, [(skill_ids[m.skill], m.method) for m in found]))
            total_links += repo.save_job_skills(conn, results, version)
            total_jobs += len(batch)
            conn.commit()

    print(f"Dictionary version: {version} ({len(skills)} skills)")
    print(f"Jobs processed:     {total_jobs}")
    print(f"Skills found:       {total_links}"
          + (f" (avg {total_links / total_jobs:.1f} per job)" if total_jobs else ""))
    if counts:
        print("Most common:        " + ", ".join(f"{s} ({n})" for s, n in counts.most_common(12)))
    print(f"Time:               {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
