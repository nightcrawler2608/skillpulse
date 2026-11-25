"""SkillPulse web app entry point.

Run:  streamlit run app/main.py
"""

import streamlit as st

import track
import ui

st.set_page_config(page_title="SkillPulse: what jobs want", page_icon="📈", layout="wide")
ui.inject_theme()

pages = [
    st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("views/market.py", title="Market dashboard", icon=":material/monitoring:"),
    st.Page("views/resume.py", title="Resume analyzer", icon=":material/description:"),
    st.Page("views/roles.py", title="Role explorer", icon=":material/category:"),
    st.Page("views/about.py", title="About", icon=":material/info:"),
]
page = st.navigation(pages, position="top")
track.event(f"view:{page.title}", once=True)
page.run()

# Adzuna's API terms ask apps that show its job data to credit it.
ui.show('<div style="text-align:center;margin:48px 0 8px;font-size:12px">'
        'Job data: <a href="https://www.adzuna.in/" target="_blank" rel="noopener">'
        "Jobs by Adzuna</a> · SkillPulse is a student project, not affiliated with Adzuna.</div>")
