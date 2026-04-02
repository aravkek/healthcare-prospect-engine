"""
MedPort Announcements — team-wide updates from leadership.
Access: all authenticated users. Admin can post and manage announcements.
"""

import os
import sys
from datetime import datetime, timezone, date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import inject_css, MEDPORT_TEAL, MEDPORT_DARK, MEDPORT_BLUE, DEPT_COLORS, DEPT_LABELS, page_header
from lib.auth import check_auth, is_admin, get_department, render_logout_button
from lib.db import (
    get_announcements,
    create_announcement,
    update_announcement,
    mark_announcement_read,
    log_activity,
)

st.set_page_config(
    page_title="Announcements — MedPort",
    page_icon="📢",
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


def _is_read(ann_id: str) -> bool:
    """Check session-state cache first, then accept True if present."""
    return ann_id in st.session_state.get("ann_read_ids", set())


def _mark_read_in_session(ann_id: str):
    if "ann_read_ids" not in st.session_state:
        st.session_state["ann_read_ids"] = set()
    st.session_state["ann_read_ids"].add(ann_id)


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
    st.markdown(
        _dept_badge(dept),
        unsafe_allow_html=True,
    )
    st.markdown("---")
    render_logout_button()
    st.markdown("---")
    st.markdown("<div style='font-size:0.75rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;'>Navigation</div>", unsafe_allow_html=True)
    st.page_link("medport_dashboard.py", label="Home", icon="🏠")
    st.page_link("pages/1_Team_Hub.py", label="Team Hub", icon="👥")
    st.page_link("pages/3_Tasks.py", label="Tasks", icon="✅")
    st.page_link("pages/6_Settings.py", label="Settings", icon="⚙️")

# ─── Load announcements ───────────────────────────────────────────────────────

all_active = get_announcements(active_only=True)
all_anns = get_announcements(active_only=False)
all_inactive = [a for a in all_anns if not a.get("is_active")]

# Sort active by priority: urgent → warning → info
_priority_order = {"urgent": 0, "warning": 1, "info": 2}
all_active_sorted = sorted(all_active, key=lambda a: _priority_order.get(a.get("priority", "info"), 2))

# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown(page_header("Announcements", "Team-wide updates from leadership"), unsafe_allow_html=True)

# ─── Active announcements ────────────────────────────────────────────────────

if not all_active_sorted:
    st.markdown(
        '<div style="color:#8a9ab0;font-size:0.9rem;padding:1.5rem 0;">No active announcements right now. Check back later.</div>',
        unsafe_allow_html=True,
    )
else:
    for ann in all_active_sorted:
        ann_id = str(ann.get("id", ""))
        priority = ann.get("priority", "info")
        title = ann.get("title", "Untitled")
        body = ann.get("body", "")
        posted_by = ann.get("posted_by_name") or ann.get("author_name") or "Leadership"
        created_at = ann.get("created_at", "")
        time_str = _time_ago(created_at)

        css_class = f"announcement-{priority}"
        already_read = _is_read(ann_id)

        priority_icon = {"urgent": "🔴", "warning": "🟡", "info": "🔵"}.get(priority, "🔵")

        st.markdown(
            f"""
            <div class="{css_class}">
              <div class="announcement-title">{priority_icon} {title}</div>
              <div class="announcement-body">{body}</div>
              <div style="font-size:0.8rem;color:#94a3b8;margin-top:0.5rem;">
                Posted by {posted_by} &middot; {time_str}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_read, col_spacer = st.columns([1, 5])
        with col_read:
            if already_read:
                st.markdown(
                    '<span style="font-size:0.8rem;color:#10b981;font-weight:600;">&#10003; Read</span>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button("Mark as Read", key=f"ann_read_{ann_id}", use_container_width=True):
                    ok = mark_announcement_read(ann_id, email)
                    if ok:
                        _mark_read_in_session(ann_id)
                        st.rerun()

# ─── Archive (admin only) ────────────────────────────────────────────────────

if admin:
    with st.expander(f"Archive ({len(all_inactive)} inactive)", expanded=False):
        if not all_inactive:
            st.caption("No archived announcements.")
        else:
            for ann in all_inactive:
                ann_id = str(ann.get("id", ""))
                title = ann.get("title", "Untitled")
                priority = ann.get("priority", "info")
                created_at = ann.get("created_at", "")
                time_str = _time_ago(created_at)

                col_info, col_restore = st.columns([5, 1])
                with col_info:
                    st.markdown(
                        f"""
                        <div style="padding:0.5rem 0;border-bottom:1px solid #f1f5f9;">
                          <span style="font-weight:600;color:{MEDPORT_DARK};">{title}</span>
                          <span style="font-size:0.75rem;color:#94a3b8;margin-left:0.75rem;">{priority} &middot; {time_str}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_restore:
                    if st.button("Restore", key=f"ann_restore_{ann_id}", use_container_width=True):
                        ok = update_announcement(ann_id, {"is_active": True})
                        if ok:
                            st.success(f"Restored: {title}")
                            log_activity(
                                actor_email=email,
                                actor_name=name,
                                action_type="announcement_restored",
                                entity_type="announcement",
                                entity_id=ann_id,
                                entity_name=title,
                            )
                            st.rerun()

# ─── Post new announcement (admin only) ──────────────────────────────────────

if admin:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Post Announcement", expanded=False):
        ann_title = st.text_input(
            "Title *",
            max_chars=200,
            key="ann_new_title",
            placeholder="Announcement title...",
        )
        ann_body = st.text_area(
            "Body *",
            max_chars=2000,
            key="ann_new_body",
            height=120,
            placeholder="Write the announcement body here...",
        )
        ann_priority = st.selectbox(
            "Priority",
            options=["info", "warning", "urgent"],
            key="ann_new_priority",
            format_func=lambda x: {"info": "Info (blue)", "warning": "Warning (yellow)", "urgent": "Urgent (red)"}[x],
        )
        ann_expires = st.date_input(
            "Expires at (optional — leave today or earlier to omit)",
            value=None,
            key="ann_new_expires",
        )

        if st.button("Post Announcement", type="primary", key="ann_submit"):
            title_clean = ann_title.strip()
            body_clean = ann_body.strip()
            if not title_clean:
                st.error("Title is required.")
            elif not body_clean:
                st.error("Body is required.")
            else:
                expires_iso = None
                if ann_expires and ann_expires > date.today():
                    expires_iso = ann_expires.isoformat()

                payload = {
                    "title": title_clean,
                    "body": body_clean,
                    "priority": ann_priority,
                    "is_active": True,
                    "posted_by_name": name,
                    "posted_by_email": email,
                }
                if expires_iso:
                    payload["expires_at"] = expires_iso

                new_id = create_announcement(payload)
                if new_id:
                    log_activity(
                        actor_email=email,
                        actor_name=name,
                        action_type="announcement_created",
                        entity_type="announcement",
                        entity_id=str(new_id),
                        entity_name=title_clean,
                        details={"priority": ann_priority},
                    )
                    st.success(f"Announcement posted: {title_clean}")
                    st.rerun()
                else:
                    st.error("Failed to post announcement. Check Supabase connection.")
