"""SkillPulse web app entry point.

Run:  streamlit run app/main.py
"""

import streamlit as st

import ui

st.set_page_config(page_title="SkillPulse: what jobs want", page_icon="📈", layout="wide")
ui.inject_theme()

pages = [
    st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("views/market.py", title="Market dashboard", icon=":material/monitoring:"),
    st.Page("views/resume.py", title="Resume analyzer", icon=":material/description:"),
]
st.navigation(pages, position="top").run()
