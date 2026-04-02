"""
MedPort Tasks — task management, team goals, and Google Calendar sync info.
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta, date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import (
    inject_css, MEDPORT_BLUE, MEDPORT_GREEN, MEDPORT_TEAL, TEAM_MEMBERS,
    PRIORITY_COLORS, TASK_STATUS_COLORS,
)
from lib.auth import check_auth, is_admin
from lib.db import (
    load_prospects, get_tasks, create_task, update_task,
    get_goals, create_goal, update_goal, log_activity, get_team_members,
)

st.set_page_config(
    page_title="Tasks — MedPort",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _due_label(due_str: str | None) -> str:
    if not due_str:
        return ""
    try:
        due_dt = datetime.strptime(due_str, "%Y-%m-%d").date()
        today = date.today()
        days_left = (due_dt - today).days
        if days_left < 0:
            return f'<span class="task-overdue">OVERDUE ({abs(days_left)}d)</span>'
        elif days_left == 0:
            return f'<span class="task-overdue">Due TODAY</span>'
        elif days_left <= 2:
            return f'<span class="task-due-soon">Due in {days_left}d</span>'
        else:
            return f'<span style="font-size:0.72rem;color:#6b7a8d;">Due {due_str}</span>'
    except Exception:
        return f'<span style="font-size:0.72rem;color:#6b7a8d;">{due_str}</span>'


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">Tasks</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='font-size:0.8rem;color:#94a3b8;'>{name}</div>", unsafe_allow_html=True)
    st.markdown("---")

    try:
        auth_configured = bool(st.secrets.get("auth", {}))
    except Exception:
        auth_configured = False
    if auth_configured and os.environ.get("LOCAL_DEV", "false").lower() != "true":
        if st.button("Sign out"):
            st.logout()

    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ─── Load data ───────────────────────────────────────────────────────────────

all_tasks = get_tasks()
goals = get_goals()
df = load_prospects()
_dynamic_members = get_team_members()
_dynamic_member_names = [m["name"] for m in _dynamic_members]
prospect_options = (
    [{"id": "", "name": "None"}]
    + [{"id": str(row["id"]), "name": row.get("name", "")} for _, row in df.iterrows()]
    if not df.empty else [{"id": "", "name": "None"}]
)

# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown("# Tasks")
st.markdown(
    f'<div style="color:#6b7a8d;font-size:0.88rem;margin-top:-0.6rem;margin-bottom:1.2rem;">'
    f'Team tasks, goals, and deadlines'
    f'</div>',
    unsafe_allow_html=True,
)

# ─── Create Task (admin only) ─────────────────────────────────────────────────

if admin:
    with st.expander("Create New Task", expanded=False):
        t_title = st.text_input("Title *", key="new_task_title")
        t_desc = st.text_area("Description", key="new_task_desc", height=80)
        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1:
            t_assigned = st.multiselect(
                "Assign to *",
                _dynamic_member_names,
                key="new_task_assigned",
            )
            t_type = st.selectbox(
                "Task type",
                ["individual", "group", "team_goal"],
                key="new_task_type",
            )
        with t_col2:
            t_priority = st.selectbox(
                "Priority",
                ["low", "medium", "high", "urgent"],
                index=1,
                key="new_task_priority",
            )
            t_due = st.date_input("Due date (optional)", value=None, key="new_task_due")
        with t_col3:
            prospect_names = ["None"] + [p["name"] for p in prospect_options if p["id"]]
            t_prospect_name = st.selectbox("Linked prospect", prospect_names, key="new_task_prospect")
            t_prospect_id = ""
            if t_prospect_name != "None":
                match = next((p for p in prospect_options if p["name"] == t_prospect_name), None)
                if match:
                    t_prospect_id = match["id"]

        if st.button("Create Task", type="primary", key="do_create_task"):
            if t_title.strip() and t_assigned:
                task_dict = {
                    "title": t_title.strip(),
                    "description": t_desc.strip() or None,
                    "assigned_by_email": email,
                    "assigned_by_name": name,
                    "assigned_to": t_assigned,
                    "task_type": t_type,
                    "priority": t_priority,
                    "status": "open",
                    "due_date": t_due.isoformat() if t_due else None,
                    "prospect_id": t_prospect_id or None,
                    "prospect_name": t_prospect_name if t_prospect_name != "None" else None,
                }
                task_id = create_task(task_dict)
                if task_id:
                    log_activity(
                        actor_email=email, actor_name=name,
                        action_type="task_created", entity_type="task",
                        entity_id=task_id, entity_name=t_title.strip(),
                        details={"assigned_to": t_assigned, "priority": t_priority},
                    )
                    st.success(f"Task created and assigned to {', '.join(t_assigned)}.")
                    get_tasks.clear()
                    st.rerun()
            else:
                st.warning("Please enter a title and assign to at least one person.")

st.markdown("")

# ─── Two columns: My Tasks + All Team Tasks ───────────────────────────────────

left_col, right_col = st.columns([2, 3])

with left_col:
    st.markdown(f"### My Tasks")

    my_tasks = [
        t for t in all_tasks
        if name in (t.get("assigned_to") or [])
    ]

    # Filter controls
    status_filter = st.multiselect(
        "Filter by status",
        ["open", "in_progress", "completed", "blocked"],
        default=["open", "in_progress"],
        key="my_task_status_filter",
        format_func=lambda s: s.replace("_", " ").title(),
    )
    my_tasks_filtered = [t for t in my_tasks if t.get("status") in status_filter]

    if not my_tasks_filtered:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">No tasks match this filter.</div>',
            unsafe_allow_html=True,
        )
    else:
        for task in my_tasks_filtered:
            task_id = task.get("id", "")
            title = task.get("title", "")
            desc = task.get("description", "")
            priority = task.get("priority", "medium")
            status = task.get("status", "open")
            due = task.get("due_date")
            prospect = task.get("prospect_name", "")
            border_color = TASK_STATUS_COLORS.get(status, MEDPORT_BLUE)
            due_html = _due_label(due)

            with st.container():
                st.markdown(
                    f"""
                    <div class="task-card" style="border-left-color:{border_color};">
                      <div class="task-title">{title}</div>
                      <div class="task-meta">
                        <span class="badge-priority-{priority}">{priority.upper()}</span>
                        <span class="badge-status-{status}">{status.replace("_"," ").title()}</span>
                        {"&nbsp;" + due_html if due_html else ""}
                        {"&nbsp;<span style='font-size:0.72rem;color:#6b7a8d;'>Re: " + prospect + "</span>" if prospect else ""}
                      </div>
                      {"<div style='font-size:0.8rem;color:#5a6a7a;margin-top:4px;'>" + desc + "</div>" if desc else ""}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                act_col1, act_col2 = st.columns([3, 2])
                with act_col1:
                    new_status = st.selectbox(
                        "Status",
                        ["open", "in_progress", "completed", "blocked"],
                        index=["open", "in_progress", "completed", "blocked"].index(status) if status in ["open", "in_progress", "completed", "blocked"] else 0,
                        format_func=lambda s: s.replace("_", " ").title(),
                        key=f"my_status_{task_id}",
                        label_visibility="collapsed",
                    )
                with act_col2:
                    if st.button("Update", key=f"my_update_{task_id}", use_container_width=True):
                        upd: dict = {"status": new_status}
                        if new_status == "completed" and status != "completed":
                            upd["completed_at"] = datetime.now(timezone.utc).isoformat()
                            upd["completed_by"] = email
                            log_activity(
                                actor_email=email, actor_name=name,
                                action_type="task_completed", entity_type="task",
                                entity_id=task_id, entity_name=title,
                            )
                        update_task(task_id, upd)
                        get_tasks.clear()
                        st.rerun()

                st.markdown("")

with right_col:
    st.markdown(f"### All Team Tasks")

    # Group by assignee
    from collections import defaultdict

    tasks_by_assignee: dict[str, list] = defaultdict(list)
    for t in all_tasks:
        if t.get("status") in ("open", "in_progress", "blocked"):
            for assignee in (t.get("assigned_to") or []):
                tasks_by_assignee[assignee].append(t)

    # Show each team member
    member_tabs = _dynamic_member_names if _dynamic_member_names else [m for m in TEAM_MEMBERS if m != "Unassigned"]
    if member_tabs:
        tabs = st.tabs(member_tabs)
        for i, member in enumerate(member_tabs):
            with tabs[i]:
                member_task_list = tasks_by_assignee.get(member, [])
                if not member_task_list:
                    st.markdown(
                        f'<div style="color:#8a9ab0;font-size:0.88rem;">No open tasks for {member}.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    for task in sorted(member_task_list, key=lambda t: (
                        {"urgent": 0, "high": 1, "medium": 2, "low": 3}.get(t.get("priority", "medium"), 2)
                    )):
                        title = task.get("title", "")
                        priority = task.get("priority", "medium")
                        status = task.get("status", "open")
                        due = task.get("due_date")
                        due_html = _due_label(due)
                        border_color = TASK_STATUS_COLORS.get(status, MEDPORT_BLUE)

                        st.markdown(
                            f"""
                            <div class="task-card" style="border-left-color:{border_color};">
                              <div class="task-title">{title}</div>
                              <div class="task-meta">
                                <span class="badge-priority-{priority}">{priority.upper()}</span>
                                <span class="badge-status-{status}">{status.replace("_"," ").title()}</span>
                                {"&nbsp;" + due_html if due_html else ""}
                              </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ─── Team Goals ──────────────────────────────────────────────────────────────

st.markdown("## Team Goals")

# Create goal (admin only)
if admin:
    with st.expander("Create New Goal", expanded=False):
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            g_title = st.text_input("Goal title *", key="new_goal_title")
            g_desc = st.text_area("Description", key="new_goal_desc", height=60)
            g_metric = st.selectbox(
                "Metric type",
                ["demos_booked", "emails_sent", "converted", "custom"],
                key="new_goal_metric",
            )
        with g_col2:
            g_target = st.number_input("Target value", min_value=1, value=10, key="new_goal_target")
            g_due = st.date_input("Due date (optional)", value=None, key="new_goal_due")

        if st.button("Create Goal", type="primary", key="do_create_goal"):
            if g_title.strip():
                goal_id = create_goal({
                    "title": g_title.strip(),
                    "description": g_desc.strip() or None,
                    "target_value": int(g_target),
                    "current_value": 0,
                    "metric_type": g_metric,
                    "due_date": g_due.isoformat() if g_due else None,
                    "status": "active",
                    "created_by_email": email,
                })
                if goal_id:
                    log_activity(
                        actor_email=email, actor_name=name,
                        action_type="goal_updated", entity_type="goal",
                        entity_id=goal_id, entity_name=g_title.strip(),
                        details={"action": "created", "target": int(g_target)},
                    )
                    st.success("Goal created.")
                    get_goals.clear()
                    st.rerun()
            else:
                st.warning("Please enter a goal title.")

active_goals = [g for g in goals if g.get("status") == "active"]
completed_goals = [g for g in goals if g.get("status") == "completed"]

if active_goals:
    g_cols = st.columns(min(len(active_goals), 3))
    for i, goal in enumerate(active_goals):
        with g_cols[i % 3]:
            goal_id = goal.get("id", "")
            title = goal.get("title", "")
            target = max(1, goal.get("target_value", 1))
            current = goal.get("current_value", 0)
            pct = min(100, round(current / target * 100))
            due = goal.get("due_date", "")
            metric = goal.get("metric_type", "custom").replace("_", " ").title()

            bar_color = MEDPORT_TEAL if pct >= 80 else ("#f59e0b" if pct >= 50 else MEDPORT_BLUE)

            st.markdown(
                f"""
                <div class="goal-card">
                  <div class="goal-title">{title}</div>
                  <div class="goal-meta">{metric} &nbsp;·&nbsp; {"Due " + due if due else "No deadline"}</div>
                  <div class="goal-progress-outer">
                    <div class="goal-progress-inner" style="width:{pct}%;background:{bar_color};"></div>
                  </div>
                  <div class="goal-pct">{current} / {target} &nbsp; ({pct}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if admin:
                with st.expander("Update progress", expanded=False):
                    new_val = st.number_input(
                        "Current value", min_value=0, max_value=target * 10,
                        value=current, key=f"goal_update_{goal_id}",
                    )
                    new_goal_status = st.selectbox(
                        "Goal status", ["active", "completed", "paused"],
                        index=["active", "completed", "paused"].index(goal.get("status", "active")),
                        key=f"goal_status_{goal_id}",
                    )
                    if st.button("Save", key=f"goal_save_{goal_id}"):
                        update_goal(goal_id, {
                            "current_value": int(new_val),
                            "status": new_goal_status,
                        })
                        log_activity(
                            actor_email=email, actor_name=name,
                            action_type="goal_updated", entity_type="goal",
                            entity_id=goal_id, entity_name=title,
                            details={"old_value": current, "new_value": int(new_val)},
                        )
                        get_goals.clear()
                        st.rerun()
else:
    st.markdown(
        '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">No active goals. Use the form above to create one.</div>',
        unsafe_allow_html=True,
    )

if completed_goals:
    with st.expander(f"Completed Goals ({len(completed_goals)})", expanded=False):
        for goal in completed_goals:
            target = max(1, goal.get("target_value", 1))
            current = goal.get("current_value", 0)
            st.markdown(
                f'<span style="color:{MEDPORT_TEAL};font-weight:700;">✓</span> '
                f'**{goal.get("title", "")}** — {current}/{target}',
                unsafe_allow_html=True,
            )

st.markdown("---")

# ─── Google Calendar sync info ───────────────────────────────────────────────

st.markdown("## Google Calendar Sync")

with st.expander("Setup Instructions & Sync", expanded=False):
    st.markdown("""
**To enable Google Calendar sync for tasks with due dates:**

1. Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the **Google Calendar API**
3. Create a **Service Account** and download the JSON key
4. Share your Google Calendar with the service account email (give it "Make changes to events" permission)
5. Add the JSON key to Streamlit secrets as `GOOGLE_SERVICE_ACCOUNT_JSON` (paste the entire JSON as a string)
6. Add your calendar ID as `GOOGLE_CALENDAR_ID` (usually your email address for the primary calendar)

Once configured, the Sync button below will create/update calendar events for all tasks with due dates.
    """)

    cal_configured = False
    try:
        cal_configured = bool(st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", ""))
    except Exception:
        pass

    if cal_configured:
        if st.button("Sync Tasks to Google Calendar", type="primary", key="gcal_sync"):
            tasks_with_due = [t for t in all_tasks if t.get("due_date") and t.get("status") != "completed"]

            try:
                import json
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                sa_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
                creds = service_account.Credentials.from_service_account_info(
                    sa_info, scopes=["https://www.googleapis.com/auth/calendar"]
                )
                service = build("calendar", "v3", credentials=creds)
                cal_id = st.secrets.get("GOOGLE_CALENDAR_ID", "primary")

                synced = 0
                for task in tasks_with_due:
                    event_body = {
                        "summary": f"[MedPort] {task.get('title', '')}",
                        "description": task.get("description", ""),
                        "start": {"date": task["due_date"]},
                        "end": {"date": task["due_date"]},
                        "colorId": "3" if task.get("priority") == "urgent" else "7",
                    }
                    existing_event_id = task.get("google_calendar_event_id")
                    if existing_event_id:
                        try:
                            service.events().update(
                                calendarId=cal_id, eventId=existing_event_id, body=event_body
                            ).execute()
                        except Exception:
                            result = service.events().insert(calendarId=cal_id, body=event_body).execute()
                            update_task(task["id"], {"google_calendar_event_id": result["id"]})
                    else:
                        result = service.events().insert(calendarId=cal_id, body=event_body).execute()
                        update_task(task["id"], {"google_calendar_event_id": result["id"]})
                    synced += 1

                st.success(f"Synced {synced} tasks to Google Calendar.")
            except ImportError:
                st.error("Google API packages not installed. Run: pip install google-api-python-client google-auth")
            except Exception as e:
                st.error(f"Sync failed: {e}")
    else:
        st.info("Google Calendar sync is not yet configured. Follow the setup instructions above, then add secrets to your Streamlit deployment.")
