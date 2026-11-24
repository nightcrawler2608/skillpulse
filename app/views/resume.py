"""Resume Analyzer: match score, ranked missing skills, and live jobs that fit.

Privacy: the resume is read in memory only. Its text, skills and embedding live in
this browser session (st.session_state) and disappear when the tab closes. Nothing
is cached across users, written to disk, or saved to the database.
"""

from datetime import UTC, datetime

import streamlit as st

import data
import ui
from skillpulse.analytics.market import MIN_JOBS
from skillpulse.config import CITIES
from skillpulse.db.connection import get_connection
from skillpulse.matching.embedder import embed_resume
from skillpulse.matching.recommender import recommend
from skillpulse.matching.resume_parser import ResumeError, clean_text, pdf_to_text
from skillpulse.matching.resume_skills import resume_skills
from skillpulse.matching.scorer import score_resume
from skillpulse.nlp.extractor import DictionaryExtractor
from skillpulse.nlp.taxonomy import default_skills

DEMAND_DAYS = 90   # use all recent postings for the role's skill weights


@st.cache_resource(show_spinner=False)
def extractor():
    return DictionaryExtractor()


@st.cache_resource(show_spinner="Loading the language model (first time only)...")
def warm_model():
    embed_resume("warm up")   # loads all-MiniLM-L6-v2 once per server
    return True


roles = data.roles()
role_names = sorted(roles)
ss = st.session_state

ui.section("Resume analyzer · 100% private, nothing is saved", "Get your match score",
           "Upload your resume, pick the job you want, and see how you stack up against "
           "real postings.")

left, mid, right = st.columns([1, 2.2, 1])
with left:
    st.html(f'<div style="margin-top:120px">{ui.mascot("resumo", 170, -10)}</div>')
with right:
    st.html(f'<div style="margin-top:40px">{ui.mascot("lensy", 170, 12)}</div>')
with mid, ui.card("form"), st.form("resume-form", border=False):
    pdf = st.file_uploader("Your resume (PDF, up to 5 MB)", type=["pdf"])
    pasted = st.text_area("…or paste your resume text", height=120,
                          placeholder="Skills, projects, experience…")
    c1, c2 = st.columns(2)
    default_role = role_names.index("Data Analyst") if "Data Analyst" in role_names else 0
    role = c1.selectbox("Target role", role_names, index=default_role)
    city_label = c2.selectbox("City (for job matches)",
                              ["Any city"] + [c.name for c in CITIES if c.adzuna_where])
    go = st.form_submit_button("Analyze my resume", type="primary", use_container_width=True)
    st.caption("Your resume is read in memory and never stored. Close the tab and it's gone.")

if go:
    try:
        if pdf is not None:
            text = pdf_to_text(pdf.getvalue())
        elif len(pasted.strip()) >= 100:
            text = clean_text(pasted)
        else:
            raise ResumeError("Please upload a PDF or paste at least a few lines of your resume.")
    except ResumeError as e:
        st.error(str(e), icon=":material/error:")
        st.stop()
    with st.spinner("Reading your resume and comparing it with live jobs…"):
        warm_model()
        ss.resume = {
            "skills": sorted(resume_skills(text, extractor())),
            "vec": embed_resume(text),
            "role": role,
            "city": None if city_label == "Any city" else city_label,
            "at": datetime.now(UTC),
        }
    ss.pop("edited_skills", None)

if "resume" not in ss:
    st.stop()

# ---------------------------------------------------------------------- results
r = ss.resume
role_id = roles[r["role"]]
demand, postings = data.top_skills(role_id, "ALL", DEMAND_DAYS, 30)

st.write("")
with ui.card("found"):
    st.markdown("#### Skills we found")
    st.caption("Add any we missed (or remove wrong ones). Your score updates instantly.")
    all_names = sorted((s.name for s in default_skills()), key=str.lower)
    skills = set(st.multiselect("Your skills", all_names, default=r["skills"],
                                key="edited_skills", label_visibility="collapsed"))

result = score_resume(skills, demand, postings)
if postings < MIN_JOBS:
    st.warning(f"Only {postings} {r['role']} postings so far, so this score is rough.",
               icon=":material/info:")

st.write("")
a, b = st.columns([1, 2.2], gap="medium")
with a, ui.card("score"):
    st.markdown("#### Your match")
    st.html(ui.score_ring(result.score))
    verdict = ("Strong match!" if result.score >= 75 else "Almost there!" if result.score >= 50
               else "Getting there" if result.score >= 25 else "Early days, and that's fine")
    st.html(f'<div class="sp-h" style="font-size:18px">{verdict}</div>')
    st.caption(f"For {r['role']}, weighted by how often each skill appears in {postings} "
               "live postings.")
with b, ui.card("skills"):
    st.markdown("#### Skills you have")
    have = [g.skill for g in result.have]
    st.html(ui.chips(have) if have else '<p class="sp-cap">None of the top skills found yet.</p>')
    st.markdown("#### Learn these next")
    st.caption("Ranked by how many employers ask for them · points = how much your score rises")
    st.html(ui.gap_chips(result.missing[:8]))
    if result.missing:
        g = result.missing[0]
        st.caption(f"Adding **{g.skill}** alone would raise your score to about "
                   f"**{min(100, result.score + g.gain):.0f}**.")

# ---------------------------------------------------------------------- jobs
st.write("")
ui.section("Live job matches", "Jobs that fit you",
           f"{r['role']} postings{' in ' + r['city'] if r['city'] else ''}, ranked by how close "
           "they are to your resume in meaning and in skills.")
with get_connection() as conn:
    jobs = recommend(conn, r["vec"], skills, role_id, r["city"], top=9)
if jobs.empty:
    st.info("No active postings for this role and city yet. Try 'Any city'.")
else:
    cols = st.columns(3, gap="medium")
    for i, j in enumerate(jobs.itertuples()):
        posted = f"posted {j.posted_at:%d %b}" if j.posted_at else ""
        # missing values come back from pandas as NaN (a float), so keep real text only
        meta = " · ".join(x for x in [j.company, j.city, posted] if isinstance(x, str) and x)
        cols[i % 3].html(ui.job_card(j.title, meta, j.fit, j.matched, j.to_learn, j.url))
    st.caption("Fit = 50% meaning similarity (AI embeddings of your resume vs. the job) + 50% "
               "skill match (share of the job's listed skills you have, pulled toward 50% when "
               "a job lists only a few). Links open the original ad on Adzuna.")
