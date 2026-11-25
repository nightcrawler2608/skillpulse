"""Anonymous usage events and feedback.

What's stored: a random ID made fresh for each browser tab (no cookie, no login, not
linked to anything about the person), an event name like "analyze" or a thumbs-up /
thumbs-down, and the role. Never resume text, skills, names, IP addresses or cities.

Why: Phase 7 needs real numbers (how many people used it, which parts helped) for the
report, and feedback shows where the app is wrong.

Every write is best-effort: if the database is slow or down, the app carries on.
"""

from __future__ import annotations

import logging
import os
import uuid

import streamlit as st

from skillpulse.db.connection import get_connection

log = logging.getLogger(__name__)

EVENT_SQL = "INSERT INTO usage_events (session_id, event, role_id) VALUES (%s, %s, %s)"
FEEDBACK_SQL = ("INSERT INTO feedback (session_id, role_id, target, job_id, rating) "
                "VALUES (%s, %s, %s, %s, %s)")


def session_id() -> str:
    if "sid" not in st.session_state:
        st.session_state.sid = uuid.uuid4().hex
    return st.session_state.sid


def _write(sql: str, params: tuple) -> None:
    if os.getenv("SKILLPULSE_TRACKING", "on").lower() == "off":   # local testing
        return
    try:
        with get_connection() as conn:
            conn.execute(sql, params)
            conn.commit()
    except Exception as e:  # noqa: BLE001 - tracking must never break the app
        log.warning("tracking write skipped: %s", type(e).__name__)


def event(name: str, role_id: int | None = None, once: bool = False) -> None:
    """Record an event. once=True: at most once per browser session (e.g. page views)."""
    if once:
        seen = st.session_state.setdefault("seen_events", set())
        if name in seen:
            return
        seen.add(name)
    _write(EVENT_SQL, (session_id(), name[:60], role_id))


def thumbs(target: str, key: str, role_id: int | None = None, job_id: int | None = None,
           label: str | None = None) -> None:
    """A thumbs up/down widget; a vote is saved once per widget per session."""
    if label:
        st.caption(label)
    value = st.feedback("thumbs", key=f"fb_{key}")
    done = st.session_state.setdefault("fb_saved", set())
    if value is not None and key not in done:
        done.add(key)
        _write(FEEDBACK_SQL, (session_id(), role_id, target, job_id, 1 if value == 1 else -1))
        st.toast("Thanks, noted!", icon=":material/thumb_up:")
