"""SkillPulse web app entry point.

Run:  streamlit run app/main.py
"""

import contextlib
import os
import sys
from datetime import UTC, datetime, timedelta
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

import data  # needs src/ on the path first
import track
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

# Database reachable? A friendly message beats a crash page.
try:
    status = data.status()
except Exception:  # noqa: BLE001 - any connection problem looks the same to a visitor
    st.error("SkillPulse can't reach its database right now. Please try again in a minute.",
             icon=":material/cloud_off:")
    st.stop()

# Honest freshness: say so if the nightly update has stopped.
if status.last_run is not None:
    age = datetime.now(UTC) - status.last_run
    if age > timedelta(hours=36):
        st.warning(f"Heads up: job data was last updated {age.days} day(s) ago, so the numbers "
                   "may be a little out of date.", icon=":material/schedule:")

track.event(f"view:{page.title}", once=True)
page.run()

# One footer for every page. Adzuna's API terms ask apps that show its job data to credit it.
ui.rule()
ui.show('<div class="sp-foot">We never store resumes · job data refreshed nightly · '
        '<a href="https://www.adzuna.in/" target="_blank" rel="noopener">Jobs by Adzuna</a><br>'
        "<b>SkillPulse</b>: a final-year data science project, not affiliated with Adzuna.</div>")
