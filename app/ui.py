"""SkillPulse look & feel for Streamlit (see design/DESIGN_SYSTEM.md).

- inject_theme(): fonts, colours, borders and shadows on Streamlit's own widgets
- small HTML components: hero, ribbon, stat card, section header, mascots
- Plotly chart styling that matches the design
"""

from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ASSETS = Path(__file__).parent / "assets"

INK, INK2, INK3 = "#1C1C1C", "#3D4242", "#6A7272"
BG, BG_SHADOW, PAPER, GRID = "#D7E1E1", "#BCC9C9", "#FFFFFF", "#E4EBEB"
SUN, TANGERINE, GOOD = "#FFB000", "#F2541B", "#0E6B47"
# Chart colours: checked for colour-blind safety and 3:1 contrast on white.
SERIES = ["#4A4FD6", "#F2541B", "#168BCC"]

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Bowlby+One&family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, p, li, label, input {{ font-family: 'Inter', system-ui, sans-serif; }}
.stApp {{ background: {BG}; }}
/* solid top bar, so page text doesn't show through it while scrolling */
header[data-testid="stHeader"] {{ background: {BG}; box-shadow: 0 1.5px 0 {BG_SHADOW}; }}
.block-container {{ max-width: 1100px; padding-top: 4.4rem; }}   /* clears the solid top bar */
h1, h2, h3, h4 {{ font-family: 'Bowlby One', 'Arial Black', sans-serif !important; color: {INK} !important;
    letter-spacing: -.01em; font-weight: 400 !important; }}
[data-testid="stSidebar"] {{ background: {PAPER}; border-right: 2px solid {INK}; }}

/* cards = bordered containers created with ui.card() (key starts with "card") */
[class*="st-key-card"] {{ background: {PAPER}; border: 2px solid {INK} !important;
    border-radius: 0 !important; box-shadow: 6px 6px 0 {BG_SHADOW}; padding: 18px 20px !important; }}
[class*="st-key-card"] h4 {{ font-size: 17px !important; text-transform: uppercase; padding-top: 0; }}
/* role pills: square, inked */
[data-testid="stButtonGroup"] button {{ border: 2px solid {INK} !important; border-radius: 0 !important;
    font-weight: 600; }}

/* buttons & links styled like the mockup */
.stButton button, .stLinkButton a, [data-testid="stPageLink"] a {{
    font-family: 'Bowlby One', 'Arial Black', sans-serif !important; text-transform: uppercase;
    border: 2px solid {INK} !important; border-radius: 0 !important; box-shadow: 4px 4px 0 {INK};
    background: {PAPER}; color: {INK} !important; }}
[data-testid="stPageLink"] a:hover {{ transform: translate(-2px,-2px); box-shadow: 6px 6px 0 {INK}; }}
/* main action buttons: solid ink, white text, in every state (hover/focus/pressed included),
   like the "Analyze my resume" button. Without this the text turned ink-on-ink when pressed. */
.stButton button[kind="primary"], [data-testid="stBaseButton-primary"],
.stButton button[kind="primary"]:hover, .stButton button[kind="primary"]:focus,
.stButton button[kind="primary"]:active {{
    background: {INK} !important; color: #fff !important; border-color: {INK} !important;
    box-shadow: 4px 4px 0 {SUN}; }}
.stButton button[kind="primary"] p {{ color: #fff !important; }}
.stButton button:not([kind="primary"]):focus, .stButton button:not([kind="primary"]):active {{
    background: {PAPER} !important; color: {INK} !important; }}
[data-testid="stPageLink"] a p {{ font-family: inherit !important; font-size: 13px; }}

/* inputs: square, inked */
[data-baseweb="select"] > div, .stTextInput input, [data-testid="stFileUploaderDropzone"] {{
    border: 2px solid {INK} !important; border-radius: 0 !important; background: {PAPER}; }}
[data-testid="stWidgetLabel"] p {{ font-weight: 600; color: {INK}; }}
/* pills / segmented control */
[data-testid^="stBaseButton-pills"], [data-testid^="stBaseButton-segmented_control"] {{
    border: 2px solid {INK} !important; border-radius: 0 !important; font-weight: 600; }}
[data-testid="stBaseButton-pillsActive"], [data-testid="stBaseButton-segmented_controlActive"] {{
    background: {INK} !important; color: #fff !important; }}
[data-testid="stAlert"] {{ border-radius: 0; border: 2px solid {INK}; }}

/* ---- custom components ---- */
.sp-cap {{ font-size: 12px; color: {INK3}; letter-spacing: .02em; }}
.sp-meta {{ display:flex; justify-content:space-between; max-width:560px; margin:0 auto 2px;
    font-size:12px; color:{INK}; }}
.sp-mega {{ font-family:'Anton', Impact, sans-serif; color:{INK}; text-transform:uppercase; text-align:center;
    font-size:clamp(84px,12vw,150px); line-height:.9; letter-spacing:-.01em; margin:0; padding-top:.06em; }}
.sp-hero {{ position:relative; overflow:visible; padding-bottom: 6px; }}
.sp-ribbon {{ position:absolute; left:-12vw; right:-12vw; top:51%; transform:rotate(-4deg); background:{PAPER};
    border-top:2px solid {INK}; border-bottom:2px solid {INK}; box-shadow:0 8px 0 {BG_SHADOW}; overflow:hidden; z-index:3; }}
.sp-track {{ display:flex; width:max-content; animation:sp-marquee 40s linear infinite; }}
.sp-item {{ font:14px 'Bowlby One','Arial Black',sans-serif; color:{INK}; padding:9px 0; white-space:nowrap; }}
.sp-item i {{ font-style:normal; padding:0 18px; color:{INK3}; }}
.sp-item b {{ font-weight:400; color:{GOOD}; }}
@keyframes sp-marquee {{ to {{ transform: translateX(-50%); }} }}
@media (prefers-reduced-motion: reduce) {{ .sp-track, .sp-bob {{ animation:none !important; }} }}
.sp-mascots {{ display:flex; justify-content:center; align-items:flex-end; gap:10px; }}
.sp-bob {{ animation: sp-bob 4s ease-in-out infinite; }}
@keyframes sp-bob {{ 50% {{ translate: 0 -8px; }} }}
.sp-h {{ font-family:'Bowlby One','Arial Black',sans-serif; color:{INK}; line-height:1.05; text-align:center; }}
.sp-sec {{ text-align:center; margin: 8px 0 22px; }}
.sp-sec .sp-h {{ font-size:clamp(30px,5vw,52px); text-transform:uppercase; }}
.sp-sec p {{ max-width:560px; margin:8px auto 0; font-size:14px; color:{INK}; }}
.sp-stat {{ background:{PAPER}; border:2px solid {INK}; box-shadow:6px 6px 0 {BG_SHADOW}; padding:18px 20px; height:100%; }}
.sp-stat .tag {{ display:inline-block; font:11px 'Bowlby One','Arial Black',sans-serif; padding:3px 8px;
    border:1.5px solid {INK}; margin-bottom:10px; color:{INK}; text-transform:uppercase; }}
.sp-stat .k {{ font:28px/1.1 'Bowlby One','Arial Black',sans-serif; color:{INK}; }}
.sp-stat .l {{ font-size:12.5px; color:{INK2}; margin-top:6px; }}
.sp-rule {{ border:0; border-top:1.5px solid {INK}; max-width:520px; margin:56px auto; }}
.sp-list {{ list-style:none; text-align:center; padding:0; margin:0; }}
.sp-list li {{ font:clamp(20px,3vw,28px)/1.45 'Bowlby One','Arial Black',sans-serif; color:{INK}; }}
.up {{ color:{GOOD}; }} .down {{ color:{TANGERINE}; }}
.sp-note {{ background:{PAPER}; border:2px dashed {INK}; padding:14px 16px; font-size:13px; color:{INK}; }}
.sp-chips {{ display:flex; flex-wrap:wrap; gap:8px; margin:6px 0 14px; }}
.sp-chip {{ font:600 12.5px 'Inter',sans-serif; padding:6px 10px; border:1.5px solid {INK}; background:{PAPER};
    color:{INK}; display:inline-flex; gap:6px; align-items:center; }}
.sp-chip.miss {{ background:{SUN}; }}
.sp-chip .ok {{ color:{GOOD}; font-weight:800; }}
.sp-chip .n {{ font:11px 'Bowlby One','Arial Black',sans-serif; background:{INK}; color:#fff; min-width:18px;
    height:18px; display:grid; place-items:center; border-radius:50%; }}
.sp-chip .g {{ color:{INK3}; font-weight:500; }}
.sp-ring {{ width:176px; height:176px; border-radius:50%; margin:6px auto 8px; display:grid; place-items:center; }}
.sp-ring .in {{ width:130px; height:130px; border-radius:50%; background:{PAPER}; display:grid; place-items:center;
    text-align:center; }}
.sp-ring .v {{ font:54px/1 'Anton',Impact,sans-serif; color:{INK}; }}
.sp-job {{ background:{PAPER}; border:2px solid {INK}; box-shadow:6px 6px 0 {BG_SHADOW}; padding:16px 18px;
    margin-bottom:16px; }}
.sp-job .t {{ font:16px/1.25 'Bowlby One','Arial Black',sans-serif; color:{INK}; }}
.sp-job .m {{ font-size:12.5px; color:{INK2}; margin:4px 0 8px; }}
.sp-job .fit {{ display:flex; justify-content:space-between; align-items:center; border-top:1.5px solid {INK};
    padding-top:10px; margin-top:6px; }}
.sp-job .pct {{ font:22px 'Bowlby One','Arial Black',sans-serif; color:{INK}; }}
.sp-job a.go {{ font:11px 'Bowlby One','Arial Black',sans-serif; text-transform:uppercase; color:{INK};
    border:2px solid {INK}; padding:7px 12px; box-shadow:3px 3px 0 {INK}; text-decoration:none; background:{PAPER}; }}
.sp-plan {{ background:{PAPER}; border:2px solid {INK}; box-shadow:6px 6px 0 {BG_SHADOW}; padding:16px 18px;
    margin-bottom:16px; }}
.sp-plan .wk {{ display:inline-block; font:11px 'Bowlby One','Arial Black',sans-serif; text-transform:uppercase;
    background:{SUN}; border:1.5px solid {INK}; padding:3px 8px; color:{INK}; }}
.sp-plan .t {{ font:18px/1.25 'Bowlby One','Arial Black',sans-serif; color:{INK}; margin:8px 0 2px; }}
.sp-plan .m {{ font-size:13.5px; color:{INK}; font-weight:600; }}
.sp-plan ul {{ margin:8px 0; padding-left:18px; font-size:13px; color:{INK2}; }}
.sp-plan .pj {{ font-size:13px; color:{INK}; border-top:1.5px dashed {INK}; padding-top:8px; margin:6px 0 12px; }}
.sp-plan a.go {{ font:11px 'Bowlby One','Arial Black',sans-serif; text-transform:uppercase; color:{INK};
    border:2px solid {INK}; padding:7px 12px; box-shadow:3px 3px 0 {INK}; text-decoration:none; display:inline-block; }}

/* ---- polish: same look, better feel ---- */
a.go {{ transition: transform .12s ease, box-shadow .12s ease; }}
a.go:hover {{ transform: translate(-1px,-1px); box-shadow: 4px 4px 0 {INK}; }}
a.go:active {{ transform: translate(2px,2px); box-shadow: 1px 1px 0 {INK}; }}
a.go:focus-visible, [data-testid="stPageLink"] a:focus-visible, .stButton button:focus-visible {{
    outline: 3px solid {SUN}; outline-offset: 2px; }}
.sp-job, .sp-plan {{ display:flex; flex-direction:column; }}
.sp-job .fit, .sp-plan a.go {{ margin-top:auto; }}
.sp-plan a.go {{ align-self:flex-start; }}
.sp-soft {{ font-size:12.5px; color:{INK2}; margin:-4px 0 10px; }}
.sp-foot {{ text-align:center; font-size:12.5px; color:{INK}; margin:0 0 28px; line-height:1.7; }}
.sp-foot a {{ color:{INK}; }}
/* results summary strip with jump links */
.sp-sum {{ display:flex; flex-wrap:wrap; gap:10px; align-items:stretch; justify-content:center; margin:6px 0 4px; }}
.sp-sum .it {{ background:{PAPER}; border:2px solid {INK}; box-shadow:4px 4px 0 {BG_SHADOW}; padding:10px 14px;
    min-width:150px; }}
.sp-sum .it .k {{ font:20px/1.1 'Bowlby One','Arial Black',sans-serif; color:{INK}; }}
.sp-sum .it .l {{ font-size:11.5px; color:{INK3}; text-transform:uppercase; letter-spacing:.04em; }}
.sp-jump {{ text-align:center; font-size:13px; margin:10px 0 0; }}
.sp-jump a {{ color:{INK}; font-weight:600; margin:0 8px; }}
.sp-anchor {{ position:relative; top:-80px; }}   /* lands below the fixed top bar */
.sp-roles {{ display:flex; flex-direction:column; gap:10px; }}
.sp-rb {{ display:grid; grid-template-columns: minmax(150px, 1.3fr) 2fr 36px; gap:12px; align-items:center; }}
.sp-rb .lab {{ font-size:13px; color:{INK}; display:flex; flex-direction:column; line-height:1.25; }}
.sp-rb .bar {{ height:16px; border:1.5px solid {INK}; background:{PAPER}; }}
.sp-rb .bar span {{ display:block; height:100%; background:{INK3}; }}
.sp-rb.here .bar span {{ background:{SUN}; }}
.sp-rb .v {{ font:16px 'Bowlby One','Arial Black',sans-serif; color:{INK}; text-align:right; }}
@media (max-width: 640px) {{ .sp-rb {{ grid-template-columns: 1fr 34px; }}
  .sp-rb .bar {{ grid-column: 1 / -1; grid-row: 2; }} }}

/* ---- phones (Streamlit stacks columns below 640px) ---- */
@media (max-width: 640px) {{
  .block-container {{ padding: 3.6rem 1rem 2rem !important; }}
  .sp-mega {{ font-size: 23vw; }}
  .sp-meta {{ flex-direction:column; align-items:center; gap:2px; }}
  .sp-mascots > div {{ width: 27vw !important; height: 27vw !important; }}
  .sp-mascots img {{ width:100%; height:100%; }}
  .sp-sec {{ margin: 4px 0 16px; }}
  .sp-sec .sp-h {{ font-size: 30px; }}
  .sp-list li {{ font-size: 20px; }}
  .sp-rule {{ margin: 36px auto; }}
  .sp-stat .k {{ font-size: 24px; }}
  .sp-ring {{ width:150px; height:150px; }}
  .sp-ring .in {{ width:110px; height:110px; }}
  .sp-ring .v {{ font-size:46px; }}
  [class*="st-key-card"] {{ padding: 14px 14px !important; }}
}}
/* ---- tablets: a little less padding so 3-column rows breathe ---- */
@media (min-width: 641px) and (max-width: 1024px) {{
  .block-container {{ padding-left: 1.4rem !important; padding-right: 1.4rem !important; }}
  .sp-job, .sp-plan {{ padding: 14px 14px; }}
}}
"""


def inject_theme() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def show(html_str: str) -> None:
    """Render a block of our own (trusted) HTML."""
    st.html(html_str)


@lru_cache(maxsize=8)
def _svg_data_uri(name: str) -> str:
    # Streamlit's HTML sanitiser strips inline <svg>, so we embed each mascot as an
    # image with a data: URI instead (still no extra files to host).
    raw = (ASSETS / f"{name}.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(raw).decode()


def mascot(name: str, size: int = 200, rotate: float = 0, bob: bool = False) -> str:
    cls = "sp-bob" if bob else ""
    return (f'<div class="{cls}" style="width:{size}px;height:{size}px;transform:rotate({rotate}deg)">'
            f'<img src="{_svg_data_uri(name)}" alt="" width="{size}" height="{size}"></div>')


def ribbon(items: list[tuple[str, str]]) -> str:
    """items: (label, highlighted suffix) e.g. ("PYTHON", "83 JOBS")."""
    one = "".join(f'<span class="sp-item">{html.escape(a)}'
                  f'{f" <b>{html.escape(b)}</b>" if b else ""}<i>·</i></span>' for a, b in items)
    return f'<div class="sp-ribbon" aria-label="Trending skills"><div class="sp-track">{one * 4}</div></div>'


def section(cap: str, title: str, sub: str = "") -> None:
    show(f'<div class="sp-sec"><div class="sp-cap">{html.escape(cap)}</div>'
         f'<div class="sp-h">{html.escape(title)}</div>'
         f'{f"<p>{html.escape(sub)}</p>" if sub else ""}</div>')


def stat(tag: str, value: str, label_html: str) -> str:
    return (f'<div class="sp-stat"><span class="tag">{html.escape(tag)}</span>'
            f'<div class="k">{html.escape(value)}</div><div class="l">{label_html}</div></div>')


def card(name: str):
    """A white, ink-bordered card (use as `with ui.card("top"):`)."""
    return st.container(border=True, key=f"card-{name}")


def score_ring(score: float) -> str:
    pct = max(0.0, min(100.0, score))
    return (f'<div class="sp-ring" role="img" aria-label="Match score {score:.0f} out of 100" '
            f'style="background:conic-gradient({INK} 0 {pct}%, {GRID} {pct}% 100%)">'
            f'<div class="in"><div><div class="v">{score:.0f}</div>'
            f'<div class="sp-cap">out of 100</div></div></div></div>')


def chips(items: list[str], kind: str = "have") -> str:
    if kind == "have":
        inner = "".join(f'<span class="sp-chip"><span class="ok">✓</span>{html.escape(s)}</span>'
                        for s in items)
    else:
        inner = "".join(f'<span class="sp-chip">{html.escape(s)}</span>' for s in items)
    return f'<div class="sp-chips">{inner}</div>'


def gap_chips(gaps) -> str:
    """Missing skills: rank, name, share of postings, and the score gain."""
    inner = "".join(
        f'<span class="sp-chip miss"><span class="n">{i}</span>{html.escape(g.skill)}'
        f'<span class="g">· {g.share * 100:.0f}% of jobs · +{g.gain:.0f} pts</span></span>'
        for i, g in enumerate(gaps, 1))
    return f'<div class="sp-chips">{inner}</div>'


def job_card(title: str, meta: str, fit: float, matched: list[str], to_learn: list[str],
             url: str | None) -> str:
    def _chip_list(items, cls=""):
        return "".join(f'<span class="sp-chip {cls}">{html.escape(s)}</span>' for s in items)
    link = (f'<a class="go" href="{html.escape(url)}" target="_blank" rel="noopener">View job ▸</a>'
            if url else "")
    skills = ""
    if matched:
        skills += f'<div class="sp-cap">You have</div><div class="sp-chips">{_chip_list(matched)}</div>'
    if to_learn:
        skills += (f'<div class="sp-cap">It also asks for</div>'
                   f'<div class="sp-chips">{_chip_list(to_learn[:5], "miss")}</div>')
    return (f'<div class="sp-job"><div class="t">{html.escape(title)}</div>'
            f'<div class="m">{html.escape(meta)}</div>{skills}'
            f'<div class="fit"><span><span class="pct">{fit * 100:.0f}%</span> '
            f'<span class="sp-cap">fit</span></span>{link}</div></div>')


def plan_week(item) -> str:
    """One block of the learning plan (a planner.PlanWeek). All text is escaped."""
    wk = item.weeks
    label = f"Week {wk[0]}" if len(wk) == 1 else f"Weeks {wk[0]}–{wk[-1]}"
    tasks = "".join(f"<li>{html.escape(t)}</li>" for t in item.tasks)
    return (f'<div class="sp-plan"><div class="wk">{label}</div>'
            f'<div class="t">{html.escape(item.skill)}</div>'
            f'<div class="m">{html.escape(item.goal)}</div><ul>{tasks}</ul>'
            f'<div class="pj"><b>Mini project:</b> {html.escape(item.project)}</div>'
            f'<a class="go" href="{html.escape(item.link)}" target="_blank" rel="noopener">'
            f'{html.escape(item.link_label)} ▸</a></div>')


def role_bars(fits, current: str) -> str:
    """Ranked roles with an inked bar per score (RoleFit list from scorer.rank_roles)."""
    rows = []
    for f in fits:
        here = f.role == current
        nxt = (f'<span class="sp-cap">next: {html.escape(f.next_skill)}</span>'
               if f.next_skill else "")
        rows.append(
            f'<div class="sp-rb{" here" if here else ""}">'
            f'<div class="lab"><b>{html.escape(f.role)}</b>{" · your pick" if here else ""}{nxt}</div>'
            f'<div class="bar"><span style="width:{max(2.0, min(100.0, f.score)):.0f}%"></span></div>'
            f'<div class="v">{f.score:.0f}</div></div>')
    return f'<div class="sp-roles">{"".join(rows)}</div>'


def rule() -> None:
    show('<hr class="sp-rule">')


# ---------------------------------------------------------------- charts
def _base_layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=8, r=16, t=8, b=8),
        paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=INK2),
        hoverlabel=dict(bgcolor=INK, font_color="#fff", font_family="Inter", bordercolor=INK),
        showlegend=False,
        dragmode=False,                 # no drag-to-zoom: on phones it traps scrolling
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=GRID,
                     tickfont=dict(color=INK3), fixedrange=True)
    fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color=INK), fixedrange=True)
    return fig


def bar_chart(skills: list[str], shares: list[float], jobs: list[int], total: int) -> go.Figure:
    """Horizontal ranked bars, one colour (single series)."""
    fig = go.Figure(go.Bar(
        x=[s * 100 for s in shares], y=skills, orientation="h",
        marker=dict(color=SERIES[0], cornerradius=4),
        text=[f"{s * 100:.0f}%" for s in shares], textposition="outside", cliponaxis=False,
        textfont=dict(color=INK3, size=11),
        customdata=list(zip(jobs, [total] * len(jobs))),
        hovertemplate="<b>%{y}</b><br>%{x:.0f}% of postings · %{customdata[0]} of %{customdata[1]}"
                      "<extra></extra>",
    ))
    fig = _base_layout(fig, height=34 * len(skills) + 30)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(ticksuffix="%", rangemode="tozero")
    fig.update_layout(bargap=0.35)
    return fig


def line_chart(df, skills: list[str]) -> go.Figure:
    """One line per skill; colour follows the skill's position in the user's pick."""
    fig = go.Figure()
    for i, skill in enumerate(skills):
        d = df[df["skill"] == skill]
        color = SERIES[i % len(SERIES)]
        fig.add_trace(go.Scatter(
            x=d["period"], y=d["share"] * 100, name=skill, mode="lines+markers",
            line=dict(color=color, width=2), marker=dict(size=8, color=color,
                                                          line=dict(color="#fff", width=2)),
            customdata=list(zip(d["jobs"].astype(int), d["total"].astype(int))),
            hovertemplate=f"<b>{html.escape(skill)}</b> %{{y:.0f}}% "
                          "(%{customdata[0]} of %{customdata[1]})<extra></extra>",
        ))
    fig = _base_layout(fig, height=300)
    fig.update_layout(showlegend=True, hovermode="x unified",
                      legend=dict(orientation="h", y=1.12, x=0, font=dict(color=INK2)))
    fig.update_yaxes(ticksuffix="%", rangemode="tozero", showgrid=True, gridcolor=GRID,
                     tickfont=dict(color=INK3))
    fig.update_xaxes(showgrid=False, tickformat="%d %b")
    return fig


CHART_CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": False}
