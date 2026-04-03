"""
MedPort Tech Hub — sprint board, AI tracker, personal tasks, and tech team overview.
Access: tech department or admin only.
"""

import os
import sys
from datetime import datetime, timezone, timedelta, date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import (
    inject_css, page_header,
    MEDPORT_TEAL, MEDPORT_BLUE, MEDPORT_DARK,
    DEPT_COLORS, TASK_STATUS_COLORS, PRIORITY_COLORS,
)
from lib.auth import check_auth, is_admin, get_department, render_logout_button
from lib.db import (
    get_tasks, get_tasks_by_department, create_task,
    update_task, get_team_members, get_activity_feed, log_activity,
    get_active_sprint, get_sprint_tasks,
)
from lib.sprint_widget import render_sprint_widget, render_create_sprint_form

st.set_page_config(
    page_title="Tech Hub — MedPort",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)
dept = get_department(email)

TECH_PURPLE = DEPT_COLORS["tech"]  # #8B5CF6

# ─── Access control ──────────────────────────────────────────────────────────

if dept not in ("tech", "leadership") and not admin:
    st.error("This page is for the Tech team.")
    st.page_link("medport_dashboard.py", label="Back to Home", icon="🏠")
    st.stop()

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">MedPort</span>'
        f'<span style="font-size:0.8rem;color:#94a3b8;margin-left:0.4rem;">Team Intelligence Hub</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:0.78rem;color:#94a3b8;margin-top:0.2rem;'>Signed in as <b>{name}</b></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="margin:0.5rem 0;">'
        f'<span style="background:{TECH_PURPLE};color:#fff;font-size:0.72rem;font-weight:700;'
        f'padding:2px 10px;border-radius:20px;letter-spacing:0.04em;">Tech</span>'
        + (
            f'&nbsp;<span style="background:{MEDPORT_TEAL};color:#fff;font-size:0.72rem;font-weight:700;'
            f'padding:2px 10px;border-radius:20px;">Admin</span>'
            if admin else ""
        )
        + f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    render_logout_button()
    st.markdown("---")

    st.page_link("medport_dashboard.py", label="Home", icon="🏠")
    st.page_link("pages/1_Team_Hub.py", label="Team Hub", icon="👥")
    st.page_link("pages/3_Tasks.py", label="Tasks", icon="✅")
    st.page_link("pages/5_AI_Research.py", label="AI Research", icon="🔬")
    st.page_link("pages/12_Announcements.py", label="Announcements", icon="📢")
    st.page_link("pages/13_Standups.py", label="Standups", icon="🎯")
    st.page_link("pages/6_Settings.py", label="Settings", icon="⚙️")

    if admin:
        st.markdown("---")
        st.markdown(
            f"<div style='font-size:0.72rem;color:#94a3b8;font-weight:600;letter-spacing:0.05em;'>ADMIN</div>",
            unsafe_allow_html=True,
        )
        st.page_link("pages/7_Intelligence.py", label="Intelligence", icon="🧠")
        st.page_link("pages/4_Cards.py", label="Cards", icon="🟨")
        st.page_link("pages/2_Outreach_CRM.py", label="Outreach CRM", icon="📋")

    if st.button("Refresh data", use_container_width=True, key="tech_refresh_btn"):
        st.cache_data.clear()
        st.rerun()

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
            return '<span class="task-overdue">Due TODAY</span>'
        elif days_left <= 2:
            return f'<span class="task-due-soon">Due in {days_left}d</span>'
        else:
            return f'<span style="font-size:0.72rem;color:#6b7a8d;">Due {due_str}</span>'
    except Exception:
        return f'<span style="font-size:0.72rem;color:#6b7a8d;">{due_str}</span>'


def _time_ago(ts_str: str) -> str:
    if not ts_str:
        return ""
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        secs = int((now - ts).total_seconds())
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


def _task_card_html(task: dict, show_assigned: bool = True) -> str:
    title = task.get("title", "")
    priority = task.get("priority", "medium")
    status = task.get("status", "open")
    due = task.get("due_date")
    assigned = task.get("assigned_to") or []
    due_html = _due_label(due)
    assigned_html = (
        f'<span style="font-size:0.72rem;color:#6b7a8d;">{", ".join(assigned)}</span>'
        if show_assigned and assigned else ""
    )
    border_color = TASK_STATUS_COLORS.get(status, MEDPORT_BLUE)
    return f"""
    <div class="task-card" style="border-left-color:{border_color};margin-bottom:0.5rem;">
      <div class="task-title">{title}</div>
      <div class="task-meta">
        <span class="badge-priority-{priority}">{priority.upper()}</span>
        <span class="badge-status-{status}">{status.replace("_", " ").title()}</span>
        {"&nbsp;" + due_html if due_html else ""}
        {"&nbsp;" + assigned_html if assigned_html else ""}
      </div>
    </div>
    """


# ─── Load data ───────────────────────────────────────────────────────────────

all_members = get_team_members()
tech_members = [m for m in all_members if m.get("department") == "tech"]
tech_member_names = [m["name"] for m in tech_members]
all_member_names = [m["name"] for m in all_members]

# Fetch tech tasks — try dept function, fall back to filtering all tasks
try:
    tech_tasks = get_tasks_by_department("tech")
    if not tech_tasks:
        raise ValueError("empty")
except Exception:
    all_t = get_tasks()
    tech_tasks = [
        t for t in all_t
        if any(a in tech_member_names for a in (t.get("assigned_to") or []))
    ]

all_tasks = get_tasks()

week_ago = datetime.now(timezone.utc) - timedelta(days=7)

# ─── Tabs ────────────────────────────────────────────────────────────────────

tab_sprint, tab_ai, tab_mine, tab_team = st.tabs(
    ["Sprint Board", "AI Tracker", "My Tasks", "Team"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Sprint Board
# ═══════════════════════════════════════════════════════════════════════════════

with tab_sprint:
    st.markdown(
        page_header("Tech Hub", "Aarya's sprint and engineering command center"),
        unsafe_allow_html=True,
    )

    # Stat cards
    open_count = sum(1 for t in tech_tasks if t.get("status") == "open")
    in_progress_count = sum(1 for t in tech_tasks if t.get("status") == "in_progress")
    blocked_count = sum(1 for t in tech_tasks if t.get("status") == "blocked")
    completed_week = 0
    for t in tech_tasks:
        if t.get("status") == "completed" and t.get("completed_at"):
            try:
                completed_dt = datetime.fromisoformat(t["completed_at"].replace("Z", "+00:00"))
                if completed_dt >= week_ago:
                    completed_week += 1
            except Exception:
                pass

    sc1, sc2, sc3, sc4 = st.columns(4)
    for col, val, label, color in [
        (sc1, open_count, "Open Tasks", MEDPORT_BLUE),
        (sc2, in_progress_count, "In Progress", TECH_PURPLE),
        (sc3, completed_week, "Completed This Week", MEDPORT_TEAL),
        (sc4, blocked_count, "Blocked", "#ef4444"),
    ]:
        with col:
            st.markdown(
                f'<div class="stat-card">'
                f'<div class="stat-value" style="color:{color};">{val}</div>'
                f'<div class="stat-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── My Sprint tasks ───────────────────────────────────────────────────────
    _sprint = get_active_sprint()
    if _sprint:
        _sprint_tasks = get_sprint_tasks(_sprint["id"])
        render_sprint_widget(_sprint, _sprint_tasks, current_email=email, show_my_tasks=True, admin=admin)
    elif admin:
        render_create_sprint_form(email)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Sprint Kanban")

    STATUSES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("blocked", "Blocked"),
    ]
    STATUS_NEXT = {
        "open": "in_progress",
        "in_progress": "completed",
        "blocked": "open",
        "completed": "open",
    }

    kanban_cols = st.columns(4)
    for col_idx, (status_key, status_label) in enumerate(STATUSES):
        col_tasks = [t for t in tech_tasks if t.get("status") == status_key]
        status_color = TASK_STATUS_COLORS.get(status_key, MEDPORT_BLUE)
        with kanban_cols[col_idx]:
            st.markdown(
                f'<div style="font-weight:700;font-size:0.88rem;color:{status_color};'
                f'border-bottom:2px solid {status_color};padding-bottom:0.4rem;margin-bottom:0.75rem;">'
                f'{status_label.upper()} ({len(col_tasks)})</div>',
                unsafe_allow_html=True,
            )
            if not col_tasks:
                st.markdown(
                    '<div style="color:#8a9ab0;font-size:0.82rem;font-style:italic;padding:0.5rem 0;">None</div>',
                    unsafe_allow_html=True,
                )
            for task in sorted(
                col_tasks,
                key=lambda t: {"urgent": 0, "high": 1, "medium": 2, "low": 3}.get(
                    t.get("priority", "medium"), 2
                ),
            ):
                task_id = task.get("id", "")
                st.markdown(_task_card_html(task), unsafe_allow_html=True)

                next_status = STATUS_NEXT.get(status_key, "open")
                next_label = {
                    "in_progress": "Start",
                    "completed": "Complete",
                    "open": "Reopen",
                    "blocked": "Unblock",
                }.get(next_status, next_status.replace("_", " ").title())

                btn_key = f"tech_sprint_move_{status_key}_{task_id}"
                if st.button(
                    next_label,
                    key=btn_key,
                    use_container_width=True,
                ):
                    updates: dict = {"status": next_status}
                    if next_status == "completed":
                        updates["completed_at"] = datetime.now(timezone.utc).isoformat()
                        updates["completed_by"] = email
                    update_task(task_id, updates)
                    log_activity(
                        actor_email=email,
                        actor_name=name,
                        action_type="status_change",
                        entity_type="task",
                        entity_id=task_id,
                        entity_name=task.get("title", ""),
                        details={"old_status": status_key, "new_status": next_status},
                    )
                    get_tasks.clear()
                    try:
                        get_tasks_by_department.clear()
                    except AttributeError:
                        pass
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — AI Tracker
# ═══════════════════════════════════════════════════════════════════════════════

with tab_ai:
    st.markdown("### AI & Product Tasks")

    ai_tasks = [
        t for t in tech_tasks
        if "ai" in (t.get("tags") or []) or "product" in (t.get("tags") or [])
    ]
    debt_tasks = [
        t for t in tech_tasks
        if "debt" in (t.get("tags") or [])
    ]

    if ai_tasks:
        for task in ai_tasks:
            status = task.get("status", "open")
            priority = task.get("priority", "medium")
            due = task.get("due_date")
            due_html = _due_label(due)
            status_color = TASK_STATUS_COLORS.get(status, MEDPORT_BLUE)
            st.markdown(
                f'<div class="task-card" style="border-left-color:{status_color};">'
                f'<div class="task-title">{task.get("title", "")}</div>'
                f'<div class="task-meta">'
                f'<span class="badge-priority-{priority}">{priority.upper()}</span>&nbsp;'
                f'<span class="badge-status-{status}">{status.replace("_"," ").title()}</span>'
                + (f"&nbsp;{due_html}" if due_html else "")
                + f"</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:1rem 0;">'
            'No tasks tagged with "ai" or "product". Tag tasks to track them here.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### Tech Debt")

    if debt_tasks:
        for task in debt_tasks:
            status = task.get("status", "open")
            priority = task.get("priority", "medium")
            due_html = _due_label(task.get("due_date"))
            status_color = TASK_STATUS_COLORS.get(status, MEDPORT_BLUE)
            st.markdown(
                f'<div class="task-card" style="border-left-color:{status_color};">'
                f'<div class="task-title">{task.get("title", "")}</div>'
                f'<div class="task-meta">'
                f'<span class="badge-priority-{priority}">{priority.upper()}</span>&nbsp;'
                f'<span class="badge-status-{status}">{status.replace("_"," ").title()}</span>'
                + (f"&nbsp;{due_html}" if due_html else "")
                + f"</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:1rem 0;">'
            'No tasks tagged with "debt". Tag tech debt tasks to track them here.</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — My Tasks
# ═══════════════════════════════════════════════════════════════════════════════

with tab_mine:
    st.markdown("### My Tasks")

    my_tasks = [t for t in all_tasks if name in (t.get("assigned_to") or [])]

    for group_status, group_label in [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("blocked", "Blocked"),
    ]:
        group_tasks = [t for t in my_tasks if t.get("status") == group_status]
        status_color = TASK_STATUS_COLORS.get(group_status, MEDPORT_BLUE)
        st.markdown(
            f'<div style="font-weight:700;font-size:0.85rem;color:{status_color};'
            f'margin-top:1rem;margin-bottom:0.4rem;">{group_label} ({len(group_tasks)})</div>',
            unsafe_allow_html=True,
        )

        if not group_tasks:
            st.markdown(
                f'<div style="color:#8a9ab0;font-size:0.82rem;font-style:italic;padding:0.2rem 0;">None</div>',
                unsafe_allow_html=True,
            )
            continue

        for task in group_tasks:
            task_id = task.get("id", "")
            title = task.get("title", "")
            due_html = _due_label(task.get("due_date"))
            priority = task.get("priority", "medium")

            st.markdown(
                f'<div class="task-card" style="border-left-color:{status_color};">'
                f'<div class="task-title">{title}</div>'
                f'<div class="task-meta">'
                f'<span class="badge-priority-{priority}">{priority.upper()}</span>'
                + (f"&nbsp;{due_html}" if due_html else "")
                + f"</div></div>",
                unsafe_allow_html=True,
            )

            done_key = f"tech_mine_complete_{task_id}"
            if st.button("Mark Complete", key=done_key):
                update_task(task_id, {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "completed_by": email,
                })
                log_activity(
                    actor_email=email,
                    actor_name=name,
                    action_type="task_completed",
                    entity_type="task",
                    entity_id=task_id,
                    entity_name=title,
                )
                get_tasks.clear()
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Create Tech Task
    with st.expander("Create Tech Task", expanded=False):
        ct_title = st.text_input("Title *", key="tech_ct_title")
        ct_desc = st.text_area("Description", key="tech_ct_desc", height=80)
        ct_col1, ct_col2 = st.columns(2)
        with ct_col1:
            ct_priority = st.selectbox(
                "Priority",
                ["low", "medium", "high", "urgent"],
                index=1,
                key="tech_ct_priority",
            )
            ct_due = st.date_input("Due date (optional)", value=None, key="tech_ct_due")
        with ct_col2:
            ct_assigned = st.multiselect(
                "Assign to *",
                all_member_names,
                default=[name] if name in all_member_names else [],
                key="tech_ct_assigned",
            )

        if st.button("Create Task", type="primary", key="tech_ct_submit"):
            if ct_title.strip() and ct_assigned:
                task_dict = {
                    "title": ct_title.strip(),
                    "description": ct_desc.strip() or None,
                    "assigned_by_email": email,
                    "assigned_by_name": name,
                    "assigned_to": ct_assigned,
                    "task_type": "individual",
                    "priority": ct_priority,
                    "status": "open",
                    "due_date": ct_due.isoformat() if ct_due else None,
                    "tags": ["tech"],
                }
                task_id = create_task(task_dict)
                if task_id:
                    log_activity(
                        actor_email=email,
                        actor_name=name,
                        action_type="task_created",
                        entity_type="task",
                        entity_id=task_id,
                        entity_name=ct_title.strip(),
                        details={"assigned_to": ct_assigned, "priority": ct_priority},
                    )
                    st.success(f"Task created and assigned to {', '.join(ct_assigned)}.")
                    get_tasks.clear()
                    st.rerun()
            else:
                st.warning("Please enter a title and assign to at least one person.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Team
# ═══════════════════════════════════════════════════════════════════════════════

with tab_team:
    st.markdown("### Tech Team")

    activities = get_activity_feed(limit=10)
    tech_emails = {(m.get("email") or "").lower() for m in tech_members}
    tech_names_set = set(tech_member_names)

    if tech_members:
        member_grid = st.columns(min(len(tech_members), 3))
        for idx, member in enumerate(tech_members):
            member_name = member["name"]
            member_role = member.get("role", "Tech")
            avatar_color = member.get("avatar_color", TECH_PURPLE)
            initials = "".join(w[0].upper() for w in member_name.split()[:2])

            open_tasks = sum(
                1 for t in all_tasks
                if member_name in (t.get("assigned_to") or [])
                and t.get("status") in ("open", "in_progress", "blocked")
            )

            with member_grid[idx % 3]:
                st.markdown(
                    f"""
                    <div class="member-card">
                      <div class="member-avatar"
                        style="background:linear-gradient(135deg,{avatar_color},{MEDPORT_BLUE});">
                        {initials}
                      </div>
                      <div class="member-name">{member_name}</div>
                      <div class="member-role">{member_role}</div>
                      <div class="member-stat" style="margin-top:0.5rem;">
                        <b style="color:{TECH_PURPLE};">{open_tasks}</b> open tasks
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;">No tech team members found in the system.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Recent Tech Activity")

    # Filter activity to tech members
    tech_activities = [
        a for a in activities
        if a.get("actor_name") in tech_names_set
        or a.get("actor_email", "").lower() in tech_emails
    ]

    if tech_activities:
        for act in tech_activities:
            actor = act.get("actor_name", "?")
            initials = "".join(w[0].upper() for w in actor.split()[:2])
            entity = act.get("entity_name", "")
            action = act.get("action_type", "").replace("_", " ")
            ts = _time_ago(act.get("created_at", ""))
            st.markdown(
                f"""
                <div class="activity-item">
                  <div class="activity-avatar"
                    style="background:linear-gradient(135deg,{TECH_PURPLE},{MEDPORT_BLUE});">
                    {initials}
                  </div>
                  <div style="flex:1;">
                    <div class="activity-text"><b>{actor}</b> {action} &mdash; <i>{entity}</i></div>
                    <div class="activity-time">{ts}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">'
            'No recent activity from tech team members.</div>',
            unsafe_allow_html=True,
        )
