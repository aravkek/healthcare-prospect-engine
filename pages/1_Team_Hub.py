"""
MedPort Team Hub — team overview, activity feed, goals, and my tasks.
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import inject_css, MEDPORT_BLUE, MEDPORT_GREEN, MEDPORT_TEAL, TASK_STATUS_COLORS
from lib.auth import check_auth, is_admin, render_logout_button
from lib.db import load_prospects, get_activity_feed, get_tasks, get_goals, get_team_members

st.set_page_config(
    page_title="Team Hub — MedPort",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

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


def _activity_description(activity: dict) -> str:
    action = activity.get("action_type", "")
    entity = activity.get("entity_name", "")
    details = activity.get("details") or {}

    if action == "status_change":
        old = details.get("old_status", "").replace("_", " ").title()
        new_s = details.get("new_status", "").replace("_", " ").title()
        return f'moved <b>{entity}</b> from {old} &rarr; {new_s}'
    elif action == "note_added":
        return f'added a note on <b>{entity}</b>'
    elif action == "task_created":
        return f'created task <b>{entity}</b>'
    elif action == "task_completed":
        return f'completed task <b>{entity}</b>'
    elif action == "card_issued":
        card_type = details.get("card_type", "card")
        return f'issued a <b>{card_type} card</b> to {entity}'
    elif action == "goal_updated":
        return f'updated goal <b>{entity}</b>'
    elif action == "search_run":
        return f'ran a search: <b>{entity}</b>'
    return f'took action on <b>{entity}</b>'


def _activity_color_class(action: str) -> str:
    mapping = {
        "task_completed": "green",
        "goal_updated": "green",
        "card_issued": "orange",
    }
    return mapping.get(action, "")


def _week_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=now.weekday())


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">MedPort</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='font-size:0.8rem;color:#94a3b8;'>Signed in as <b>{name}</b></div>", unsafe_allow_html=True)
    st.markdown("---")

    render_logout_button()

    auto_refresh = st.toggle("Auto-refresh (30s)", value=False, key="hub_refresh")
    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()

# ─── Load data ───────────────────────────────────────────────────────────────

df = load_prospects()
all_tasks = get_tasks()
goals = get_goals()
activities = get_activity_feed(limit=30)
members = get_team_members()

week_start = _week_start()

# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown(f"# Team Hub")
st.markdown(
    f'<div style="color:#6b7a8d;font-size:0.88rem;margin-top:-0.6rem;margin-bottom:1.2rem;">'
    f'Team command center — activity, goals, and who\'s doing what'
    f'</div>',
    unsafe_allow_html=True,
)

# ─── Quick stats bar ─────────────────────────────────────────────────────────

if not df.empty:
    total_p = len(df)
    demos = len(df[df["status"] == "demo_booked"])
    converted = len(df[df["status"] == "converted"])
    contacted = len(df[df["status"] != "not_contacted"])
    conv_rate = round(converted / contacted * 100, 1) if contacted > 0 else 0.0
    tier_a_fresh = len(df[(df["priority_rank"] == 1) & (df["status"] == "not_contacted")])
else:
    demos = converted = contacted = tier_a_fresh = 0
    conv_rate = 0.0

open_t = sum(1 for t in all_tasks if t.get("status") in ("open", "in_progress"))
completed_this_week = sum(
    1 for t in all_tasks
    if t.get("status") == "completed" and t.get("completed_at")
    and datetime.fromisoformat(t["completed_at"].replace("Z", "+00:00")) >= week_start
)

c1, c2, c3, c4, c5 = st.columns(5)
for col, val, label in [
    (c1, total_p, "Total Prospects"),
    (c2, demos, "Demos Booked"),
    (c3, f"{conv_rate}%", "Conversion Rate"),
    (c4, open_t, "Open Tasks"),
    (c5, completed_this_week, "Completed This Week"),
]:
    with col:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value">{val}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ─── Team Overview strip ─────────────────────────────────────────────────────

st.markdown(f"### Team Overview")

num_members = max(len(members), 1)
member_cols = st.columns(num_members)
for idx, member in enumerate(members):
    member_name = member["name"]
    member_role = member.get("role", "Team Member")
    avatar_color = member.get("avatar_color", MEDPORT_TEAL)
    with member_cols[idx]:
        # Prospects assigned
        if not df.empty and "assigned_to" in df.columns:
            assigned_count = len(df[df["assigned_to"] == member_name])
        else:
            assigned_count = 0

        # Tasks
        member_tasks = [t for t in all_tasks if member_name in (t.get("assigned_to") or [])]
        open_member = sum(1 for t in member_tasks if t.get("status") in ("open", "in_progress"))
        completed_member = sum(
            1 for t in member_tasks
            if t.get("status") == "completed" and t.get("completed_at")
            and datetime.fromisoformat(t["completed_at"].replace("Z", "+00:00")) >= week_start
        )

        initials = "".join(w[0].upper() for w in member_name.split()[:2])
        st.markdown(
            f"""
            <div class="member-card">
              <div class="member-avatar" style="background:linear-gradient(135deg,{avatar_color},{MEDPORT_BLUE});">{initials}</div>
              <div class="member-name">{member_name}</div>
              <div class="member-role">{member_role}</div>
              <div class="member-stat" style="margin-top:0.5rem;">
                <b style="color:{MEDPORT_TEAL};">{assigned_count}</b> prospects
              </div>
              <div class="member-stat">
                <b style="color:#8b5cf6;">{open_member}</b> tasks open
              </div>
              <div class="member-stat">
                <b style="color:{MEDPORT_TEAL};">{completed_member}</b> done this week
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ─── Two-column: Activity feed + Goals ───────────────────────────────────────

col_feed, col_goals = st.columns([3, 2])

with col_feed:
    st.markdown(f"### Activity Feed")

    if activities:
        for act in activities:
            actor = act.get("actor_name", "?")
            initials = "".join(w[0].upper() for w in actor.split()[:2])
            action = act.get("action_type", "")
            color_cls = _activity_color_class(action)
            avatar_cls = f"activity-avatar {color_cls}" if color_cls else "activity-avatar"
            desc = _activity_description(act)
            ts = _time_ago(act.get("created_at", ""))

            st.markdown(
                f"""
                <div class="activity-item">
                  <div class="{avatar_cls}">{initials}</div>
                  <div style="flex:1;">
                    <div class="activity-text"><b>{actor}</b> {desc}</div>
                    <div class="activity-time">{ts}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:1rem 0;">No activity recorded yet. '
            'Actions in the CRM, Tasks, and Cards pages appear here.</div>',
            unsafe_allow_html=True,
        )

with col_goals:
    st.markdown(f"### Team Goals")

    active_goals = [g for g in goals if g.get("status") == "active"]
    if active_goals:
        for goal in active_goals:
            title = goal.get("title", "Untitled")
            target = max(1, goal.get("target_value", 1))
            current = goal.get("current_value", 0)
            pct = min(100, round(current / target * 100))
            due = goal.get("due_date", "")
            metric = goal.get("metric_type", "custom").replace("_", " ").title()

            if pct >= 80:
                bar_color = MEDPORT_TEAL
            elif pct >= 50:
                bar_color = "#f59e0b"
            else:
                bar_color = MEDPORT_BLUE

            due_str = f"Due {due}" if due else ""

            st.markdown(
                f"""
                <div class="goal-card">
                  <div class="goal-title">{title}</div>
                  <div class="goal-meta">{metric} &nbsp;·&nbsp; {due_str}</div>
                  <div class="goal-progress-outer">
                    <div class="goal-progress-inner" style="width:{pct}%;background:{bar_color};"></div>
                  </div>
                  <div class="goal-pct">{current} / {target} &nbsp; ({pct}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">No active goals. '
            'Create goals in the Tasks page.</div>',
            unsafe_allow_html=True,
        )

    # My tasks widget
    st.markdown(f"### My Open Tasks")
    my_tasks = [t for t in all_tasks if name in (t.get("assigned_to") or []) and t.get("status") in ("open", "in_progress")]
    if my_tasks:
        for task in my_tasks[:5]:
            title = task.get("title", "")
            priority = task.get("priority", "medium")
            status = task.get("status", "open")
            due = task.get("due_date", "")
            due_str = ""
            if due:
                try:
                    due_dt = datetime.strptime(due, "%Y-%m-%d")
                    days_left = (due_dt - datetime.now()).days
                    if days_left < 0:
                        due_str = f'<span class="task-overdue">OVERDUE ({abs(days_left)}d)</span>'
                    elif days_left <= 2:
                        due_str = f'<span class="task-due-soon">Due in {days_left}d</span>'
                    else:
                        due_str = f'<span style="font-size:0.72rem;color:#6b7a8d;">Due {due}</span>'
                except Exception:
                    due_str = f'<span style="font-size:0.72rem;color:#6b7a8d;">{due}</span>'

            border_color = TASK_STATUS_COLORS.get(status, MEDPORT_BLUE)
            st.markdown(
                f"""
                <div class="task-card" style="border-left-color:{border_color};">
                  <div class="task-title">{title}</div>
                  <div class="task-meta">
                    <span class="badge-priority-{priority}">{priority.upper()}</span>
                    &nbsp;{due_str}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;">No open tasks assigned to you.</div>',
            unsafe_allow_html=True,
        )
