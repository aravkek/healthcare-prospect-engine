"""
MedPort Team Hub — Auth gate and home screen.
This is the entry point for the Streamlit multi-page app.
All CRM / team content lives in pages/.
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta

import streamlit as st

# Ensure lib/ is importable when running from medport_tools/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.styles import (
    inject_css, MEDPORT_BLUE, MEDPORT_GREEN, MEDPORT_TEAL,
    MEDPORT_LIGHT_BLUE, MEDPORT_LIGHT_GREEN, MEDPORT_LIGHT_TEAL
)
from lib.auth import check_auth, is_admin, render_logout_button
from lib.db import load_prospects, get_activity_feed, get_tasks, get_goals

# ─── Page config — must be first Streamlit call ──────────────────────────────
st.set_page_config(
    page_title="MedPort Team Hub",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ─── Auth ────────────────────────────────────────────────────────────────────
name, email = check_auth()
admin = is_admin(email)


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


ACTION_ICONS = {
    "status_change": ("blue", "S"),
    "note_added": ("blue", "N"),
    "task_created": ("green", "T"),
    "task_completed": ("green", "C"),
    "card_issued": ("orange", "!"),
    "goal_updated": ("green", "G"),
    "search_run": ("blue", "Q"),
}


def _activity_html(activity: dict) -> str:
    actor = activity.get("actor_name", "?")
    initials = "".join(w[0].upper() for w in actor.split()[:2])
    action = activity.get("action_type", "")
    entity = activity.get("entity_name", "")
    details = activity.get("details") or {}
    ts = _time_ago(activity.get("created_at", ""))

    color_cls, _ = ACTION_ICONS.get(action, ("blue", "A"))
    avatar_cls = f"activity-avatar {color_cls}" if color_cls != "blue" else "activity-avatar"

    # Human-readable description
    if action == "status_change":
        old = details.get("old_status", "").replace("_", " ").title()
        new = details.get("new_status", "").replace("_", " ").title()
        desc = f'moved <b>{entity}</b> from {old} &rarr; {new}'
    elif action == "note_added":
        desc = f'added a note on <b>{entity}</b>'
    elif action == "task_created":
        desc = f'created task <b>{entity}</b>'
    elif action == "task_completed":
        desc = f'completed task <b>{entity}</b>'
    elif action == "card_issued":
        card_type = details.get("card_type", "card")
        desc = f'issued a <b>{card_type} card</b> to {entity}'
    elif action == "goal_updated":
        desc = f'updated goal <b>{entity}</b>'
    else:
        desc = f'performed action on <b>{entity}</b>'

    return f"""
<div class="activity-item">
  <div class="{avatar_cls}">{initials}</div>
  <div style="flex:1;">
    <div class="activity-text"><b>{actor}</b> {desc}</div>
    <div class="activity-time">{ts}</div>
  </div>
</div>
"""


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f"""
        <div style="padding:0.5rem 0 0.2rem 0;">
          <span style="font-size:1.3rem;font-weight:900;color:{MEDPORT_TEAL};">MedPort</span>
          <span style="font-size:0.75rem;color:#94a3b8;display:block;">Team Intelligence Hub</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:0.8rem;color:#94a3b8;'>Signed in as <b>{name}</b></div>",
        unsafe_allow_html=True,
    )
    if admin:
        st.markdown(
            f"<span style='background:linear-gradient(135deg,{MEDPORT_TEAL},{MEDPORT_BLUE});color:#fff;border-radius:999px;padding:1px 10px;font-size:0.7rem;font-weight:700;'>Admin</span>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    render_logout_button()

    auto_refresh = st.toggle("Auto-refresh (30s)", value=False, key="home_refresh")

    st.markdown("---")
    st.markdown("### Navigate")
    st.page_link("pages/1_Team_Hub.py", label="Team Hub", icon="🏠")
    st.page_link("pages/2_Outreach_CRM.py", label="Outreach CRM", icon="📊")
    st.page_link("pages/3_Tasks.py", label="Tasks", icon="✅")
    st.page_link("pages/4_Cards.py", label="Cards", icon="🟨")
    st.page_link("pages/5_AI_Research.py", label="AI Research", icon="🤖")
    st.page_link("pages/7_Intelligence.py", label="Intelligence", icon="🔍")
    st.page_link("pages/6_Settings.py", label="Settings", icon="⚙️")

# ─── Auto-refresh ────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()

# ─── Main ─────────────────────────────────────────────────────────────────────

# Logo / greeting
st.markdown(
    f"""
    <div style="display:flex;align-items:baseline;gap:0.6rem;margin-bottom:0.3rem;">
      <span style="font-size:2.4rem;font-weight:700;color:#0F172A;
        font-family:'Plus Jakarta Sans',sans-serif;letter-spacing:-0.02em;">MedPort</span>
      <span style="font-size:1rem;color:#64748b;font-weight:500;">Team Intelligence Hub</span>
    </div>
    <div style="font-size:1.1rem;color:#1e293b;margin-bottom:1.4rem;font-weight:500;">
      Welcome back, <b>{name}</b>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Quick stats ─────────────────────────────────────────────────────────────
df = load_prospects()
tasks = get_tasks()
goals = get_goals()

total_prospects = len(df) if not df.empty else 0
demos_booked = len(df[df["status"] == "demo_booked"]) if not df.empty else 0
converted = len(df[df["status"] == "converted"]) if not df.empty else 0
open_tasks = sum(1 for t in tasks if t.get("status") in ("open", "in_progress"))
active_goals = sum(1 for g in goals if g.get("status") == "active")

c1, c2, c3, c4, c5 = st.columns(5)
for col, val, label in [
    (c1, total_prospects, "Total Prospects"),
    (c2, demos_booked, "Demos Booked"),
    (c3, converted, "Converted"),
    (c4, open_tasks, "Open Tasks"),
    (c5, active_goals, "Active Goals"),
]:
    with col:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value">{val}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ─── Two-column layout: activity + navigation ─────────────────────────────────
left, right = st.columns([3, 2])

with left:
    st.markdown(f"### Recent Activity")
    activities = get_activity_feed(limit=5)
    if activities:
        for act in activities:
            st.markdown(_activity_html(act), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">No activity yet — actions taken in the CRM, Tasks, and Cards pages will appear here.</div>',
            unsafe_allow_html=True,
        )

with right:
    st.markdown("### Quick Access")
    col_a, col_b = st.columns(2)
    with col_a:
        st.page_link("pages/1_Team_Hub.py", label="Team Hub", icon="🏠", use_container_width=True)
        st.page_link("pages/3_Tasks.py", label="Tasks", icon="✅", use_container_width=True)
    with col_b:
        st.page_link("pages/2_Outreach_CRM.py", label="Outreach CRM", icon="📊", use_container_width=True)
        st.page_link("pages/4_Cards.py", label="Cards", icon="🟨", use_container_width=True)

    st.page_link("pages/5_AI_Research.py", label="AI Research Assistant", icon="🤖", use_container_width=True)
    st.page_link("pages/7_Intelligence.py", label="Intelligence Engine", icon="🔍", use_container_width=True)

    if not df.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        tier_a_uncontacted = len(df[(df["priority_rank"] == 1) & (df["status"] == "not_contacted")])
        if tier_a_uncontacted > 0:
            st.markdown(
                f'<div class="alert-box"><b>{tier_a_uncontacted} Tier A prospects</b> haven\'t been contacted yet. '
                f'<a href="/Outreach_CRM" target="_self">Open CRM Queue</a></div>',
                unsafe_allow_html=True,
            )
