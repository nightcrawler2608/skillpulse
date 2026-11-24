"""Hand-labelling tool: mark which skills each sample job really asks for.

Run:  streamlit run app/labeler.py

Rules for honest labels:
- You see the job text only, NOT what the extractor found, so the extractor's
  answers can't influence you.
- Pick every skill the job asks for or clearly mentions as part of the work.
  Don't pick skills only mentioned in the company blurb ("we are an AI company").
- If a skill is missing from the list, type it in "Other skills".
"""

from __future__ import annotations

import csv
import os
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from skillpulse.config import PROJECT_ROOT
from skillpulse.nlp.taxonomy import default_skills

SAMPLE = PROJECT_ROOT / "data" / "eval" / "sample_jobs.csv"
LABELS = PROJECT_ROOT / "data" / "eval" / "labels.csv"
FIELDS = ["job_id", "skills", "other", "labeled_at", "annotator"]

st.set_page_config(page_title="SkillPulse labeller", layout="wide")


@st.cache_data
def load_sample() -> list[dict]:
    with open(SAMPLE, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_labels() -> dict[str, dict]:
    if not LABELS.exists():
        return {}
    with open(LABELS, encoding="utf-8", newline="") as f:
        return {r["job_id"]: r for r in csv.DictReader(f)}


def save_labels(labels: dict[str, dict]) -> None:
    tmp = Path(str(LABELS) + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in sorted(labels.values(), key=lambda r: int(r["job_id"])):
            w.writerow(row)
    os.replace(tmp, LABELS)   # write-then-rename, so a crash never corrupts the file


if not SAMPLE.exists():
    st.error("No sample yet. Run:  python scripts/make_eval_sample.py")
    st.stop()

jobs = load_sample()
labels = load_labels()
skill_names = sorted((s.name for s in default_skills()), key=str.lower)

done = sum(1 for j in jobs if j["job_id"] in labels)
st.progress(done / len(jobs), text=f"{done} / {len(jobs)} jobs labelled")

if "idx" not in st.session_state:
    st.session_state.idx = next((i for i, j in enumerate(jobs) if j["job_id"] not in labels), 0)

with st.sidebar:
    st.header("Jump to job")
    st.session_state.idx = st.number_input("Job #", 1, len(jobs), st.session_state.idx + 1) - 1
    st.caption("✓ = labelled")
    st.markdown(" ".join("✓" if j["job_id"] in labels else "·" for j in jobs))

job = jobs[st.session_state.idx]
existing = labels.get(job["job_id"])

st.caption(f"Job {st.session_state.idx + 1} of {len(jobs)} · role: {job['role']} · id {job['job_id']}")
st.subheader(job["title"])
st.markdown(f"> {job['text']}")

with st.form(key=f"form-{job['job_id']}"):
    chosen = st.multiselect(
        "Skills this job asks for (type to search)", skill_names,
        default=[s for s in (existing["skills"].split("|") if existing and existing["skills"] else [])
                 if s in skill_names],
    )
    other = st.text_input("Other skills not in the list (comma separated)",
                          value=existing["other"] if existing else "")
    saved = st.form_submit_button("Save & next →", type="primary")

if saved:
    labels[job["job_id"]] = {
        "job_id": job["job_id"],
        "skills": "|".join(sorted(chosen)),
        "other": other.strip(),
        "labeled_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "annotator": "human",
    }
    save_labels(labels)
    nxt = next((i for i, j in enumerate(jobs) if j["job_id"] not in labels), None)
    st.session_state.idx = nxt if nxt is not None else st.session_state.idx
    st.rerun()

if done == len(jobs):
    st.success("All jobs labelled! Now run:  python scripts/evaluate_extraction.py")
