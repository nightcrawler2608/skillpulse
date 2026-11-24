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
                r"staff|architect|manager|lead|expert)\b"), 8.0),
    (re.compile(r"(?i)\b(senior|sr\.?)(?=\W)"), 5.0),
    (re.compile(r"(?i)\b(iii|l3|level 3)\b"), 4.0),
    (re.compile(r"(?i)\b(ii|l2|level 2|sde 2|engineer 2|scientist 2)\b"), 2.0),
]


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
    return None


# --- resume side ----------------------------------------------------------------
# Only phrasings that describe the person's experience: "with 2 years", "(18 months)",
# "for 3 years", "2+ years of experience". Not "cleaned 2 years of sales data".
_NUM = r"(\d{1,2}(?:\.\d)?)\s*\+?\s*"
_R_YEARS = re.compile(rf"(?i)(?:\bwith\s+|\bfor\s+|\(){_NUM}(?:years?|yrs?)\b"
                      rf"|\b{_NUM}(?:years?|yrs?)\s+(?:of\s+)?(?:[\w-]+\s+)?experience")
_R_MONTHS = re.compile(r"(?i)(?:\bwith\s+|\bfor\s+|\()(\d{1,2})\s*months?\b")


def resume_years(text: str) -> float:
    """Largest stated experience in years (months / 12); 0 for a fresher.
    Date ranges ("2023 - Present") aren't read; the app lets users correct the estimate."""
    years = [float(m.group(1) or m.group(2)) for m in _R_YEARS.finditer(text or "")]
    years += [int(m.group(1)) / 12 for m in _R_MONTHS.finditer(text or "")]
    years = [y for y in years if y <= 40]
    return round(max(years), 1) if years else 0.0


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
