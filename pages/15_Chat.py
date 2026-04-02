"""
MedPort Team Chat — real-time messaging for the founding team.
Channels: #general + direct messages between team members.
Access: all authenticated users.
"""

import os
import sys
import time
from datetime import datetime, timezone

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import inject_css, MEDPORT_TEAL, MEDPORT_DARK, DEPT_COLORS, page_header
from lib.auth import check_auth, is_admin, get_department, render_logout_button
from lib.db import get_messages, send_message, get_dm_channel, get_team_members, _dm_channel

st.set_page_config(
    page_title="Chat — MedPort",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)
dept = get_department(email)

# ─── Default session state ────────────────────────────────────────────────────

if "chat_channel" not in st.session_state:
    st.session_state["chat_channel"] = "general"
if "chat_channel_name" not in st.session_state:
    st.session_state["chat_channel_name"] = "# general"
if "chat_auto_refresh" not in st.session_state:
    st.session_state["chat_auto_refresh"] = False

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
    color = DEPT_COLORS.get(department, "#64748b")
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:99px;'
        f'font-size:0.7rem;font-weight:600;background:{color}20;color:{color};">'
        f'{department.title()}</span>'
    )


def _msg_html(msg: dict, current_email: str) -> str:
    is_me = msg.get("sender_email", "").lower() == current_email.lower()
    sender = msg.get("sender_name", "?")
    content = msg.get("content", "")
    ts = _time_ago(msg.get("created_at", ""))
    initials = "".join(w[0].upper() for w in sender.split()[:2])

    if is_me:
        return f"""
        <div style="display:flex;justify-content:flex-end;margin:4px 0;">
          <div style="max-width:70%;">
            <div style="background:#00B89F;color:#fff;border-radius:14px 14px 4px 14px;
              padding:0.65rem 1rem;font-size:0.9375rem;line-height:1.45;">{content}</div>
            <div style="text-align:right;font-size:0.7rem;color:#94a3b8;margin-top:2px;">{ts}</div>
          </div>
        </div>"""
    else:
        return f"""
        <div style="display:flex;align-items:flex-start;gap:8px;margin:4px 0;">
          <div style="width:30px;height:30px;border-radius:50%;background:#1e293b;color:#fff;
            font-size:0.7rem;font-weight:700;display:flex;align-items:center;justify-content:center;
            flex-shrink:0;">{initials}</div>
          <div style="max-width:70%;">
            <div style="font-size:0.75rem;font-weight:600;color:#64748b;margin-bottom:2px;">{sender}</div>
            <div style="background:#f8fafc;border:1px solid #e2e8f0;color:#0F172A;
              border-radius:14px 14px 14px 4px;padding:0.65rem 1rem;font-size:0.9375rem;line-height:1.45;">{content}</div>
            <div style="font-size:0.7rem;color:#94a3b8;margin-top:2px;">{ts}</div>
          </div>
        </div>"""


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
    st.markdown(
        "<div style='font-size:0.75rem;color:#64748b;font-weight:600;text-transform:uppercase;"
        "letter-spacing:0.06em;margin-bottom:0.4rem;'>Navigation</div>",
        unsafe_allow_html=True,
    )
    st.page_link("medport_dashboard.py", label="Home", icon="🏠")
    st.page_link("pages/1_Team_Hub.py", label="Team Hub", icon="👥")
    st.page_link("pages/3_Tasks.py", label="Tasks", icon="✅")
    st.page_link("pages/6_Settings.py", label="Settings", icon="⚙️")

# ─── Layout: channel selector | message feed ─────────────────────────────────

col_nav, col_feed = st.columns([1, 3])

# ════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN — channel / DM selector
# ════════════════════════════════════════════════════════════════════════════

with col_nav:
    st.markdown(
        "<div style='font-size:0.7rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.08em;color:#94a3b8;margin-bottom:0.4rem;'>Channels</div>",
        unsafe_allow_html=True,
    )

    active_channel = st.session_state["chat_channel"]

    # #general button
    general_type = "primary" if active_channel == "general" else "secondary"
    if st.button("#  general", key="chat_ch_general", type=general_type, use_container_width=True):
        st.session_state["chat_channel"] = "general"
        st.session_state["chat_channel_name"] = "# general"
        st.rerun()

    st.markdown(
        "<div style='font-size:0.7rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.08em;color:#94a3b8;margin:1rem 0 0.4rem 0;'>Direct Messages</div>",
        unsafe_allow_html=True,
    )

    team_members = get_team_members()
    for member in team_members:
        member_email = member.get("email", "")
        member_name = member.get("name", "")

        # Skip self and members without email
        if not member_email or member_email.lower() == email.lower():
            continue

        dm_channel_id = _dm_channel(email, member_email)
        dm_type = "primary" if active_channel == dm_channel_id else "secondary"

        if st.button(
            member_name,
            key=f"chat_dm_{member_email}",
            type=dm_type,
            use_container_width=True,
        ):
            st.session_state["chat_channel"] = dm_channel_id
            st.session_state["chat_channel_name"] = f"DM with {member_name}"
            st.rerun()

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    auto_refresh = st.toggle(
        "Auto-refresh (5s)",
        value=st.session_state["chat_auto_refresh"],
        key="chat_auto_refresh_toggle",
    )
    st.session_state["chat_auto_refresh"] = auto_refresh

# ════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — message feed + input
# ════════════════════════════════════════════════════════════════════════════

with col_feed:
    channel = st.session_state["chat_channel"]
    channel_name = st.session_state["chat_channel_name"]

    st.subheader(channel_name)

    # Message feed container
    feed_container = st.container()
    with feed_container:
        messages = get_messages(channel, limit=100)

        if not messages:
            st.markdown(
                "<div style='color:#94a3b8;font-size:0.9rem;padding:2rem 0;text-align:center;'>"
                "No messages yet. Be the first to say something.</div>",
                unsafe_allow_html=True,
            )
        else:
            bubbles_html = "".join(_msg_html(m, email) for m in messages)
            st.markdown(
                f'<div style="padding:0.5rem 0;">{bubbles_html}</div>',
                unsafe_allow_html=True,
            )

        # Scroll anchor
        st.markdown("<div id='chat-bottom'></div>", unsafe_allow_html=True)

    # Message input
    msg_input = st.chat_input(f"Message {channel_name}...", key="chat_msg_input")
    if msg_input:
        ok = send_message(channel, email, name, msg_input)
        if ok:
            st.rerun()
        else:
            st.error("Failed to send message. Check your connection.")

# ─── Auto-refresh ─────────────────────────────────────────────────────────────

if st.session_state.get("chat_auto_refresh"):
    time.sleep(5)
    st.cache_data.clear()
    st.rerun()
