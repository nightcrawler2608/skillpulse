"""The skill dictionary ("taxonomy"): every skill we track and its other spellings.

Source: data/skills/skills.csv (hand-curated). Columns:
  name                    canonical name shown in the app, e.g. "Power BI"
  category                group, e.g. "bi_tool", "language", "soft"
  aliases                 other spellings, matched ignoring case, separated by "|"
  case_sensitive_aliases  spellings that only count with exact capitals, e.g. "R",
                          "Excel", "Spark". Lowercase "excel" or "spark" are normal
                          English words, so we only trust the capitalised form.
  match_name              "no" = don't match the skill's own name, only its aliases
                          (for names that are generic words, e.g. "Leadership").
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from skillpulse.config import PROJECT_ROOT

SKILLS_CSV = PROJECT_ROOT / "data" / "skills" / "skills.csv"


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    aliases: tuple[str, ...]                 # lowercase, case-insensitive
    case_sensitive_aliases: tuple[str, ...]  # exact form


def _split(value: str) -> list[str]:
    return [a.strip() for a in (value or "").split("|") if a.strip()]


def load_skills(path: Path = SKILLS_CSV) -> list[Skill]:
    skills: list[Skill] = []
    seen: set[str] = set()
    # utf-8-sig: also reads files saved by Excel/PowerShell with a BOM marker
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = row["name"].strip()
            if name.lower() in seen:
                raise ValueError(f"duplicate skill in taxonomy: {name}")
            seen.add(name.lower())
            cs = tuple(_split(row.get("case_sensitive_aliases", "")))
            ci = {a.lower() for a in _split(row["aliases"])}
            # The canonical name also counts, unless: it is one of the "capitals
            # only" words (then it's already in cs), a 1-2 letter name like "Go"
            # or "C", or the CSV says match_name=no because the word is too
            # generic on its own ("leadership", "communication").
            match_name = (row.get("match_name") or "").strip().lower() != "no"
            if name not in cs and len(name) > 2 and match_name:
                ci.add(name.lower())
            skills.append(Skill(name, row["category"].strip(), tuple(sorted(ci)), cs))
    return skills


@lru_cache(maxsize=1)
def default_skills() -> tuple[Skill, ...]:
    return tuple(load_skills())


def taxonomy_version(path: Path = SKILLS_CSV) -> str:
    """Short fingerprint of the CSV. When the dictionary changes, the version
    changes, and the pipeline knows to re-extract skills for stored jobs."""
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]
