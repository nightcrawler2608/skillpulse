"""Turn messy raw Adzuna job dicts into clean, uniform records."""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from datetime import datetime

# Different spellings / suburbs -> the one standard city name we use.
CITY_ALIASES: dict[str, str] = {
    "bangalore": "Bengaluru", "bengaluru": "Bengaluru", "bangalore urban": "Bengaluru",
    "hyderabad": "Hyderabad", "secunderabad": "Hyderabad",
    "pune": "Pune",
    "chennai": "Chennai",
    "mumbai": "Mumbai", "navi mumbai": "Mumbai", "thane": "Mumbai",
    "delhi": "Delhi NCR", "new delhi": "Delhi NCR", "gurgaon": "Delhi NCR",
    "gurugram": "Delhi NCR", "noida": "Delhi NCR", "greater noida": "Delhi NCR",
    "ghaziabad": "Delhi NCR", "faridabad": "Delhi NCR",
}

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


@dataclass
class CleanJob:
    source_job_id: str
    dedupe_hash: str
    title: str
    company: str | None
    city: str | None
    state: str | None
    category: str | None
    salary_min: float | None
    salary_max: float | None
    contract_type: str | None
    contract_time: str | None
    posted_at: datetime | None
    description: str | None
    url: str | None
    role_id: int | None = None   # filled in by the role mapper


MOJIBAKE_RE = re.compile(r"â[\x80-\x9f€]*[\x80-\x9f–—“”™]?")


def fix_mojibake(text: str) -> str:
    """Repair text whose UTF-8 bytes were decoded as Latin-1 somewhere upstream
    ("12 PM â\x80\x93 9 PM" -> "12 PM – 9 PM")."""
    if "â" not in text and "Ã" not in text:
        return text
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Bytes were partly lost: the usual culprit is an en dash, so use that.
        return MOJIBAKE_RE.sub("–", text)


def clean_text(text: str | None) -> str | None:
    """Remove HTML tags/entities, repair broken characters, squeeze whitespace."""
    if not text:
        return None
    text = fix_mojibake(html.unescape(TAG_RE.sub(" ", text)))
    text = SPACE_RE.sub(" ", text).strip()
    return text or None


def normalize_city(area: list[str] | None, display_name: str | None) -> tuple[str | None, str | None]:
    """Return (city, state). Adzuna 'area' looks like ['India', 'Karnataka', 'Bangalore']."""
    area = area or []
    state = area[1] if len(area) > 1 else None
    # Check most specific first, then fall back to the display name parts.
    candidates = list(reversed(area[1:]))
    if display_name:
        candidates += [p.strip() for p in display_name.split(",")]
    for name in candidates:
        city = CITY_ALIASES.get(name.lower())
        if city:
            return city, state
    # area = [country, state, city, ...]: only a 3rd level is a real city/town.
    most_specific = area[-1] if len(area) > 2 else None
    return most_specific, state


def make_dedupe_hash(title: str, company: str | None, city: str | None) -> str:
    """Same title + company + city = probably the same job reposted."""
    key = "|".join(SPACE_RE.sub(" ", (p or "").lower()).strip() for p in (title, company, city))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)  # Python 3.11+ understands the trailing "Z"
    except ValueError:
        return None


def to_number(value) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def clean_job(raw: dict) -> CleanJob | None:
    """Clean one raw job. Returns None if the job is unusable (no id or title)."""
    job_id = raw.get("id")
    title = clean_text(raw.get("title"))
    if not job_id or not title:
        return None

    location = raw.get("location") or {}
    city, state = normalize_city(location.get("area"), location.get("display_name"))
    company = clean_text((raw.get("company") or {}).get("display_name"))

    # Adzuna sometimes *estimates* salaries. We only keep real, advertised ones.
    predicted = str(raw.get("salary_is_predicted", "0")) == "1"
    salary_min = None if predicted else to_number(raw.get("salary_min"))
    salary_max = None if predicted else to_number(raw.get("salary_max"))

    return CleanJob(
        source_job_id=str(job_id),
        dedupe_hash=make_dedupe_hash(title, company, city),
        title=title,
        company=company,
        city=city,
        state=state,
        category=(raw.get("category") or {}).get("label"),
        salary_min=salary_min,
        salary_max=salary_max,
        contract_type=raw.get("contract_type"),
        contract_time=raw.get("contract_time"),
        posted_at=parse_date(raw.get("created")),
        description=clean_text(raw.get("description")),
        url=raw.get("redirect_url"),
    )
