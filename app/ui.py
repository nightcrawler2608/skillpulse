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
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 1100px; padding-top: 2.2rem; }}
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
    font-size:clamp(84px,15vw,190px); line-height:.9; letter-spacing:-.01em; margin:0; padding-top:.06em; }}
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
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=GRID,
                     tickfont=dict(color=INK3))
    fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color=INK))
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


CHART_CONFIG = {"displayModeBar": False, "responsive": True}
