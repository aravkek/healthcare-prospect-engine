"""
MedPort Finance Hub — Advait's financial command center.
Access: finance dept or admin only.
"""

import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import (
    inject_css,
    MEDPORT_TEAL,
    MEDPORT_BLUE,
    MEDPORT_DARK,
    MEDPORT_DARK_CARD,
    DEPT_COLORS,
    DEPT_LABELS,
    STATUS_COLORS,
    STATUS_LABELS,
    PIPELINE_STAGES,
    TASK_STATUS_COLORS,
    page_header,
)
from lib.auth import check_auth, is_admin, render_logout_button, get_department
from lib.db import (
    load_prospects,
    get_goals,
    create_goal,
    update_goal,
    get_tasks,
    get_tasks_by_department,
    log_activity,
    get_active_sprint,
    get_sprint_tasks,
)
from lib.sprint_widget import render_sprint_widget, render_create_sprint_form

st.set_page_config(
    page_title="Finance Hub — MedPort",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)
dept = get_department(email)

# ─── Access control ───────────────────────────────────────────────────────────

if dept not in ("finance", "leadership") and not admin:
    st.markdown(
        f"""
        <div style="padding:2rem;background:#1e293b;border-radius:1rem;
          border-left:4px solid #ef4444;margin-top:2rem;max-width:560px;">
          <div style="font-size:1.1rem;font-weight:700;color:#ef4444;margin-bottom:0.5rem;">
            Access Denied
          </div>
          <div style="font-size:0.9rem;color:#94a3b8;">
            The Finance Hub is only available to the finance team.
            Contact Arav if you believe this is an error.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ─── Sidebar ─────────────────────────────────────────────────────────────────

FINANCE_COLOR = DEPT_COLORS["finance"]

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">MedPort</span>'
        f'<span style="font-size:0.8rem;color:#94a3b8;margin-left:0.4rem;">Team OS</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:0.8rem;color:#94a3b8;margin-top:0.2rem;'>Signed in as <b>{name}</b></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span style="display:inline-block;background:{FINANCE_COLOR}22;color:{FINANCE_COLOR};'
        f'border:1px solid {FINANCE_COLOR}55;border-radius:999px;padding:2px 10px;'
        f'font-size:0.72rem;font-weight:600;margin-top:4px;">Finance</span>',
        unsafe_allow_html=True,
    )
    if admin:
        st.markdown(
            f'<span style="display:inline-block;background:#f59e0b22;color:#f59e0b;'
            f'border:1px solid #f59e0b55;border-radius:999px;padding:2px 10px;'
            f'font-size:0.72rem;font-weight:600;margin-top:4px;">Admin</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    render_logout_button()

    st.markdown(
        f"<div style='font-size:0.72rem;color:#64748b;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:0.05em;margin:0.8rem 0 0.4rem;'>Navigation</div>",
        unsafe_allow_html=True,
    )

    nav_pages = [
        ("Home", "pages/0_Home.py"),
        ("Team Hub", "pages/1_Team_Hub.py"),
        ("Tasks", "pages/3_Tasks.py"),
        ("Announcements", "pages/6_Settings.py"),
        ("Standups", "pages/7_Intelligence.py"),
        ("Settings", "pages/6_Settings.py"),
    ]
    if admin:
        nav_pages += [
            ("Marketing Hub", "pages/8_Marketing_Hub.py"),
        ]

    for label, page_path in nav_pages:
        try:
            st.page_link(page_path, label=label)
        except Exception:
            pass

    if st.button("Refresh data", use_container_width=True, key="fin_refresh_btn"):
        st.cache_data.clear()
        st.rerun()

# ─── Load data ────────────────────────────────────────────────────────────────

df = load_prospects()
goals = get_goals()

fin_tasks = get_tasks_by_department("finance")
if not fin_tasks:
    fin_tasks = get_tasks()

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_overview, tab_pipeline_val, tab_goals, tab_tasks = st.tabs(
    ["Overview", "Pipeline Value", "Goals", "Tasks"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview
# ══════════════════════════════════════════════════════════════════════════════

with tab_overview:
    st.markdown(
        page_header("Finance Hub", "Advait's financial command center"),
        unsafe_allow_html=True,
    )

    # ── Sprint widget ─────────────────────────────────────────────────────────
    _sprint = get_active_sprint()
    if _sprint:
        _sprint_tasks = get_sprint_tasks(_sprint["id"])
        render_sprint_widget(_sprint, _sprint_tasks, current_email=email, show_my_tasks=True, admin=admin)
    elif admin:
        render_create_sprint_form(email)

    # ── Stat cards ────────────────────────────────────────────────────────────

    if not df.empty:
        total_prospects = len(df)
        demos_booked = int((df["status"] == "demo_booked").sum())
        deals_closed = int((df["status"] == "converted").sum())
        arr_projection = deals_closed * 2400
    else:
        total_prospects = demos_booked = deals_closed = arr_projection = 0

    sc1, sc2, sc3, sc4 = st.columns(4)
    for col, val, label in [
        (sc1, total_prospects, "Total Prospects"),
        (sc2, demos_booked, "Demos Booked"),
        (sc3, deals_closed, "Deals Closed"),
        (sc4, f"${arr_projection:,}", "ARR Projection"),
    ]:
        with col:
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{val}</div>'
                f'<div class="stat-label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Active finance-related goals ──────────────────────────────────────────

    st.markdown("### Revenue Goals")

    finance_keywords = ("revenue", "arr", "target", "mrr", "sales", "deal")
    finance_goals = [
        g for g in goals
        if g.get("status") == "active"
        and any(kw in (g.get("title") or "").lower() for kw in finance_keywords)
    ]

    if not finance_goals:
        # Show all active goals as fallback
        finance_goals = [g for g in goals if g.get("status") == "active"]

    if not finance_goals:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;">No active goals yet. '
            'Add goals in the Goals tab.</div>',
            unsafe_allow_html=True,
        )
    else:
        goal_cols = st.columns(min(len(finance_goals), 3))
        for i, goal in enumerate(finance_goals):
            with goal_cols[i % 3]:
                title = goal.get("title", "")
                target = max(1, goal.get("target_value", 1))
                current = goal.get("current_value", 0)
                pct = min(100, round(current / target * 100))
                due = goal.get("due_date", "")
                metric = goal.get("metric_type", "custom").replace("_", " ").title()
                bar_color = MEDPORT_TEAL if pct >= 80 else ("#f59e0b" if pct >= 50 else FINANCE_COLOR)

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


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Pipeline Value
# ══════════════════════════════════════════════════════════════════════════════

with tab_pipeline_val:
    st.markdown("### Pipeline Value")

    if df.empty:
        st.info("No prospect data available.")
    else:
        # Deal value assumptions
        DEAL_VALUES = {
            "not_contacted": 0,
            "email_sent": 100,
            "pending_response": 250,
            "demo_booked": 500,
            "converted": 2400,
        }

        stage_counts: dict[str, int] = {}
        stage_values: dict[str, int] = {}

        for stage in PIPELINE_STAGES:
            count = int((df["status"] == stage).sum())
            stage_counts[stage] = count
            stage_values[stage] = count * DEAL_VALUES.get(stage, 0)

        total_pipeline = sum(stage_values.values())
        arr = stage_values.get("converted", 0)
        potential = stage_values.get("demo_booked", 0)

        # ── Summary stats ──────────────────────────────────────────────────────

        pv1, pv2, pv3 = st.columns(3)
        for col, val, label, color in [
            (pv1, f"${arr:,}", "Current ARR", MEDPORT_TEAL),
            (pv2, f"${potential:,}", "Demo Pipeline", "#8b5cf6"),
            (pv3, f"${total_pipeline:,}", "Total Pipeline", FINANCE_COLOR),
        ]:
            with col:
                st.markdown(
                    f'<div class="stat-card">'
                    f'<div class="stat-value" style="color:{color};">{val}</div>'
                    f'<div class="stat-label">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Value by Stage")

        # ── Progress bar visualization ─────────────────────────────────────────

        max_val = max(stage_values.values()) if stage_values else 1
        max_val = max(max_val, 1)

        for stage in PIPELINE_STAGES:
            count = stage_counts[stage]
            value = stage_values[stage]
            label = STATUS_LABELS.get(stage, stage)
            bar_color = STATUS_COLORS.get(stage, MEDPORT_TEAL)
            bar_pct = min(100, round(value / max_val * 100)) if max_val > 0 else 0

            st.markdown(
                f"""
                <div style="margin-bottom:0.65rem;">
                  <div style="display:flex;justify-content:space-between;
                    font-size:0.82rem;margin-bottom:3px;">
                    <span style="color:#e2e8f0;font-weight:600;">{label}</span>
                    <span style="color:#94a3b8;">{count} prospects &nbsp;·&nbsp;
                      <b style="color:{bar_color};">${value:,}</b></span>
                  </div>
                  <div style="background:#1e293b;border-radius:4px;height:10px;overflow:hidden;">
                    <div style="width:{bar_pct}%;background:{bar_color};height:100%;
                      border-radius:4px;transition:width 0.3s ease;"></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.78rem;color:#475569;">'
            'Deal value assumptions: Email Sent $100 · Pending Response $250 · '
            'Demo Booked $500 · Converted $2,400 ARR ($200/mo &times; 12)</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Goals
# ══════════════════════════════════════════════════════════════════════════════

with tab_goals:
    st.markdown("### Team Goals")

    # ── Create goal (admin only) ───────────────────────────────────────────────

    if admin:
        with st.expander("Create New Goal", expanded=False):
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                fin_g_title = st.text_input("Goal title *", key="fin_new_goal_title")
                fin_g_desc = st.text_area("Description", key="fin_new_goal_desc", height=60)
                fin_g_metric = st.selectbox(
                    "Metric type",
                    ["demos_booked", "converted", "custom", "emails_sent"],
                    key="fin_new_goal_metric",
                )
            with g_col2:
                fin_g_target = st.number_input(
                    "Target value", min_value=1, value=10, key="fin_new_goal_target"
                )
                fin_g_due = st.date_input(
                    "Due date (optional)", value=None, key="fin_new_goal_due"
                )

            if st.button("Create Goal", type="primary", key="fin_do_create_goal"):
                if fin_g_title.strip():
                    goal_id = create_goal({
                        "title": fin_g_title.strip(),
                        "description": fin_g_desc.strip() or None,
                        "target_value": int(fin_g_target),
                        "current_value": 0,
                        "metric_type": fin_g_metric,
                        "due_date": fin_g_due.isoformat() if fin_g_due else None,
                        "status": "active",
                        "created_by_email": email,
                    })
                    if goal_id:
                        log_activity(
                            actor_email=email,
                            actor_name=name,
                            action_type="goal_updated",
                            entity_type="goal",
                            entity_id=goal_id,
                            entity_name=fin_g_title.strip(),
                            details={"action": "created", "target": int(fin_g_target)},
                        )
                        st.success("Goal created.")
                        get_goals.clear()
                        st.rerun()
                else:
                    st.warning("Please enter a goal title.")

    # ── Active goals ──────────────────────────────────────────────────────────

    active_goals = [g for g in goals if g.get("status") == "active"]
    completed_goals = [g for g in goals if g.get("status") == "completed"]
    paused_goals = [g for g in goals if g.get("status") == "paused"]

    def _goal_status_badge(status: str) -> str:
        cfg = {
            "active":    ("#00B89F22", "#00B89F", "Active"),
            "completed": ("#10b98122", "#10b981", "Completed"),
            "paused":    ("#f59e0b22", "#f59e0b", "Paused"),
        }
        bg, color, label = cfg.get(status, ("#94a3b822", "#94a3b8", status.title()))
        return (
            f'<span style="background:{bg};color:{color};border:1px solid {color}55;'
            f'border-radius:999px;padding:1px 9px;font-size:0.72rem;font-weight:600;">{label}</span>'
        )

    if not active_goals and not completed_goals and not paused_goals:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">'
            'No goals yet. Use the form above to create one.</div>',
            unsafe_allow_html=True,
        )

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
                status = goal.get("status", "active")
                bar_color = MEDPORT_TEAL if pct >= 80 else ("#f59e0b" if pct >= 50 else FINANCE_COLOR)

                st.markdown(
                    f"""
                    <div class="goal-card">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;
                        margin-bottom:0.3rem;">
                        <div class="goal-title">{title}</div>
                        {_goal_status_badge(status)}
                      </div>
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
                            "Current value",
                            min_value=0,
                            max_value=target * 10,
                            value=current,
                            key=f"fin_goal_val_{goal_id}",
                        )
                        new_goal_status = st.selectbox(
                            "Goal status",
                            ["active", "completed", "paused"],
                            index=["active", "completed", "paused"].index(
                                goal.get("status", "active")
                            ),
                            key=f"fin_goal_status_{goal_id}",
                        )
                        if st.button("Save", key=f"fin_goal_save_{goal_id}"):
                            update_goal(goal_id, {
                                "current_value": int(new_val),
                                "status": new_goal_status,
                            })
                            log_activity(
                                actor_email=email,
                                actor_name=name,
                                action_type="goal_updated",
                                entity_type="goal",
                                entity_id=goal_id,
                                entity_name=title,
                                details={"old_value": current, "new_value": int(new_val)},
                            )
                            get_goals.clear()
                            st.rerun()

    if completed_goals:
        with st.expander(f"Completed Goals ({len(completed_goals)})", expanded=False):
            for goal in completed_goals:
                target = max(1, goal.get("target_value", 1))
                current = goal.get("current_value", 0)
                st.markdown(
                    f'<span style="color:{MEDPORT_TEAL};font-weight:700;">&#10003;</span> '
                    f'**{goal.get("title", "")}** — {current}/{target}',
                    unsafe_allow_html=True,
                )

    if paused_goals:
        with st.expander(f"Paused Goals ({len(paused_goals)})", expanded=False):
            for goal in paused_goals:
                target = max(1, goal.get("target_value", 1))
                current = goal.get("current_value", 0)
                pct = min(100, round(current / target * 100))
                st.markdown(
                    f'<span style="color:#f59e0b;font-weight:700;">&#9646;&#9646;</span> '
                    f'**{goal.get("title", "")}** — {current}/{target} ({pct}%)',
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Tasks
# ══════════════════════════════════════════════════════════════════════════════

with tab_tasks:
    st.markdown("### Finance Tasks")

    # ── Filter controls ───────────────────────────────────────────────────────

    fin_status_filter = st.multiselect(
        "Filter by status",
        ["open", "in_progress", "completed", "blocked"],
        default=["open", "in_progress"],
        key="fin_task_status_filter",
        format_func=lambda s: s.replace("_", " ").title(),
    )

    filtered_tasks = [t for t in fin_tasks if t.get("status") in fin_status_filter]

    if not filtered_tasks:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">No tasks match this filter.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="font-size:0.82rem;color:#64748b;margin-bottom:0.8rem;">'
            f'{len(filtered_tasks)} task{"s" if len(filtered_tasks) != 1 else ""}</div>',
            unsafe_allow_html=True,
        )

        for task in sorted(
            filtered_tasks,
            key=lambda t: (
                {"urgent": 0, "high": 1, "medium": 2, "low": 3}.get(t.get("priority", "medium"), 2)
            ),
        ):
            task_id = task.get("id", "")
            title = task.get("title", "")
            desc = task.get("description", "")
            priority = task.get("priority", "medium")
            status = task.get("status", "open")
            due = task.get("due_date", "")
            assigned = task.get("assigned_to") or []
            border_color = TASK_STATUS_COLORS.get(status, MEDPORT_BLUE)

            priority_colors = {
                "low": "#64748b",
                "medium": MEDPORT_BLUE,
                "high": "#f59e0b",
                "urgent": "#ef4444",
            }
            pcolor = priority_colors.get(priority, MEDPORT_BLUE)

            st.markdown(
                f"""
                <div class="task-card" style="border-left-color:{border_color};">
                  <div class="task-title">{title}</div>
                  <div class="task-meta">
                    <span style="background:{pcolor}22;color:{pcolor};border:1px solid {pcolor}55;
                      border-radius:999px;padding:1px 8px;font-size:0.7rem;font-weight:700;">
                      {priority.upper()}</span>
                    <span style="background:{border_color}22;color:{border_color};border:1px solid {border_color}55;
                      border-radius:999px;padding:1px 8px;font-size:0.7rem;font-weight:600;margin-left:4px;">
                      {status.replace("_", " ").title()}</span>
                    {"&nbsp;<span style='font-size:0.72rem;color:#64748b;'>Due " + due + "</span>" if due else ""}
                    {"&nbsp;<span style='font-size:0.72rem;color:#64748b;'>Assigned: " + ", ".join(assigned) + "</span>" if assigned else ""}
                  </div>
                  {"<div style='font-size:0.8rem;color:#5a6a7a;margin-top:4px;'>" + desc + "</div>" if desc else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )
