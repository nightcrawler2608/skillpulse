"""Experience level: how many years a job wants, and how many a resume has.

Why: in the Precision@5 trial, 63% of irrelevant matches were senior jobs shown to
freshers. Meaning and skills can't see this ("Senior Data Scientist" and a fresher's
data-science resume are about the same topic), so we read the level separately.

Rules, in plain language:
- Job: if the text states years ("3+ years", "4-7 yrs", "minimum 5 years"), use the
  lowest number. Otherwise use the title: Senior/Sr ~5, Lead/Principal/Staff/Manager/
  VP... ~8, "III"/"L3" ~4, "II"/"L2" ~2, Junior/Fresher/Intern/Graduate 0.
  No signal -> unknown (no penalty: we don't punish what we can't read).
- Resume: the largest "N years"/"N months" of experience stated; 0 if none (fresher).
- Penalty: a job asking for at most 1 year more than you have is fine. Beyond that,
  the fit is multiplied by 0.85 per extra year, down to 0.3.
"""

from __future__ import annotations

import re
from datetime import date

# --- job side -----------------------------------------------------------------
_YEARS = re.compile(
    r"(?i)(?:min(?:imum)?\.?\s*(?:of\s*)?)?"
    r"\b(\d{1,2})(?:\.\d)?\s*(?:\+|plus)?\s*(?:(?:-|–|—|to)\s*\d{1,2}\s*\+?\s*)?"
    r"(?:years?|yrs?)\b(?!\s*old)")
_FRESHER_TEXT = re.compile(r"(?i)\b(freshers?|entry[- ]level|0\s*(?:-|–|to)\s*[12]\s*"
                           r"(?:years?|yrs?))\b")
_FRESHER_TITLE = re.compile(r"(?i)\b(freshers?|entry[- ]level|graduate|intern(ship)?|junior|"
                            r"jr\.?|trainee|associate)(?=\W|$)")
_TITLE_LEVELS = [   # checked in order; first match wins
    (re.compile(r"(?i)\b(distinguished|director|head|vice president|vp|avp|principal|"
                r"staff|architect|manager|lead|expert|advisor)\b"), 8.0),
    (re.compile(r"(?i)\b(senior|sr\.?|founding|l4|level 4)(?=\W|$)"), 5.0),
    (re.compile(r"(?i)\b(iii|l3|level 3)\b"), 4.0),
    (re.compile(r"(?i)\b(specialist)\b"), 3.0),
    (re.compile(r"(?i)\b(ii|l2|level 2|sde 2|engineer 2|scientist 2)\b"), 2.0),
]
# Text that asks for experience without a number: "We are looking for an experienced ...".
_EXPERIENCED = re.compile(
    r"(?i)\b(?:looking for|seeking|hiring|need)\s+(?:an?\s+)?(?:highly\s+)?"
    r"(?:experienced|seasoned|highly skilled)\b|\bdeep expertise\b|\bproven track record\b")
_INTERN_TITLE = re.compile(r"(?i)\bintern(ship)?\b")


def years_in_text(text: str) -> float | None:
    """Lowest plausible 'N years' requirement in a job text (1-20), else None."""
    found = [int(m.group(1)) for m in _YEARS.finditer(text or "")]
    found = [n for n in found if 1 <= n <= 20]
    return float(min(found)) if found else None


def job_years(title: str, text: str = "") -> float | None:
    """Estimated years of experience a job asks for; None if there's no signal."""
    stated = years_in_text(f"{title or ''} . {text or ''}")
    if stated is not None:
        return stated
    for pattern, years in _TITLE_LEVELS:          # "Senior Associate" is senior, so first
        if pattern.search(title or ""):
            return years
    if _FRESHER_TITLE.search(title or "") or _FRESHER_TEXT.search(text or ""):
        return 0.0
    if _EXPERIENCED.search(text or ""):
        return 3.0
    return None


def is_internship(title: str) -> bool:
    return bool(_INTERN_TITLE.search(title or ""))


# --- resume side ----------------------------------------------------------------
# Only phrasings that describe the person's experience: "with 2 years", "(18 months)",
# "for 3 years", "2+ years of experience". Not "cleaned 2 years of sales data".
_NUM = r"(\d{1,2}(?:\.\d)?)\s*\+?\s*"
_R_YEARS = re.compile(rf"(?i)(?:\bwith\s+|\bfor\s+|\(){_NUM}(?:years?|yrs?)\b"
                      rf"|\b{_NUM}(?:years?|yrs?)\s+(?:of\s+)?(?:[\w-]+\s+)?experience")
_R_MONTHS = re.compile(r"(?i)(?:\bwith\s+|\bfor\s+|\()(\d{1,2})\s*months?\b")


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*"
_NOW = r"(present|current|now|till date|today)"
# "Jul 2023 - Present", "Jun 2026 – Aug 2026", "since Mar 2023". Month names are required so
# that education years ("2022 - 2026") aren't counted as work.
_RANGE = re.compile(rf"(?i)\b{_MON}((?:19|20)\d\d)\s*(?:-|–|—|to)\s*(?:{_MON}((?:19|20)\d\d)|{_NOW})")
_SINCE = re.compile(rf"(?i)\bsince\s+{_MON}((?:19|20)\d\d)")


def _months_between(m1: str, y1: str, m2: str | None, y2: str | None, today: date) -> int:
    start = int(y1) * 12 + _MONTHS[m1[:3].lower()]
    end = (int(y2) * 12 + _MONTHS[m2[:3].lower()] if m2 and y2
           else today.year * 12 + today.month)
    return max(0, end - start + 1)


def years_from_dates(text: str, today: date | None = None) -> float:
    """Total months in work date ranges, as years. Overlapping jobs are rare on fresher
    and junior resumes, so ranges are simply added up."""
    today = today or date.today()
    months = sum(_months_between(m.group(1), m.group(2), m.group(3), m.group(4), today)
                 for m in _RANGE.finditer(text or ""))
    months += sum(_months_between(m.group(1), m.group(2), None, None, today)
                  for m in _SINCE.finditer(text or ""))
    return months / 12


def resume_years(text: str, today: date | None = None) -> float:
    """Experience in years: the larger of what the resume states ("2 years of experience",
    "(18 months)") and the total of its work date ranges; 0 for a fresher."""
    years = [float(m.group(1) or m.group(2)) for m in _R_YEARS.finditer(text or "")]
    years += [int(m.group(1)) / 12 for m in _R_MONTHS.finditer(text or "")]
    years.append(years_from_dates(text, today))
    years = [y for y in years if y <= 40]
    return round(max(years), 1)


# --- combining --------------------------------------------------------------------
SLACK = 1.0          # asking up to 1 year more than you have is fine
STEP = 0.15          # each further year costs 15% of the fit
FLOOR = 0.3


def level_factor(job: float | None, have: float) -> float:
    """Multiplier for the fit score (1 = no penalty)."""
    if job is None:
        return 1.0
    gap = job - have - SLACK
    return 1.0 if gap <= 0 else max(FLOOR, 1.0 - STEP * gap)


EXPERIENCE_CHOICES = {"Fresher (0 years)": 0.0, "About 1 year": 1.0, "About 2 years": 2.0,
                      "3-4 years": 3.5, "5+ years": 6.0}


def nearest_choice(years: float) -> str:
    return min(EXPERIENCE_CHOICES, key=lambda k: abs(EXPERIENCE_CHOICES[k] - years))
