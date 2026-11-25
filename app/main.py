"""SkillPulse web app entry point.

Run:  streamlit run app/main.py
"""

import contextlib
import os
import sys
from pathlib import Path

import streamlit as st

# Hosted copies (Streamlit Community Cloud) run straight from the repo without installing
# our package, so make src/ importable.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Secrets pasted into the host's Secrets box arrive in st.secrets; our code reads environment
# variables, so copy plain top-level values across (never overwriting real ones).
with contextlib.suppress(Exception):          # no secrets file locally is normal
    for key, value in st.secrets.items():
        if isinstance(value, str) and key not in os.environ:
            os.environ[key] = value

import track  # needs src/ on the path first
import ui

st.set_page_config(page_title="SkillPulse: what jobs want", page_icon="📈", layout="wide")
ui.inject_theme()

pages = [
    st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    # short names so all five fit in the top bar on an iPad
    st.Page("views/market.py", title="Market", icon=":material/monitoring:"),
    st.Page("views/resume.py", title="Resume check", icon=":material/description:"),
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
