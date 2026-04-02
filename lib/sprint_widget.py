"""
Sprint widget helpers — reusable across dashboard and dept hubs.
"""
import streamlit as st
from datetime import date


def render_sprint_widget(sprint: dict, tasks: list[dict], current_email: str = "", show_my_tasks: bool = False):
    """
    Renders a sprint progress widget inline (no container needed).

    sprint: dict from sprints table
    tasks: all tasks in this sprint (from get_sprint_tasks)
    current_email: filter to this person's tasks if show_my_tasks=True
    show_my_tasks: if True, show only tasks assigned to current_email
    """
    from lib.styles import MEDPORT_TEAL, MEDPORT_DARK

    sprint_name = sprint.get("name", "Current Sprint")
    sprint_desc = sprint.get("description", "")
    start = sprint.get("start_date", "")
    end = sprint.get("end_date", "")

    # Date range display
    try:
        start_d = date.fromisoformat(start) if start else None
        end_d = date.fromisoformat(end) if end else None
        today = date.today()
        date_str = ""
        days_left_str = ""
        if start_d and end_d:
            date_str = f"{start_d.strftime('%b %d')} \u2013 {end_d.strftime('%b %d')}"
            if today <= end_d:
                days_left = (end_d - today).days
                days_left_str = f"{days_left} day{'s' if days_left != 1 else ''} left"
            else:
                days_left_str = "Sprint ended"
    except Exception:
        date_str = f"{start} \u2013 {end}"
        days_left_str = ""

    # Task filtering
    if show_my_tasks and current_email:
        display_tasks = [t for t in tasks if current_email.lower() in [a.lower() for a in (t.get("assigned_to") or [])]]
        section_label = "My Sprint Tasks"
    else:
        display_tasks = tasks
        section_label = "Sprint Tasks"

    total = len(display_tasks)
    completed = sum(1 for t in display_tasks if t.get("status") == "completed")
    pct = int(completed / total * 100) if total > 0 else 0

    # Sprint header card
    st.markdown(
        f"""
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;
          padding:1.25rem 1.5rem;margin-bottom:1rem;
          box-shadow:0 1px 2px rgba(0,0,0,0.04);">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;">
            <div>
              <div style="font-size:0.7rem;font-weight:700;color:#64748b;text-transform:uppercase;
                letter-spacing:0.08em;margin-bottom:4px;">Active Sprint</div>
              <div style="font-size:1.125rem;font-weight:700;color:#0F172A;
                font-family:'Plus Jakarta Sans',sans-serif;">{sprint_name}</div>
              {f'<div style="font-size:0.875rem;color:#64748b;margin-top:3px;">{sprint_desc}</div>' if sprint_desc else ''}
            </div>
            <div style="text-align:right;flex-shrink:0;">
              <div style="font-size:0.8125rem;color:#64748b;">{date_str}</div>
              <div style="font-size:0.8125rem;font-weight:600;color:#00B89F;margin-top:2px;">{days_left_str}</div>
            </div>
          </div>
          <div style="margin-top:1rem;">
            <div style="display:flex;justify-content:space-between;font-size:0.8125rem;color:#64748b;margin-bottom:4px;">
              <span>{section_label}: {completed}/{total} complete</span>
              <span style="font-weight:700;color:#00B89F;">{pct}%</span>
            </div>
            <div style="width:100%;height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
              <div style="width:{pct}%;height:8px;background:#00B89F;border-radius:4px;
                transition:width 0.5s ease;"></div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Task list
    if display_tasks:
        status_icons = {"open": "\u25cb", "in_progress": "\u25d1", "completed": "\u25cf", "blocked": "\u2715"}
        status_colors = {"open": "#3B82F6", "in_progress": "#8B5CF6", "completed": "#00B89F", "blocked": "#ef4444"}

        for task in display_tasks:
            t_status = task.get("status", "open")
            t_title = task.get("title", "Untitled")
            t_assignees = task.get("assigned_to") or []
            assignee_str = ", ".join(a.split("@")[0].capitalize() for a in t_assignees[:2]) if t_assignees else "Unassigned"
            icon = status_icons.get(t_status, "\u25cb")
            color = status_colors.get(t_status, "#64748b")
            opacity = "opacity:0.6;" if t_status == "completed" else ""

            st.markdown(
                f"""<div style="display:flex;align-items:center;gap:0.75rem;
                  padding:0.6rem 0.75rem;border-radius:10px;margin-bottom:3px;
                  background:#f8fafc;border:1px solid #e2e8f0;{opacity}">
                  <span style="color:{color};font-size:1rem;flex-shrink:0;">{icon}</span>
                  <span style="flex:1;font-size:0.9rem;color:#0F172A;
                    {'text-decoration:line-through;' if t_status == 'completed' else ''}">{t_title}</span>
                  <span style="font-size:0.75rem;color:#94a3b8;">{assignee_str}</span>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div style='color:#94a3b8;font-size:0.875rem;padding:0.5rem 0;'>"
            "No tasks assigned for this sprint yet.</div>",
            unsafe_allow_html=True,
        )


def render_create_sprint_form(creator_email: str):
    """Renders a form to create a new sprint. Call only when admin and no active sprint."""
    with st.expander("Create New Sprint", expanded=False):
        from lib.db import create_sprint, get_sprints, update_sprint

        col1, col2 = st.columns(2)
        with col1:
            sprint_name = st.text_input(
                "Sprint Name *",
                placeholder="e.g. Sprint 3 — April 2026",
                max_chars=100,
                key="new_sprint_name",
            )
            sprint_start = st.date_input("Start Date", key="new_sprint_start")
        with col2:
            sprint_desc = st.text_area(
                "Description",
                max_chars=500,
                height=70,
                placeholder="Sprint goals and focus...",
                key="new_sprint_desc",
            )
            sprint_end = st.date_input("End Date", key="new_sprint_end")

        if st.button("Create Sprint", type="primary", key="create_sprint_btn"):
            if not sprint_name.strip():
                st.error("Sprint name is required.")
            elif sprint_end <= sprint_start:
                st.error("End date must be after start date.")
            else:
                # Mark any currently active sprints as completed
                for s in get_sprints(status="active"):
                    update_sprint(s["id"], {"status": "completed"})

                sid = create_sprint({
                    "name": sprint_name.strip(),
                    "description": sprint_desc.strip(),
                    "start_date": sprint_start.isoformat(),
                    "end_date": sprint_end.isoformat(),
                    "status": "active",
                    "created_by_email": creator_email,
                })
                if sid:
                    st.success(f"Sprint '{sprint_name.strip()}' created!")
                    st.rerun()
