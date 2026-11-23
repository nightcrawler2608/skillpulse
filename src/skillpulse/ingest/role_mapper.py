"""Map a messy job title to one of our 10 standard roles.

Example: "Jr. Data Analyst - Fresher (Remote)" -> "Data Analyst".

How it works: each role has keywords (see config.py). We look for those
keywords as whole words in the title. If several roles match, the longest
keyword wins, because it is more specific ("machine learning engineer" beats
"engineer"). If nothing matches, the job stays unmapped (role = None) and is
left out of the role statistics. That keeps the data honest instead of guessing.
"""

from __future__ import annotations

import re

from skillpulse.config import ROLES, Role


def _pattern(keyword: str) -> re.Pattern:
    # \b = word boundary, so "sre" doesn't match inside "measured"
    return re.compile(r"\b" + re.escape(keyword.lower()) + r"\b")


class RoleMapper:
    def __init__(self, roles: tuple[Role, ...] = ROLES, role_ids: dict[str, int] | None = None):
        self.role_ids = role_ids or {}
        self._rules = sorted(
            ((len(kw), _pattern(kw), role.name) for role in roles for kw in role.title_keywords),
            key=lambda rule: -rule[0],  # longest keyword first
        )

    def role_name(self, title: str) -> str | None:
        t = title.lower()
        for _length, pattern, name in self._rules:
            if pattern.search(t):
                return name
        return None

    def role_id(self, title: str) -> int | None:
        name = self.role_name(title)
        return self.role_ids.get(name) if name else None
