"""
MedPort Operations Hub — team overview, health tracking, tasks, and cards summary.
Access: operations department or admin only.
"""

import os
import sys
from datetime import datetime, timezone, timedelta, date
from collections import defaultdict

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import (
    inject_css, page_header,
    MEDPORT_TEAL, MEDPORT_BLUE, MEDPORT_DARK,
    DEPT_COLORS, TASK_STATUS_COLORS, PRIORITY_COLORS,
    CARD_GREY, CARD_YELLOW, CARD_RED,
)
from lib.auth import check_auth, is_admin, get_department, render_logout_button
from lib.db import (
    get_tasks, get_tasks_by_department, create_task,
    update_task, get_team_members, get_activity_feed,
    get_cards, get_card_summary, log_activity,
    get_active_sprint, get_sprint_tasks,
)
from lib.sprint_widget import render_sprint_widget, render_create_sprint_form

st.set_page_config(
    page_title="Operations Hub — MedPort",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)
dept = get_department(email)

OPS_AMBER = DEPT_COLORS["operations"]  # #F59E0B

# ─── Access control ──────────────────────────────────────────────────────────

if dept not in ("operations", "leadership") and not admin:
    st.error("This page is for the Operations team.")
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
        f'<span style="background:{OPS_AMBER};color:#fff;font-size:0.72rem;font-weight:700;'
        f'padding:2px 10px;border-radius:20px;letter-spacing:0.04em;">Operations</span>'
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
    st.page_link("pages/4_Cards.py", label="Cards", icon="🟨")
    st.page_link("pages/12_Announcements.py", label="Announcements", icon="📢")
    st.page_link("pages/13_Standups.py", label="Standups", icon="🎯")
    st.page_link("pages/6_Settings.py", label="Settings", icon="⚙️")

    if st.button("Refresh data", use_container_width=True, key="ops_refresh_btn"):
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


def _health_score(card_summary: dict) -> int:
    grey_total = sum(v.get("grey", 0) for v in card_summary.values())
    yellow_total = sum(v.get("yellow", 0) for v in card_summary.values())
    red_total = sum(v.get("red", 0) for v in card_summary.values())
    score = 100 - (grey_total * 5 + yellow_total * 15 + red_total * 30)
    return max(0, score)


# ─── Load data ───────────────────────────────────────────────────────────────

all_members = get_team_members()
all_member_names = [m["name"] for m in all_members]

all_tasks = get_tasks()

# Operations tasks: try dept function, fall back to all tasks
try:
    ops_tasks = get_tasks_by_department("operations")
    if not ops_tasks:
        raise ValueError("empty")
except Exception:
    ops_members = [m for m in all_members if m.get("department") == "operations"]
    ops_names = [m["name"] for m in ops_members]
    ops_tasks = [
        t for t in all_tasks
        if any(a in ops_names for a in (t.get("assigned_to") or []))
    ]

card_summary = get_card_summary()  # dict keyed by email or member id
all_cards = get_cards()

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_overview, tab_health, tab_tasks, tab_cards = st.tabs(
    ["Overview", "Team Health", "Tasks", "Cards Summary"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview
# ═══════════════════════════════════════════════════════════════════════════════

with tab_overview:
    st.markdown(
        page_header("Operations Hub", "Nathen's team operations command center"),
        unsafe_allow_html=True,
    )

    # Stat card calculations
    team_size = len(all_members)

    # Active cards — cards with is_active=True
    active_cards_count = sum(1 for c in all_cards if c.get("is_active", False))

    open_tasks_count = sum(
        1 for t in all_tasks if t.get("status") in ("open", "in_progress", "blocked")
    )

    health = _health_score(card_summary)
    health_color = MEDPORT_TEAL if health >= 80 else (OPS_AMBER if health >= 50 else "#ef4444")

    sc1, sc2, sc3, sc4 = st.columns(4)
    for col, val, label, color in [
        (sc1, team_size, "Team Size", OPS_AMBER),
        (sc2, active_cards_count, "Active Cards", "#ef4444"),
        (sc3, open_tasks_count, "Open Tasks", MEDPORT_BLUE),
        (sc4, f"{health}", "Team Health Score", health_color),
    ]:
        with col:
            st.markdown(
                f'<div class="stat-card">'
                f'<div class="stat-value" style="color:{color};">{val}</div>'
                f'<div class="stat-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Sprint widget ─────────────────────────────────────────────────────────
    _sprint = get_active_sprint()
    if _sprint:
        _sprint_tasks = get_sprint_tasks(_sprint["id"])
        render_sprint_widget(_sprint, _sprint_tasks, current_email=email, show_my_tasks=True, admin=admin)
    elif admin:
        render_create_sprint_form(email)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Recent Activity")

    activities = get_activity_feed(limit=6)
    if activities:
        for act in activities:
            actor = act.get("actor_name", "?")
            initials = "".join(w[0].upper() for w in actor.split()[:2])
            entity = act.get("entity_name", "")
            action = act.get("action_type", "").replace("_", " ")
            ts = _time_ago(act.get("created_at", ""))

            # Color avatar based on action type
            avatar_bg = {
                "task_completed": MEDPORT_TEAL,
                "goal_updated": MEDPORT_TEAL,
                "card_issued": "#ef4444",
            }.get(act.get("action_type", ""), OPS_AMBER)

            st.markdown(
                f"""
                <div class="activity-item">
                  <div class="activity-avatar"
                    style="background:linear-gradient(135deg,{avatar_bg},{MEDPORT_BLUE});">
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
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:1rem 0;">'
            'No recent activity recorded.</div>',
            unsafe_allow_html=True,
        )

    # ── Operations Team ───────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Operations Team")
    if ops_members:
        _ocols = st.columns(min(len(ops_members), 3))
        for _oi, _om in enumerate(ops_members):
            _oname = _om.get("name", "")
            _orole = _om.get("role", "")
            _oavatar = _om.get("avatar_color") or OPS_AMBER
            _oinitials = "".join(w[0].upper() for w in _oname.split()[:2]) if _oname else "?"
            with _ocols[_oi % 3]:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:0.7rem;padding:0.6rem 0.8rem;'
                    f'background:#1e293b;border-radius:0.6rem;margin-bottom:0.5rem;">'
                    f'<div style="width:34px;height:34px;border-radius:50%;background:{_oavatar};'
                    f'display:flex;align-items:center;justify-content:center;font-weight:700;'
                    f'font-size:0.85rem;color:#fff;flex-shrink:0;">{_oinitials}</div>'
                    f'<div><div style="font-weight:600;font-size:0.88rem;color:#e2e8f0;">{_oname}</div>'
                    f'<div style="font-size:0.75rem;color:#64748b;">{_orole}</div></div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.caption("No members assigned to Operations yet. Set department in Settings.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Team Health
# ═══════════════════════════════════════════════════════════════════════════════

with tab_health:
    st.markdown("### Team Health Overview")

    STATUS_DISPLAY = {
        "good": ("Good Standing", "standing-good"),
        "grey_warning": ("Grey Warning", "standing-grey"),
        "yellow_warning": ("Yellow Warning", "standing-yellow"),
        "review": ("Under Review", "standing-review"),
        "removed": ("Removed", "standing-removed"),
    }

    # Build task count per member
    open_tasks_by_member: dict[str, int] = defaultdict(int)
    for t in all_tasks:
        if t.get("status") in ("open", "in_progress", "blocked"):
            for assignee in (t.get("assigned_to") or []):
                open_tasks_by_member[assignee] += 1

    if all_members:
        grid_cols = st.columns(min(len(all_members), 3))
        for idx, member in enumerate(all_members):
            member_name = member["name"]
            member_dept = member.get("department", "unassigned")
            avatar_color = member.get("avatar_color", MEDPORT_TEAL)
            initials = "".join(w[0].upper() for w in member_name.split()[:2])
            dept_color = DEPT_COLORS.get(member_dept, DEPT_COLORS["unassigned"])

            # Find card summary for this member (keyed by email or name)
            member_email_key = (member.get("email") or "").lower()
            member_data = card_summary.get(member_email_key)
            if not member_data:
                # Fall back to searching by name
                for k, v in card_summary.items():
                    if v.get("name") == member_name:
                        member_data = v
                        break

            grey_n = member_data["grey"] if member_data else 0
            yellow_n = member_data["yellow"] if member_data else 0
            red_n = member_data["red"] if member_data else 0
            standing = member_data["status"] if member_data else "good"
            status_label, status_css = STATUS_DISPLAY.get(standing, ("Good Standing", "standing-good"))
            task_count = open_tasks_by_member.get(member_name, 0)

            with grid_cols[idx % 3]:
                st.markdown(
                    f"""
                    <div class="member-card">
                      <div class="member-avatar"
                        style="background:linear-gradient(135deg,{avatar_color},{MEDPORT_BLUE});">
                        {initials}
                      </div>
                      <div class="member-name">{member_name}</div>
                      <div class="member-role"
                        style="color:{dept_color};font-weight:600;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.04em;">
                        {member_dept.title()}
                      </div>
                      <div style="margin:0.5rem 0;">
                        <span class="card-grey">Grey: {grey_n}</span>&nbsp;
                        <span class="card-yellow">Yellow: {yellow_n}</span>&nbsp;
                        <span class="card-red">Red: {red_n}</span>
                      </div>
                      <div style="margin-bottom:0.5rem;">
                        <span class="{status_css}">{status_label}</span>
                      </div>
                      <div class="member-stat">
                        <b style="color:{MEDPORT_BLUE};">{task_count}</b> open tasks
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;">No team members found.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Workload Distribution")

    # Bar chart of open tasks per member
    if open_tasks_by_member:
        chart_data = {
            m["name"]: open_tasks_by_member.get(m["name"], 0)
            for m in all_members
        }
        import pandas as pd
        df_chart = pd.DataFrame.from_dict(
            chart_data, orient="index", columns=["Open Tasks"]
        )
        st.bar_chart(df_chart, use_container_width=True, color=OPS_AMBER)
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">No open tasks to display.</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Tasks
# ═══════════════════════════════════════════════════════════════════════════════

with tab_tasks:
    st.markdown("### Operations Tasks")

    # Filter control
    task_filter = st.selectbox(
        "Filter",
        ["all", "open", "in_progress", "overdue"],
        format_func=lambda s: {
            "all": "All Tasks",
            "open": "Open",
            "in_progress": "In Progress",
            "overdue": "Overdue",
        }.get(s, s),
        key="ops_task_filter",
    )

    today = date.today()

    def _is_overdue(t: dict) -> bool:
        due = t.get("due_date")
        if not due or t.get("status") == "completed":
            return False
        try:
            return datetime.strptime(due, "%Y-%m-%d").date() < today
        except Exception:
            return False

    if task_filter == "all":
        display_tasks = ops_tasks
    elif task_filter == "open":
        display_tasks = [t for t in ops_tasks if t.get("status") == "open"]
    elif task_filter == "in_progress":
        display_tasks = [t for t in ops_tasks if t.get("status") == "in_progress"]
    elif task_filter == "overdue":
        display_tasks = [t for t in ops_tasks if _is_overdue(t)]
    else:
        display_tasks = ops_tasks

    if display_tasks:
        for task in sorted(
            display_tasks,
            key=lambda t: {"urgent": 0, "high": 1, "medium": 2, "low": 3}.get(
                t.get("priority", "medium"), 2
            ),
        ):
            status = task.get("status", "open")
            priority = task.get("priority", "medium")
            due_html = _due_label(task.get("due_date"))
            assigned = task.get("assigned_to") or []
            border_color = TASK_STATUS_COLORS.get(status, MEDPORT_BLUE)

            st.markdown(
                f'<div class="task-card" style="border-left-color:{border_color};">'
                f'<div class="task-title">{task.get("title", "")}</div>'
                f'<div class="task-meta">'
                f'<span class="badge-priority-{priority}">{priority.upper()}</span>&nbsp;'
                f'<span class="badge-status-{status}">{status.replace("_", " ").title()}</span>'
                + (f"&nbsp;{due_html}" if due_html else "")
                + (
                    f'&nbsp;<span style="font-size:0.72rem;color:#6b7a8d;">{", ".join(assigned)}</span>'
                    if assigned else ""
                )
                + f"</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:1rem 0;">No tasks match this filter.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Create task (ops members and admin)
    can_create = admin or dept in ("operations", "leadership")
    if can_create:
        with st.expander("Create Operations Task", expanded=False):
            ot_title = st.text_input("Title *", key="ops_ot_title")
            ot_desc = st.text_area("Description", key="ops_ot_desc", height=80)
            ot_col1, ot_col2 = st.columns(2)
            with ot_col1:
                ot_priority = st.selectbox(
                    "Priority",
                    ["low", "medium", "high", "urgent"],
                    index=1,
                    key="ops_ot_priority",
                )
                ot_due = st.date_input("Due date (optional)", value=None, key="ops_ot_due")
            with ot_col2:
                ot_assigned = st.multiselect(
                    "Assign to *",
                    all_member_names,
                    default=[name] if name in all_member_names else [],
                    key="ops_ot_assigned",
                )

            if st.button("Create Task", type="primary", key="ops_ot_submit"):
                if ot_title.strip() and ot_assigned:
                    task_dict = {
                        "title": ot_title.strip(),
                        "description": ot_desc.strip() or None,
                        "assigned_by_email": email,
                        "assigned_by_name": name,
                        "assigned_to": ot_assigned,
                        "task_type": "individual",
                        "priority": ot_priority,
                        "status": "open",
                        "due_date": ot_due.isoformat() if ot_due else None,
                        "tags": ["operations"],
                    }
                    task_id = create_task(task_dict)
                    if task_id:
                        log_activity(
                            actor_email=email,
                            actor_name=name,
                            action_type="task_created",
                            entity_type="task",
                            entity_id=task_id,
                            entity_name=ot_title.strip(),
                            details={"assigned_to": ot_assigned, "priority": ot_priority},
                        )
                        st.success(f"Task created and assigned to {', '.join(ot_assigned)}.")
                        get_tasks.clear()
                        try:
                            get_tasks_by_department.clear()
                        except AttributeError:
                            pass
                        st.rerun()
                else:
                    st.warning("Please enter a title and assign to at least one person.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Cards Summary
# ═══════════════════════════════════════════════════════════════════════════════

with tab_cards:
    st.markdown("### Cards Summary")

    # Alert: anyone with 2+ red cards
    red_alert_members = []
    for k, v in card_summary.items():
        if v.get("red", 0) >= 2:
            red_alert_members.append(v.get("name", k))

    if red_alert_members:
        st.markdown(
            f'<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:0.75rem;'
            f'padding:0.75rem 1rem;margin-bottom:1rem;color:#991b1b;font-weight:600;font-size:0.9rem;">'
            f'Red Card Alert: {", ".join(red_alert_members)} '
            f'{"has" if len(red_alert_members) == 1 else "have"} 2 or more red cards. '
            f'Team review required.</div>',
            unsafe_allow_html=True,
        )

    STATUS_DISPLAY = {
        "good": ("Good Standing", "standing-good"),
        "grey_warning": ("Grey Warning", "standing-grey"),
        "yellow_warning": ("Yellow Warning", "standing-yellow"),
        "review": ("Under Review", "standing-review"),
        "removed": ("Removed", "standing-removed"),
    }

    # Per-member card timeline
    for member in all_members:
        member_name = member["name"]
        member_email_key = (member.get("email") or "").lower()

        member_cards = [
            c for c in all_cards if c.get("member_name") == member_name
        ]
        recent_cards = sorted(
            member_cards,
            key=lambda c: c.get("created_at", ""),
            reverse=True,
        )[:5]

        member_data = card_summary.get(member_email_key)
        if not member_data:
            for k, v in card_summary.items():
                if v.get("name") == member_name:
                    member_data = v
                    break

        grey_n = member_data["grey"] if member_data else 0
        yellow_n = member_data["yellow"] if member_data else 0
        red_n = member_data["red"] if member_data else 0
        standing = member_data["status"] if member_data else "good"
        status_label, status_css = STATUS_DISPLAY.get(standing, ("Good Standing", "standing-good"))
        total_count = len(member_cards)

        expander_label = (
            f"{member_name} — "
            f"Grey: {grey_n}  Yellow: {yellow_n}  Red: {red_n}  "
            f"({status_label})"
        )

        with st.expander(expander_label, expanded=red_n >= 2):
            st.markdown(
                f'<span class="{status_css}">{status_label}</span>'
                f'&nbsp;<span style="font-size:0.78rem;color:#6b7a8d;">'
                f'{total_count} card{"s" if total_count != 1 else ""} total</span>',
                unsafe_allow_html=True,
            )

            if recent_cards:
                st.markdown(
                    f'<div style="font-size:0.82rem;font-weight:600;color:#475569;'
                    f'margin:0.75rem 0 0.4rem;">Most recent {len(recent_cards)} card{"s" if len(recent_cards) != 1 else ""}:</div>',
                    unsafe_allow_html=True,
                )
                for card in recent_cards:
                    card_type = card.get("card_type", "grey")
                    reason = card.get("reason", "")
                    issued_by = card.get("issued_by_name", "")
                    created_at = card.get("created_at", "")
                    is_active = card.get("is_active", True)
                    auto_escalated = bool(card.get("auto_escalated_from"))

                    try:
                        ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        date_str = ts.strftime("%b %d, %Y")
                    except Exception:
                        date_str = created_at[:10] if created_at else ""

                    type_color = {
                        "grey": CARD_GREY,
                        "yellow": CARD_YELLOW,
                        "red": CARD_RED,
                    }.get(card_type, CARD_GREY)
                    inactive_style = "opacity:0.5;" if not is_active else ""
                    auto_badge = (
                        '<span style="font-size:0.7rem;background:#e8f4fd;color:#2980b9;'
                        'padding:1px 7px;border-radius:10px;">Auto-escalated</span>'
                        if auto_escalated else ""
                    )

                    st.markdown(
                        f"""
                        <div style="border-left:3px solid {type_color};padding:0.45rem 0.7rem;
                          margin:0.35rem 0;background:#fafafa;border-radius:0 6px 6px 0;{inactive_style}">
                          <div style="display:flex;align-items:center;gap:0.5rem;">
                            <span class="card-{card_type}">{card_type.upper()}</span>
                            {auto_badge}
                            <span style="font-size:0.72rem;color:#8a9ab0;margin-left:auto;">{date_str}</span>
                          </div>
                          <div style="font-size:0.85rem;color:#1a2a3a;margin-top:0.25rem;">{reason}</div>
                          <div style="font-size:0.72rem;color:#6b7a8d;margin-top:0.15rem;">
                            Issued by {issued_by}
                            {"&nbsp;&mdash;&nbsp;<i>Inactive</i>" if not is_active else ""}
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div style="color:#8a9ab0;font-size:0.85rem;padding:0.3rem 0;">'
                    'No cards on record.</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # Admin card issuance form
    if admin:
        st.markdown("---")
        st.markdown("### Issue a Card")

        from lib.styles import TEAM_EMAILS
        ic_col1, ic_col2 = st.columns([2, 3])
        with ic_col1:
            ic_member = st.selectbox(
                "Team member *",
                all_member_names,
                key="ops_ic_member",
            )
            ic_type = st.selectbox(
                "Card type *",
                ["grey", "yellow", "red"],
                format_func=lambda t: {
                    "grey": "Grey (informal warning)",
                    "yellow": "Yellow (formal warning)",
                    "red": "Red (serious breach)",
                }.get(t, t),
                key="ops_ic_type",
            )
        with ic_col2:
            ic_reason = st.text_area(
                "Reason *",
                height=100,
                key="ops_ic_reason",
                placeholder="Describe specifically what happened and why this card is being issued...",
            )

        if st.button("Issue Card", type="primary", key="ops_do_issue_card"):
            if ic_reason.strip():
                try:
                    team_email_map: dict = {}
                    raw = st.secrets.get("TEAM_MEMBER_EMAILS", "")
                    if raw:
                        for pair in raw.split(","):
                            if ":" in pair:
                                k, v = pair.split(":", 1)
                                team_email_map[k.strip()] = v.strip()
                    team_email_map.update(TEAM_EMAILS)
                except Exception:
                    team_email_map = TEAM_EMAILS

                member_email_val = team_email_map.get(
                    ic_member,
                    f"{ic_member.lower().replace(' ', '.')}@medport.ca",
                )

                from lib.db import issue_card
                card_dict = {
                    "member_email": member_email_val,
                    "member_name": ic_member,
                    "card_type": ic_type,
                    "reason": ic_reason.strip(),
                    "issued_by_email": email,
                    "issued_by_name": name,
                    "is_active": True,
                }
                card_id, escalation_msg = issue_card(card_dict)
                if card_id:
                    log_activity(
                        actor_email=email,
                        actor_name=name,
                        action_type="card_issued",
                        entity_type="card",
                        entity_id=card_id,
                        entity_name=ic_member,
                        details={"card_type": ic_type, "reason": ic_reason.strip()},
                    )
                    st.success(f"{ic_type.capitalize()} card issued to {ic_member}.")
                    if escalation_msg:
                        st.warning(f"Auto-escalation: {escalation_msg}")
                    get_cards.clear()
                    try:
                        get_card_summary.clear()
                    except AttributeError:
                        pass
                    st.rerun()
            else:
                st.warning("Please provide a reason for this card.")
    else:
        st.info("Only admins can issue cards. Contact Arav if a card should be issued.")
