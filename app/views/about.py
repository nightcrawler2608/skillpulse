"""About: what SkillPulse does, how it works, how accurate it is, and what happens to your data."""

import streamlit as st

import data
import ui

status = data.status()

ui.section("About & methodology", "How SkillPulse works",
           "A final-year data science project: live job data, open methods, honest numbers.")

c1, c2, c3 = st.columns(3)
c1.html(ui.stat("Postings collected", f"{status.total_jobs:,}",
                "Indian job ads from Adzuna's official API, refreshed every night"))
c2.html(ui.stat("Days of data", f"{status.days}",
                f"From {status.first_day:%d %b %Y}" if status.first_day else "Collecting"))
c3.html(ui.stat("Last update", f"{status.last_run:%d %b, %H:%M} UTC" if status.last_run else "—",
                "When the nightly pipeline last finished"))

st.write("")
left, right = st.columns(2, gap="large")
with left:
    st.markdown("### The pipeline (every night, free)")
    st.markdown(
        "1. **Collect:** Adzuna's API is searched for 10 roles × 7 cities, plus extra job titles "
        "(e.g. *react developer*). GitHub Actions runs it at 2 AM IST.\n"
        "2. **Clean:** HTML and broken characters fixed, cities normalised, duplicates removed "
        "(same ad id, or same title + company + city).\n"
        "3. **Role:** each title is mapped to one of 10 roles by keywords; titles we can't place "
        "are left out rather than guessed.\n"
        "4. **Skills:** a dictionary of 249 skills with alternative spellings finds skills in "
        "each ad (*Java* ≠ *JavaScript*, *R* only in safe contexts).\n"
        "5. **Aggregate & embed:** daily skill counts per role and city; each ad gets a 384-number "
        "*embedding* (all-MiniLM-L6-v2) that captures its meaning.")
    st.markdown("### Your resume")
    st.markdown(
        "- **Match score:** share of the role's 30 most-asked skills you have, each weighted by "
        "how many postings ask for it.\n"
        "- **Job matches:** the 100 postings closest in meaning (pgvector), re-ranked by 50% "
        "meaning + 50% skill overlap, lowered for jobs asking far more experience than you have "
        "or a tech stack you don't use.\n"
        "- **Learning plan:** our code picks the skills and weeks; Google's Gemini only words "
        "the tasks; links are hand-checked. A template is used when AI is unavailable.\n"
        "- **Role explorer:** KMeans clustering of each role's job skill lists.")
with right:
    st.markdown("### How accurate is it?")
    st.markdown(
        "**Finding skills in job ads**, checked on 90 hand-labelled ads that were set aside "
        "before tuning:\n\n"
        "| Precision | Recall | F1 |\n|---|---|---|\n| 0.94 | 0.86 | 0.90 |\n\n"
        "*Precision:* of the skills we report, 94% are really there. *Recall:* we find 86% of "
        "the skills that are there.\n\n"
        "**Job matches (trial):** on 20 made-up resumes kept aside for testing, about **4 of the "
        "top 5** jobs were judged relevant (Precision@5 = 0.80, up from 0.48 before adding the "
        "experience-level step). Judged blind, but the resumes and judgments are synthetic; a "
        "test with real users is the next step, and your 👍/👎 feed into it.")
    st.markdown("### Your privacy")
    st.html(
        '<div class="sp-note"><b>Your resume is never stored.</b> It is read in memory, used '
        "to compute your score and matches, and gone when you close the tab: not written to "
        "disk, not saved in the database, not cached for other users.<br><br>"
        "<b>What is sent elsewhere:</b> if you make a learning plan, only skill names, the role, "
        "your experience level and hours per week go to Google's Gemini. Never resume text."
        "<br><br><b>What we count:</b> anonymous events (e.g. \"a resume was analysed for Data "
        "Analyst\", a 👍 on a job) tied to a random ID that lasts one browser tab. No cookies, "
        "no names, no IP addresses.</div>")
    st.markdown("### Limits to keep in mind")
    st.markdown(
        "- Adzuna shares only the first ~500 characters of each ad, so some skills are missed.\n"
        "- About 3 in 10 ads list no recognisable skill.\n"
        "- Salaries appear in few ads, so salary figures are shown only with 8+ postings.\n"
        "- Rising/falling skills need 4 weeks of data before they appear.")

st.write("")
st.html('<div class="sp-cap" style="text-align:center">Built with Python, PostgreSQL + pgvector '
        "(Neon), Streamlit, scikit-learn, sentence-transformers and Gemini, at ₹0 cost. "
        'Source code: <a href="https://github.com/nightcrawler2608/skillpulse" target="_blank" '
        'rel="noopener">GitHub</a>.</div>')
