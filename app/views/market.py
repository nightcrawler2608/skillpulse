"""Market dashboard: which skills employers ask for, by role, city and time."""

from datetime import timedelta

import streamlit as st

import data
import ui
from skillpulse.analytics.market import ALL, MIN_JOBS, MOVER_WINDOW
from skillpulse.config import CITIES

status = data.status()
roles = data.roles()

ui.section(
    f"Market dashboard · {status.first_day:%d %b} – {status.last_day:%d %b %Y}"
    if status.last_day else "Market dashboard",
    "The market, right now",
    "Pick a role and a city. Numbers come from real postings collected every night.",
)

# ------------------------------------------------------------------ filters
role_names = sorted(roles)
default_role = "Data Analyst" if "Data Analyst" in roles else role_names[0]
role = st.pills("Role", role_names, default=default_role, key="role") or default_role
f1, f2 = st.columns(2)
city_label = f1.selectbox("City", [c.name for c in CITIES][::-1], index=0,
                          help="'All India' includes every location, also cities we don't list.")
city = ALL if city_label == "All India" else city_label
days = f2.segmented_control("Time window", [7, 30, 90], default=30,
                            format_func=lambda d: f"Last {d} days", key="days") or 30
role_id = roles[role]

top, total = data.top_skills(role_id, city, days, 15)

# ------------------------------------------------------------------ headline stats
sal = data.salary(role_id, city, days)
c1, c2, c3 = st.columns(3)
c1.html(ui.stat("Postings analysed", f"{total:,}",
                f"{role} postings in {city_label} that list skills, last {days} days"))
if not top.empty:
    t = top.iloc[0]
    c2.html(ui.stat("Most asked-for skill", t.skill,
                    f"In <b>{t.share * 100:.0f}%</b> of these postings ({t.jobs} of {total})"))
else:
    c2.html(ui.stat("Most asked-for skill", "—", "No postings yet for this choice"))
if "median" in sal:
    c3.html(ui.stat("Advertised salary", f"₹{sal['median']:.1f} LPA",
                    f"Median · middle half ₹{sal['p25']:.1f}–{sal['p75']:.1f} LPA · "
                    f"from {sal['n']} postings that list pay"))
else:
    c3.html(ui.stat("Advertised salary", "Not enough data",
                    f"Only {sal['n']} postings here list a salary. Most Indian job ads don't."))

if 0 < total < MIN_JOBS:
    st.warning(f"Small sample: only {total} postings. Treat these percentages as rough; "
               "try 'All India' or a longer time window.", icon=":material/info:")

st.write("")
left, right = st.columns([1.05, 1], gap="medium")

# ------------------------------------------------------------------ top skills
with left, ui.card("top"):
    st.markdown("#### Top skills")
    st.caption(f"% of {role} postings that mention each skill · hover for counts")
    if top.empty:
        st.info("No postings for this role, city and window yet.")
    else:
        st.plotly_chart(ui.bar_chart(top.skill.tolist(), top.share.tolist(), top.jobs.tolist(),
                                     total), config=ui.CHART_CONFIG, use_container_width=True)

# ------------------------------------------------------------------ trend
with right, ui.card("trend"):
    st.markdown("#### Demand over time")
    freq = "D" if status.days < 21 else "W"
    st.caption(f"{'Daily' if freq == 'D' else 'Weekly'} % of postings mentioning the skill")
    options = top.skill.tolist()
    picked = st.multiselect("Compare skills (up to 3)", options, default=options[:3],
                            max_selections=3, key=f"trend-{role}-{city}") if options else []
    if picked:
        tr = data.trend(role_id, city, tuple(picked), days, freq)
        st.plotly_chart(ui.line_chart(tr, picked), config=ui.CHART_CONFIG,
                        use_container_width=True)
    if status.days < 14:
        st.caption(f"Only {status.days} days of history so far, so day-to-day jumps are mostly "
                   "noise. Trends become meaningful after a few weeks.")

# ------------------------------------------------------------------ movers
st.write("")
with ui.card("movers"):
    st.markdown("#### Rising & cooling skills")
    mv = data.movers(role_id, city)
    if mv is None:
        ready = (status.first_day + timedelta(days=2 * MOVER_WINDOW)) if status.first_day else None
        mcol, tcol = st.columns([1, 5], vertical_alignment="center")
        mcol.html(ui.mascot("chartie", 90))
        tcol.markdown(
            f"**Still collecting.** This compares the last {MOVER_WINDOW} days with the "
            f"{MOVER_WINDOW} before, so it needs {2 * MOVER_WINDOW} days of data and at least 30 "
            f"postings in each half. We have **{status.days} days** so far"
            + (f". Check back around **{ready:%d %b %Y}**." if ready else ".")
        )
    else:
        up, down = mv.tail(5).iloc[::-1], mv.head(5)
        a, b = st.columns(2)
        a.markdown("**Rising ▲**")
        for r in up.itertuples():
            if r.change_pts > 0:
                a.html(f'<div>{r.skill} <span class="up">+{r.change_pts:.0f} pts</span></div>')
        b.markdown("**Cooling ▼**")
        for r in down.itertuples():
            if r.change_pts < 0:
                b.html(f'<div>{r.skill} <span class="down">{r.change_pts:.0f} pts</span></div>')

# ------------------------------------------------------------------ cities + table
st.write("")
cl, cr = st.columns([1, 1.4], gap="medium")
with cl, ui.card("cities"):
    st.markdown("#### Where the jobs are")
    cc = data.cities(role_id, days)
    if cc.empty:
        st.caption("No city data yet.")
    else:
        share = cc.jobs / cc.jobs.sum()
        st.plotly_chart(ui.bar_chart(cc.city.tolist(), share.tolist(), cc.jobs.tolist(),
                                     int(cc.jobs.sum())), config=ui.CHART_CONFIG,
                        use_container_width=True)
        st.caption(f"{role} postings in our tracked cities (excludes 'India-wide' ads)")
with cr, ui.card("table"):
    st.markdown("#### The numbers")
    st.caption("Same data as the chart, as a table")
    st.dataframe(
        top.assign(share=(top.share * 100).round(1)).rename(
            columns={"skill": "Skill", "category": "Category", "jobs": "Postings", "share": "% of postings"}),
        hide_index=True, use_container_width=True, height=300,
    )

st.write("")
ui.show(f"""<div class="sp-note"><b>How to read this.</b> "% of postings" = postings that mention
the skill ÷ postings for this role/city/window that list at least one skill ({total:,} here).
About a third of job ads only show a company description, so they're left out of the
denominator. Skills are found with a dictionary of 249 skills, which on a hand-labelled
test set finds 86% of the skills mentioned, and 94% of what it finds is correct.</div>""")
