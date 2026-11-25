"""Role Explorer: the different kinds of jobs inside one role (skill-based clusters)."""

import html

import streamlit as st

import data
import track
import ui
from skillpulse.analytics.clustering import MIN_JOBS, closest_kind

roles = data.roles()
ss = st.session_state

ui.section("Role explorer", "One title, different jobs",
           "Postings with the same title often want quite different skills. We group them "
           "by the skills they ask for, so you can pick the kind you're aiming for.")

role_names = sorted(roles)
default = (ss.resume["role"] if "resume" in ss and ss.resume["role"] in roles
           else "Machine Learning Engineer" if "Machine Learning Engineer" in roles
           else role_names[0])
role = st.pills("Role", role_names, default=default, key="explore_role") or default
result = data.clusters(roles[role])
track.event(f"explore:{role[:40]}", roles[role], once=True)

if result is None:
    st.html(f'<div class="sp-note">Not enough data yet for <b>{html.escape(role)}</b>: grouping '
            f"needs at least {MIN_JOBS} live postings that list two or more skills. The job "
            "pool grows every night, so check back in a few days.</div>")
    st.stop()
if not result.kinds:
    st.html(f'<div class="sp-note">We tried to group the {result.n_jobs} <b>{html.escape(role)}'
            "</b> postings that list two or more skills, but every split left a group of only "
            "a handful of jobs, so there are no distinct kinds to show yet. Most of these "
            "postings ask for a similar mix. Check back as the job pool grows.</div>")
    st.stop()

# ------------------------------------------------------------------ summary
s1, s2, s3 = st.columns(3)
s1.html(ui.stat("Postings grouped", f"{result.n_jobs}",
                f"of {result.n_total} live {html.escape(role)} postings (those listing 2+ skills)"))
s2.html(ui.stat("Kinds found", f"{len(result.kinds)}",
                "Chosen automatically: the number of groups that separates jobs best"))
s3.html(ui.stat("How distinct", result.strength.capitalize(),
                f"Silhouette score <b>{result.silhouette:.2f}</b> (1 = fully separate groups, "
                "0 = fully mixed)"))

# ------------------------------------------------------------------ kinds
mine = None
if "resume" in ss:
    have = set(ss.get("edited_skills") or ss.resume["skills"])
    mine = closest_kind(result, have)

st.write("")
cols = st.columns(len(result.kinds), gap="medium")
for i, (col, kind) in enumerate(zip(cols, result.kinds, strict=True)):
    with col, ui.card(f"kind{i}"):
        tag = "Kind " + str(i + 1) + (" · closest to your resume" if i == mine else "")
        st.html(f'<span class="sp-cap">{html.escape(tag)}</span>'
                f'<div class="sp-h" style="font-size:20px;text-align:left;margin:4px 0">'
                f'{html.escape(kind.name)}</div>'
                f'<div class="sp-cap">{kind.size} postings · {kind.share * 100:.0f}% of grouped</div>')
        st.markdown("**Skills that define it**")
        st.html(ui.chips([f"{s} · {sh * 100:.0f}%" for s, sh in kind.skills], kind="plain"))
        st.markdown("**Example titles**")
        st.html("<ul style='font-size:13px;margin:0;padding-left:18px'>"
                + "".join(f"<li>{html.escape(t[:70])}</li>" for t in kind.titles) + "</ul>")

st.write("")
track.thumbs("explorer", f"explorer_{roles[role]}", roles[role],
             label="Do these kinds of jobs make sense to you?")
st.html(
    '<div class="sp-note"><b>How to read this.</b> Each kind is a group of postings whose '
    "skill lists look alike (KMeans clustering). The % next to a skill is the share of that "
    "kind's postings asking for it. Groups are named by skills that are common in the group "
    "<i>and</i> rarer elsewhere in the role. A low silhouette score means the kinds overlap: "
    "treat them as tendencies, not strict boxes. Only skills we recognise in the job text "
    "count, and Adzuna gives us the first ~500 characters of each ad."
    + (" Analyse your resume to see which kind you're closest to." if "resume" not in ss else "")
    + "</div>")
