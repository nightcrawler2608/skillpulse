"""Find skills in text.

Layer A, DictionaryExtractor: looks for every known spelling of every skill.
  Fast, precise and fully explainable ("found 'ms excel' -> Microsoft Excel").
  Misses spellings that aren't in the dictionary.

Layer B, EmbeddingExtractor (in embedding_extractor.py): compares the meaning of
  short phrases with skill names, to catch spellings Layer A doesn't know.

The same extractor is used for job postings AND resumes, so comparing a resume
with the market is fair.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from skillpulse.nlp.taxonomy import Skill, default_skills

# A skill must not be glued to other letters/digits: "Java" must not match inside
# "JavaScript", "SQL" not inside "MySQL", "C" not inside "C++".
LEFT = r"(?<![A-Za-z0-9&])"
# ...and not followed by "-<digit>", which is a reference code ("R-71763"), not a skill.
RIGHT = r"(?![A-Za-z0-9+#&])(?!-\d)"


@dataclass(frozen=True)
class Match:
    skill: str
    alias: str      # the exact text that was found
    method: str     # "dictionary" or "embedding"


def job_text(title: str | None, description: str | None) -> str:
    """The text we extract from: title + description."""
    return " . ".join(p for p in (title, description) if p)


def _build_pattern(aliases: list[str], flags: int) -> re.Pattern | None:
    if not aliases:
        return None
    # Longest first, so "power bi" wins over a shorter overlapping alias.
    parts = sorted(set(aliases), key=len, reverse=True)
    body = "|".join(re.escape(a).replace(r"\ ", r"\s+") for a in parts)
    return re.compile(f"{LEFT}(?:{body}){RIGHT}", flags)


class DictionaryExtractor:
    method = "dictionary"

    def __init__(self, skills: tuple[Skill, ...] | list[Skill] | None = None):
        skills = skills if skills is not None else default_skills()
        self.skills = list(skills)
        # One spelling can belong to two skills: "c/c++" -> C and C++.
        self._ci: dict[str, list[str]] = defaultdict(list)
        self._cs: dict[str, list[str]] = defaultdict(list)
        for s in self.skills:
            for a in s.aliases:
                self._ci[a].append(s.name)
            for a in s.case_sensitive_aliases:
                self._cs[a].append(s.name)
        self._ci_re = _build_pattern(list(self._ci), re.IGNORECASE)
        self._cs_re = _build_pattern(list(self._cs), 0)

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", text)

    def matches(self, text: str | None) -> list[Match]:
        """All skills found, with the text that triggered each one (first hit per skill)."""
        if not text:
            return []
        found: dict[str, Match] = {}
        if self._ci_re:
            for m in self._ci_re.finditer(text):
                alias = self._norm(m.group(0))
                for skill in self._ci.get(alias.lower(), []):
                    found.setdefault(skill, Match(skill, alias, self.method))
        if self._cs_re:
            for m in self._cs_re.finditer(text):
                alias = self._norm(m.group(0))
                for skill in self._cs.get(alias, []):
                    found.setdefault(skill, Match(skill, alias, self.method))
        return list(found.values())

    def extract(self, text: str | None) -> set[str]:
        return {m.skill for m in self.matches(text)}


class HybridExtractor:
    """Layer A first; Layer B only adds skills that Layer A didn't find."""

    def __init__(self, dictionary: DictionaryExtractor, embedding=None):
        self.dictionary = dictionary
        self.embedding = embedding

    def matches(self, text: str | None) -> list[Match]:
        found = self.dictionary.matches(text)
        if self.embedding is not None:
            have = {m.skill for m in found}
            found += [m for m in self.embedding.matches(text) if m.skill not in have]
        return found

    def extract(self, text: str | None) -> set[str]:
        return {m.skill for m in self.matches(text)}
