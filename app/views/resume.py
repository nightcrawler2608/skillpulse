"""Resume Analyzer: match score, ranked missing skills, and live jobs that fit.

Privacy: the resume is read in memory only. Its text, skills and embedding live in
this browser session (st.session_state) and disappear when the tab closes. Nothing
is cached across users, written to disk, or saved to the database.
"""

import html
from datetime import UTC, datetime

import streamlit as st

import data
import track
import ui
from skillpulse.analytics.market import MIN_JOBS
from skillpulse.config import CITIES
from skillpulse.db.connection import get_connection
from skillpulse.llm.planner import make_plan
from skillpulse.matching.embedder import embed_resume
from skillpulse.matching.recommender import recommend
from skillpulse.matching.resume_parser import ResumeError, clean_text, pdf_to_text
from skillpulse.matching.resume_skills import resume_skills
from skillpulse.matching.scorer import MIN_POSTINGS_FOR_RANKING, rank_roles, score_resume
from skillpulse.matching.seniority import EXPERIENCE_CHOICES, nearest_choice, resume_years
from skillpulse.nlp.extractor import DictionaryExtractor
from skillpulse.nlp.taxonomy import default_skills

DEMAND_DAYS = 90   # use all recent postings for the role's skill weights


@st.cache_resource(show_spinner=False)
def soft_skill_names() -> frozenset[str]:
    return frozenset(s.name for s in default_skills() if s.category == "soft")


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
            "years": resume_years(text),
            "role": role,
            "city": None if city_label == "Any city" else city_label,
            "at": datetime.now(UTC),
        }
    ss.pop("edited_skills", None)
    ss.pop("experience", None)
    ss.pop("plan", None)
    track.event("analyze", roles[role])

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
    choices = list(EXPERIENCE_CHOICES)
    experience = st.radio("Your work experience (we guessed from your resume, fix it if wrong)",
                          choices, index=choices.index(nearest_choice(r.get("years", 0.0))),
                          key="experience", horizontal=True)
    have_years = EXPERIENCE_CHOICES[experience]

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
    track.thumbs("score", "score", role_id, label="Does this score feel fair?")
with b, ui.card("skills"):
    st.markdown("#### Skills you have")
    have = [g.skill for g in result.have]
    st.html(ui.chips(have) if have else '<p class="sp-cap">None of the top skills found yet.</p>')
    st.markdown("#### Learn these next")
    st.caption("Ranked by how many employers ask for them · points = how much your score rises")
    soft_names = soft_skill_names()
    learnable = [g for g in result.missing if g.skill not in soft_names]
    soft = [g.skill for g in result.missing if g.skill in soft_names]
    st.html(ui.gap_chips(learnable[:8]))
    if soft:
        st.html(f'<div class="sp-soft">Also asked for: <b>{html.escape(", ".join(soft[:4]))}</b>. '
                "Show these through projects, internships and interviews rather than "
                "courses.</div>")
    if learnable:
        g = learnable[0]
        st.caption(f"Adding **{g.skill}** alone would raise your score to about "
                   f"**{min(100, result.score + g.gain):.0f}**.")

# ---------------------------------------------------------------------- best-fit role
fits = rank_roles(skills, {name: data.top_skills(rid, "ALL", DEMAND_DAYS, 30)
                           for name, rid in roles.items()}, skip=soft_names)
if fits:
    st.write("")
    with ui.card("fit"):
        st.markdown("#### Which role fits you best?")
        st.caption("The same score for every role, from the same live postings. Roles with "
                   f"fewer than {MIN_POSTINGS_FOR_RANKING} postings aren't ranked yet.")
        st.html(ui.role_bars(fits, r["role"]))
        better = [f for f in fits if f.role != r["role"] and f.score > result.score][:3]
        if better:
            st.caption("Check yourself against a role that fits better:")
            for col, f in zip(st.columns(len(better)), better, strict=True):
                if col.button(f"Try {f.role}", key=f"try_{f.role}", use_container_width=True):
                    ss.resume["role"] = f.role
                    ss.pop("plan", None)
                    track.event("switch_role", roles[f.role])
                    st.rerun()

# ---------------------------------------------------------------------- learning plan
@st.cache_resource
def plan_store() -> dict:
    return {}


MAX_AI_PLANS = 5   # per visitor session: keeps the free Gemini quota for everyone


def cached_plan(missing: tuple[str, ...], role: str, have: tuple[str, ...], years: float,
                weeks: int, hours: int, use_llm: bool = True):
    """Reuse Gemini-written plans across users (the key is only skill names and numbers),
    saving free-tier quota. Template plans aren't stored, so a brief AI outage isn't
    remembered: the next click tries Gemini again."""
    store, key = plan_store(), (missing, role, have, years, weeks, hours)
    if key in store:
        return store[key]
    plan = make_plan(list(missing), role, list(have), years, weeks, hours,
                     use_llm=None if use_llm else False)
    if plan.source == "gemini":
        if len(store) >= 500:
            store.pop(next(iter(store)))        # forget the oldest
        store[key] = plan
    return plan


st.write("")
ui.section("Learning plan", "Your next weeks, planned",
           "Built from the skills above, most valuable first. Free resources only.")
with ui.card("plan"):
    p1, p2, p3 = st.columns([1, 1, 1.2], vertical_alignment="bottom")
    plan_weeks = p1.selectbox("Plan length", [4, 6, 8, 12], index=2,
                              format_func=lambda w: f"{w} weeks")
    hours = p2.selectbox("Time you can give", [4, 8, 12, 16], index=1,
                         format_func=lambda h: f"{h} hours / week")
    make = p3.button("Make my plan", type="primary", use_container_width=True)
    st.caption("Only skill names, the role and your experience level are sent to Google's "
               "Gemini to word the plan. Never your resume text. If AI is unavailable, a "
               "standard template is used.")
plan_key = (tuple(g.skill for g in result.missing), r["role"], tuple(sorted(skills)),
            have_years, plan_weeks, hours)
if make:
    ai_left = ss.get("ai_plans", 0) < MAX_AI_PLANS
    with st.spinner("Planning your weeks…"):
        new_plan = cached_plan(*plan_key, use_llm=ai_left)
    if ai_left:
        ss.ai_plans = ss.get("ai_plans", 0) + 1
    elif new_plan.source == "template":
        new_plan.note = (f"You've made {MAX_AI_PLANS} AI-worded plans in this visit, so this one "
                         "uses the standard template (it keeps the free AI quota fair for all).")
    ss.plan = (plan_key, new_plan)
    track.event(f"plan:{new_plan.source}", role_id)
if ss.get("plan") and ss.plan[0] == plan_key:
    plan = ss.plan[1]
    if plan.note:
        st.info(plan.note, icon=":material/info:")
    if plan.items:
        cols = st.columns(2, gap="medium")
        for i, item in enumerate(plan.items):
            cols[i % 2].html(ui.plan_week(item))
        foot = ("Worded by Gemini; schedule and links chosen by SkillPulse." if
                plan.source == "gemini" else "Standard template; schedule and links chosen by "
                "SkillPulse.")
        if plan.skipped:
            foot += f" Didn't fit in {plan_weeks} weeks: {', '.join(plan.skipped[:5])}."
        st.caption(foot)
        track.thumbs("plan", f"plan_{abs(hash(plan_key))}", role_id,
                     label="Is this plan useful?")
elif ss.get("plan"):
    st.caption("Your skills or choices changed. Press **Make my plan** again to update it.")

# ---------------------------------------------------------------------- jobs
st.write("")
ui.section("Live job matches", "Jobs that fit you",
           f"{r['role']} postings{' in ' + r['city'] if r['city'] else ''}, ranked by how close "
           "they are to your resume in meaning and in skills.")
at_my_level = st.toggle(
    "Only jobs at my level", value=have_years < 1, key="level_only",
    help="Hides jobs that clearly ask for more than about a year beyond your experience "
         "(e.g. Senior, Lead, '5+ years'). Jobs that don't say are still shown.")
with get_connection() as conn:
    jobs = recommend(conn, r["vec"], skills, role_id, r["city"], top=40, have_years=have_years,
                     stack_check=True)
if at_my_level and not jobs.empty:
    ask = jobs["job_years"]
    jobs = jobs[ask.isna() | (ask <= have_years + 1)]
jobs = jobs.head(9)
if jobs.empty:
    st.info("No active postings for this role and city yet. Try 'Any city'.")
else:
    cols = st.columns(3, gap="medium")
    for i, j in enumerate(jobs.itertuples()):
        posted = f"posted {j.posted_at:%d %b}" if j.posted_at else ""
        level = ("" if j.job_years != j.job_years or j.job_years is None   # NaN = unknown
                 else "fresher-friendly" if j.job_years == 0 else f"asks ~{j.job_years:g}+ yrs")
        # missing values come back from pandas as NaN (a float), so keep real text only
        meta = " · ".join(x for x in [j.company, j.city, level, posted]
                          if isinstance(x, str) and x)
        with cols[i % 3]:
            st.html(ui.job_card(j.title, meta, j.fit, j.matched, j.to_learn, j.url))
            track.thumbs("job", f"job_{j.id}", role_id, int(j.id))
    st.caption("Fit = 50% meaning similarity (AI embeddings of your resume vs. the job) + 50% "
               "skill match (share of the job's listed skills you have, pulled toward 50% when "
               "a job lists only a few), lowered for jobs that ask for much more experience "
               "than you picked above. Links open the original ad on Adzuna. Use 👍/👎 under a job "
               "to tell us if it's a good match.")
