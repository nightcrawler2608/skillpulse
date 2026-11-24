"""Layer B: find skills by MEANING, not exact spelling.

How it works, in plain language:
1. Cut the text into short phrases of 1-3 words ("ms-excel reporting", "viz tools").
2. Turn every phrase, and every skill name/spelling, into a list of 384 numbers
   (an "embedding") using a small pre-trained model. Phrases with similar meaning
   get similar numbers.
3. If a phrase is very similar (cosine similarity >= threshold) to a skill, we
   count that skill as found.

The threshold is the key setting: too low gives lots of wrong matches, too high
finds nothing new. We pick it with the evaluation script, using hand-labelled
jobs, instead of guessing.

Needs: pip install -e ".[nlp]"  (sentence-transformers, ~300 MB with PyTorch)
"""

from __future__ import annotations

import re

import numpy as np

from skillpulse.nlp.extractor import Match
from skillpulse.nlp.taxonomy import Skill, default_skills

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_THRESHOLD = 0.80

STOPWORDS = {"a", "an", "and", "or", "the", "of", "to", "in", "on", "for", "with", "by", "at", "from", "as", "is", "are", "be", "been", "will", "would", "should", "can", "could", "may", "must", "our", "your", "their", "we", "you", "they", "it", "this", "that", "these", "those", "who", "which", "what", "when", "where", "how", "all", "any", "each", "other", "such", "than", "then", "so", "not", "no", "nor", "only", "own", "same", "very", "good", "strong", "excellent", "experience", "experienced", "knowledge", "understanding", "ability", "skills", "skill", "working", "work", "job", "role", "candidate", "team", "years", "year", "plus", "etc", "using", "use", "including", "include", "like", "well", "also", "must-have", "nice", "have", "has", "had", "required", "preferred", "hands-on", "proficiency", "proficient", "familiarity", "familiar", "exposure", "solid", "basic", "advanced"}

SPLIT_RE = re.compile(r"[,;:()\[\]{}|•\n\r\t]+|\s[-–]\s|\.\s|\band\b|\bor\b", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#./-]*")


def candidate_phrases(text: str, min_words: int = 2, max_words: int = 3) -> list[str]:
    """Short phrases that could be skill names.

    Single words are skipped by default: in testing, single generic words
    ("data", "analytics", "cloud") matched the wrong skill far too often.
    """
    phrases: set[str] = set()
    for segment in SPLIT_RE.split(text or ""):
        tokens = TOKEN_RE.findall(segment)
        for n in range(min_words, max_words + 1):
            for i in range(len(tokens) - n + 1):
                gram = tokens[i:i + n]
                if gram[0].lower() in STOPWORDS or gram[-1].lower() in STOPWORDS:
                    continue
                phrase = " ".join(gram).strip(".-/")
                if len(phrase) >= 3:
                    phrases.add(phrase)
    return sorted(phrases)


class EmbeddingExtractor:
    method = "embedding"

    def __init__(self, skills: tuple[Skill, ...] | list[Skill] | None = None,
                 threshold: float = DEFAULT_THRESHOLD, model=None):
        from sentence_transformers import SentenceTransformer  # heavy import, only when used

        self.threshold = threshold
        self.model = model or SentenceTransformer(MODEL_NAME)
        skills = skills if skills is not None else default_skills()
        self._labels: list[str] = []
        self._label_skill: list[str] = []
        self._known: set[str] = set()
        for s in skills:
            for label in {s.name, *s.aliases, *s.case_sensitive_aliases}:
                self._labels.append(label)
                self._label_skill.append(s.name)
                self._known.add(label.lower())
        self._label_vecs = self.encode(self._labels)

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, batch_size=128, normalize_embeddings=True,
                                            show_progress_bar=False))

    def best_matches(self, text: str) -> list[tuple[str, str, float]]:
        """(phrase, skill, similarity) for every candidate phrase, best skill only.
        Used by the evaluation script to try many thresholds without re-encoding."""
        phrases = [p for p in candidate_phrases(text) if p.lower() not in self._known]
        if not phrases:
            return []
        sims = self.encode(phrases) @ self._label_vecs.T   # cosine (vectors are normalised)
        best = sims.argmax(axis=1)
        return [(p, self._label_skill[j], float(sims[i, j])) for i, (p, j) in
                enumerate(zip(phrases, best))]

    def matches(self, text: str | None) -> list[Match]:
        found: dict[str, Match] = {}
        for phrase, skill, sim in sorted(self.best_matches(text or ""), key=lambda x: -x[2]):
            if sim >= self.threshold:
                found.setdefault(skill, Match(skill, phrase, self.method))
        return list(found.values())
