"""Home page: hero, live trending skills ribbon, what SkillPulse does."""

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
  {ui.mascot("lensy", 190, -10, bob=True)}{ui.mascot("chartie", 240, 0, bob=True)}{ui.mascot("resumo", 190, 9, bob=True)}
</div>
""")

ui.show(f"""
<div style="max-width:620px;margin:26px auto 0;text-align:center">
  <div class="sp-h" style="font-size:clamp(26px,4vw,38px)">Know what jobs want.</div>
  <div class="sp-h" style="font-size:clamp(22px,3.4vw,32px);margin:6px 0 14px">Close the gap BEFORE you apply.</div>
  <p style="font-size:14px;color:#1C1C1C">Every night SkillPulse reads fresh job postings from across India and
  works out which skills employers are actually asking for, by role and city.</p>
  <p class="sp-cap">So far: {status.total_jobs:,} postings collected over {status.days} days ·
  data via the Adzuna API</p>
</div>
""")

c1, c2, c3 = st.columns([1, 1.2, 1])
with c2:
    st.page_link("views/resume.py", label="Check my resume →", use_container_width=True)
    st.page_link("views/market.py", label="See the market dashboard →", use_container_width=True)

ui.rule()

left, right = st.columns([1, 1.3], vertical_alignment="center")
with left:
    ui.show(f'<div style="display:flex;justify-content:center">{ui.mascot("baseo", 260, -6)}</div>')
with right:
    ui.show("""
    <div class="sp-cap" style="text-align:center;margin-bottom:6px">What you get, free:</div>
    <ul class="sp-list">
      <li>Live Skill Rankings</li><li>Resume Match Score</li><li>Missing Skills, Ranked</li>
      <li>Jobs That Fit You</li><li>Week-by-Week Learning Plan</li><li>Kinds of Jobs per Role</li>
    </ul>""")
    st.page_link("views/roles.py", label="Explore kinds of jobs →", use_container_width=True)

ui.rule()
ui.show("""
<div style="text-align:center;font-size:12.5px;color:#1C1C1C;margin-bottom:30px">
  We never store resumes. Job data refreshed nightly from the Adzuna API.<br>
  <b>SkillPulse: a final-year data science project</b></div>""")
