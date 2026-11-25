"""Home page: hero, live trending skills ribbon, how it works, and where to start."""

from zoneinfo import ZoneInfo

import streamlit as st

import data
import ui

status = data.status()
trend = data.trending(days=7, n=8)
roles = data.roles()

updated = (status.last_run.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y, %I:%M %p")
           if status.last_run else "not yet")
items = [(s.upper(), f"{j} JOBS") for s, j in zip(trend["skill"], trend["jobs"])]
items += [("UPDATED NIGHTLY", ""), ("CHECK WHAT JOBS WANT", "")]

ui.show(f"""
<div class="sp-hero">
  <div class="sp-meta"><span>Updated {updated} IST</span><span>India · 7 cities · {len(roles)} roles</span></div>
  <div class="sp-mega" role="heading" aria-level="1">Skill<br>Pulse</div>
  {ui.ribbon(items)}
</div>
<div class="sp-mascots">
  {ui.mascot("lensy", 120, -10, bob=True)}{ui.mascot("chartie", 160, 0, bob=True)}{ui.mascot("resumo", 120, 9, bob=True)}
</div>
""")

ui.show("""
<div style="max-width:760px;margin:10px auto 0;text-align:center">
  <div class="sp-h" style="font-size:clamp(26px,4vw,38px)">Know what jobs want.</div>
  <div class="sp-h" style="font-size:clamp(22px,3.4vw,32px);margin:4px 0 10px">Close the gap BEFORE you apply.</div>
  <p style="font-size:14px;color:#1C1C1C;margin-bottom:4px">Every night SkillPulse reads fresh job postings
  from across India and works out which skills employers are actually asking for, by role and city.</p>
</div>
""")

_, mid, _ = st.columns([1, 1.2, 1])
with mid:
    if st.button("Check my resume →", type="primary", use_container_width=True, key="cta_resume"):
        st.switch_page("views/resume.py")
    st.page_link("views/market.py", label="See the market dashboard →", use_container_width=True)
    st.caption(f"Free · no sign-up · your resume is never stored · {status.total_jobs:,} postings "
               f"collected so far")

ui.rule()
ui.section("How it works", "Three steps, two minutes", "")
steps = [
    ("Step 1", "Add your resume",
     "Upload a PDF or paste the text, pick the job you want. It's read in memory and never saved.",
     "views/resume.py", "Start here →"),
    ("Step 2", "See your gaps",
     ("A match score against real postings, the skills to learn next (ranked by how much they "
     "raise your score) and which role fits you best."),
     "views/market.py", "See what's in demand →"),
    ("Step 3", "Plan and apply",
     ("A week-by-week learning plan with free resources, plus live jobs that fit your level "
     "and skills."),
     "views/roles.py", "Explore kinds of jobs →"),
]
for col, (tag, title, text, page, link) in zip(st.columns(3, gap="medium"), steps, strict=True):
    with col:
        st.html(ui.stat(tag, title, text))
        st.page_link(page, label=link, use_container_width=True)
