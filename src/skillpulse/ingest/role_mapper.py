"""Map a messy job title to one of our 10 standard roles.

Example: "Jr. Data Analyst - Fresher (Remote)" -> "Data Analyst".

How it works: each role has keywords (see config.py). We look for those
keywords as whole words in the title. If several roles match:
1. Clear stack words win first: "Full Stack" beats everything ("Full Stack Java and
   Angular Developer" is Full Stack, not Frontend), then "Backend"/"Frontend".
2. Otherwise the longest keyword wins, because it is more specific
   ("machine learning engineer" beats "engineer").
3. Software Engineer is the fallback: its words ("software engineering", "application
   developer") only count when no more specific role matched.
If nothing matches, the job stays unmapped (role = None) and is left out of the role
statistics. That keeps the data honest instead of guessing.
"""

from __future__ import annotations

import re

from skillpulse.config import ROLES, Role


def _pattern(keyword: str) -> re.Pattern:
    # \b = word boundary, so "sre" doesn't match inside "measured"
    return re.compile(r"\b" + re.escape(keyword.lower()) + r"\b")


STACK_WORDS = {"full stack": 0, "fullstack": 0, "full-stack": 0, "mern": 0, "mean stack": 0,
               "backend": 1, "back end": 1, "back-end": 1,
               "frontend": 1, "front end": 1, "front-end": 1}
FALLBACK_ROLE = "Software Engineer"


def _tier(keyword: str, role: str) -> int:
    if keyword in STACK_WORDS:
        return STACK_WORDS[keyword]
    return 3 if role == FALLBACK_ROLE else 2


class RoleMapper:
    def __init__(self, roles: tuple[Role, ...] = ROLES, role_ids: dict[str, int] | None = None):
        self.role_ids = role_ids or {}
        self._rules = sorted(
            ((_tier(kw, role.name), len(kw), _pattern(kw), role.name)
             for role in roles for kw in role.title_keywords),
            key=lambda rule: (rule[0], -rule[1]),  # tier first, then longest keyword
        )

    def role_name(self, title: str) -> str | None:
        t = title.lower()
        for _tier_, _length, pattern, name in self._rules:
            if pattern.search(t):
                return name
        return None

    def role_id(self, title: str) -> int | None:
        name = self.role_name(title)
        return self.role_ids.get(name) if name else None
