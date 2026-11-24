"""Skills from a resume: the same dictionary as for jobs, plus two resume-only rules.

1. Plain "AI" counts in a resume. In job ads we ignore it in the body because it's
   usually company marketing ("our AI journey"); a resume has no marketing.
2. Specific skills imply the broad one they belong to. Someone with Machine
   Learning, LLMs or Generative AI clearly has "Artificial Intelligence" skills;
   someone with AWS or Azure has "Cloud Computing". Without this, students would
   be told to "learn AI" when they already have it, which is wrong and unfair.
"""

from __future__ import annotations

import re

from skillpulse.nlp.extractor import DictionaryExtractor

AI_WORD = re.compile(r"(?<![A-Za-z0-9])AI(?![A-Za-z0-9])")

IMPLIES: dict[str, set[str]] = {
    "Artificial Intelligence": {"Machine Learning", "Deep Learning", "Natural Language Processing",
                                "Computer Vision", "Generative AI", "Large Language Models",
                                "AI Agents", "RAG"},
    "Cloud Computing": {"AWS", "Microsoft Azure", "Google Cloud"},
}


def resume_skills(text: str, extractor: DictionaryExtractor) -> set[str]:
    skills = extractor.extract(text)
    if AI_WORD.search(text):
        skills.add("Artificial Intelligence")
    for broad, specific in IMPLIES.items():
        if skills & specific:
            skills.add(broad)
    return skills
