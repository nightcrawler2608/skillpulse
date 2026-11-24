"""Cached database access for the app.

Data changes once a night, so caching for 1 hour keeps the app fast and keeps
Neon's free tier quiet.
"""

from __future__ import annotations

import streamlit as st

from skillpulse.analytics import market
from skillpulse.db.connection import get_connection

TTL = 3600


@st.cache_data(ttl=TTL, show_spinner=False)
def status():
    with get_connection() as c:
        return market.data_status(c)


@st.cache_data(ttl=TTL, show_spinner=False)
def roles() -> dict[str, int]:
    with get_connection() as c:
        return {name: rid for rid, name in market.roles(c)}


@st.cache_data(ttl=TTL, show_spinner=False)
def top_skills(role_id: int, city: str, days: int, n: int = 15):
    with get_connection() as c:
        df = market.top_skills(c, role_id, city, days, n)
        return df, df.attrs.get("total", 0)


@st.cache_data(ttl=TTL, show_spinner=False)
def trend(role_id: int, city: str, skills: tuple[str, ...], days: int, freq: str):
    with get_connection() as c:
        return market.skill_trend(c, role_id, city, list(skills), days, freq)


@st.cache_data(ttl=TTL, show_spinner=False)
def movers(role_id: int, city: str):
    with get_connection() as c:
        return market.movers(c, role_id, city)


@st.cache_data(ttl=TTL, show_spinner=False)
def salary(role_id: int, city: str, days: int):
    with get_connection() as c:
        return market.salary_summary(c, role_id, city, days)


@st.cache_data(ttl=TTL, show_spinner=False)
def trending(days: int = 7, n: int = 8):
    with get_connection() as c:
        return market.trending_overall(c, days, n)


@st.cache_data(ttl=TTL, show_spinner=False)
def cities(role_id: int, days: int):
    with get_connection() as c:
        return market.city_counts(c, role_id, days)
