"""
MedPort Standups — daily standup submission and team feed.
Access: all authenticated users.
Admin sees full team feed; non-admin sees only their own.
"""

import os
import sys
import time
from datetime import datetime, timezone, date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import inject_css, MEDPORT_TEAL, MEDPORT_DARK, MEDPORT_BLUE, DEPT_COLORS, DEPT_LABELS, page_header
from lib.auth import check_auth, is_admin, get_department, render_logout_button
from lib.db import get_standups, submit_standup, get_today_standup, log_activity

st.set_page_config(
    page_title="Standups — MedPort",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)
dept = get_department(email)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _time_ago(ts_str: str) -> str:
    if not ts_str:
        return ""
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - ts
        secs = int(delta.total_seconds())
        if secs < 60:
            return "just now"
        elif secs < 3600:
            return f"{secs // 60}m ago"
        elif secs < 86400:
            return f"{secs // 3600}h ago"
        elif secs < 172800:
            return "Yesterday"
        else:
            return ts.strftime("%b %d")
    except Exception:
        return ""


def _dept_badge(department: str) -> str:
    label = DEPT_LABELS.get(department, department.title())
    return f'<span class="dept-badge dept-{department}">{label}</span>'


def _date_label(date_str: str) -> str:
    """Convert ISO date string to human-readable label."""
    if not date_str:
        return ""
    try:
        d = date.fromisoformat(date_str)
        today = date.today()
        delta = (today - d).days
        if delta == 0:
            return "Today"
        elif delta == 1:
            return "Yesterday"
        else:
            return d.strftime("%A, %b %d")
    except Exception:
        return date_str


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">MedPort</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:0.8rem;color:#94a3b8;'>Signed in as <b>{name}</b></div>",
        unsafe_allow_html=True,
    )
    st.markdown(_dept_badge(dept), unsafe_allow_html=True)
    st.markdown("---")
    render_logout_button()
    st.markdown("---")
    st.markdown("<div style='font-size:0.75rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;'>Navigation</div>", unsafe_allow_html=True)
    st.page_link("medport_dashboard.py", label="Home", icon="🏠")
    st.page_link("pages/1_Team_Hub.py", label="Team Hub", icon="👥")
    st.page_link("pages/3_Tasks.py", label="Tasks", icon="✅")
    st.page_link("pages/6_Settings.py", label="Settings", icon="⚙️")

# ─── Tabs ────────────────────────────────────────────────────────────────────

tab_submit, tab_feed = st.tabs(["Submit", "Team Feed"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Submit
# ═══════════════════════════════════════════════════════════════════════════════

with tab_submit:
    st.markdown(page_header("Daily Standup", "Keep the team in sync"), unsafe_allow_html=True)

    today_standup = get_today_standup(email)

    if today_standup:
        # Already submitted — show a success card
        submitted_at = _time_ago(today_standup.get("submitted_at") or today_standup.get("created_at", ""))
        st.markdown(
            f"""
            <div style="background:#f0fdf9;border:1px solid #6ee7b7;border-left:4px solid #10b981;
              border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;">
              <div style="font-size:1rem;font-weight:700;color:#065f46;font-family:'Plus Jakarta Sans',sans-serif;">
                Already submitted today &#10003;
              </div>
              <div style="font-size:0.875rem;color:#047857;margin-top:4px;">
                Submitted {submitted_at}. Here's what you shared:
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Show the submitted standup
        yesterday_text = today_standup.get("yesterday", "")
        today_text = today_standup.get("today", "")
        blockers_text = today_standup.get("blockers", "")

        st.markdown(
            f"""
            <div class="standup-card">
              <div class="standup-author">{name}</div>
              {"" if not yesterday_text else f'<div class="standup-section">Yesterday</div><div class="standup-text">{yesterday_text}</div>'}
              <div class="standup-section">Today</div>
              <div class="standup-text">{today_text}</div>
              {"" if not blockers_text else f'<div class="standup-section">Blockers</div><div class="standup-text">{blockers_text}</div>'}
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        # Show submission form
        std_yesterday = st.text_area(
            "What did you accomplish yesterday?",
            max_chars=1000,
            height=100,
            key="std_yesterday",
            placeholder="Describe what you completed or made progress on...",
        )
        std_today = st.text_area(
            "What will you work on today? *",
            max_chars=1000,
            height=100,
            key="std_today",
            placeholder="Describe your focus for today...",
        )
        std_blockers = st.text_area(
            "Any blockers?",
            max_chars=500,
            height=80,
            key="std_blockers",
            placeholder="None — leave blank if you have no blockers.",
        )

        if st.button("Submit Standup", type="primary", key="std_submit"):
            today_clean = std_today.strip()
            if not today_clean:
                st.error("Today's focus is required.")
            else:
                payload = {
                    "author_email": email.lower(),
                    "author_name": name,
                    "department": dept,
                    "yesterday": std_yesterday.strip(),
                    "today": today_clean,
                    "blockers": std_blockers.strip(),
                    "date": date.today().isoformat(),
                }
                new_id = submit_standup(payload)
                if new_id:
                    log_activity(
                        actor_email=email,
                        actor_name=name,
                        action_type="standup_submitted",
                        entity_type="standup",
                        entity_id=str(new_id),
                        entity_name=f"{name} standup {date.today().isoformat()}",
                    )
                    st.success("Standup submitted!")
                    st.balloons()
                    # Brief pause so balloons render, then rerun to show the card
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to submit standup. Check your connection.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Team Feed
# ═══════════════════════════════════════════════════════════════════════════════

with tab_feed:
    st.markdown(
        '<div style="font-size:1.25rem;font-weight:700;color:#0F172A;font-family:\'Plus Jakarta Sans\',sans-serif;margin-bottom:0.25rem;">Team Standups</div>',
        unsafe_allow_html=True,
    )

    # Admin can filter by date; admin sees all standups, non-admin sees only own
    if admin:
        col_filter, col_spacer = st.columns([2, 4])
        with col_filter:
            std_date_filter = st.date_input(
                "Filter by date",
                value=None,
                key="std_date_filter",
            )
        standups = get_standups(limit=30)
    else:
        std_date_filter = None
        standups = get_standups(limit=30, author_email=email)

    if std_date_filter:
        filter_str = std_date_filter.isoformat()
        standups = [s for s in standups if s.get("date") == filter_str]

    if not standups:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.9rem;padding:1rem 0;">No standups found.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Group by date
        current_date_label = None
        for standup in standups:
            standup_date = standup.get("date", "")
            date_label = _date_label(standup_date)

            if date_label != current_date_label:
                current_date_label = date_label
                st.markdown(
                    f"""
                    <div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.08em;color:#94a3b8;margin:1.25rem 0 0.5rem 0;
                      border-bottom:1px solid #e2e8f0;padding-bottom:0.4rem;">
                      {date_label}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            author_name = standup.get("author_name", "Unknown")
            author_dept = standup.get("department", "unassigned")
            submitted_at = _time_ago(standup.get("submitted_at") or standup.get("created_at", ""))
            yesterday_text = standup.get("yesterday", "")
            today_text = standup.get("today", "")
            blockers_text = standup.get("blockers", "")
            dept_badge_html = _dept_badge(author_dept)

            blockers_html = (
                f'<div class="standup-section">Blockers</div><div class="standup-text">{blockers_text}</div>'
                if blockers_text else ""
            )
            yesterday_html = (
                f'<div class="standup-section">Yesterday</div><div class="standup-text">{yesterday_text}</div>'
                if yesterday_text else ""
            )

            st.markdown(
                f"""
                <div class="standup-card">
                  <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
                    <span class="standup-author">{author_name}</span>
                    {dept_badge_html}
                    <span class="standup-date">{submitted_at}</span>
                  </div>
                  {yesterday_html}
                  <div class="standup-section">Today</div>
                  <div class="standup-text">{today_text}</div>
                  {blockers_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
