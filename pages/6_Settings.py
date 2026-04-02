"""
MedPort Settings — team member management and admin controls.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import inject_css, MEDPORT_TEAL, MEDPORT_BLUE, MEDPORT_DARK
from lib.auth import check_auth, is_admin
from lib.db import get_team_members, create_team_member, update_team_member, delete_team_member

st.set_page_config(
    page_title="Settings — MedPort",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">Settings</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='font-size:0.8rem;color:#94a3b8;'>Signed in as <b>{name}</b></div>", unsafe_allow_html=True)
    st.markdown("---")

    try:
        auth_configured = bool(st.secrets.get("auth", {}))
    except Exception:
        auth_configured = False
    if auth_configured and os.environ.get("LOCAL_DEV", "false").lower() != "true":
        if st.button("Sign out"):
            st.logout()

    if st.button("Refresh data", use_container_width=True):
        get_team_members.clear()
        st.rerun()

# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div style="margin-bottom:1.5rem;">
      <div style="font-size:1.9rem;font-weight:800;line-height:1.15;
        background:linear-gradient(135deg,{MEDPORT_TEAL},{MEDPORT_BLUE});
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
        background-clip:text;font-family:'Syne',sans-serif;">Settings</div>
      <div style="color:#475569;font-size:0.9rem;margin-top:0.2rem;">
        Team member management and admin controls
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not admin:
    st.warning("Only admins can manage team settings. Contact Arav if you need changes made.")
    st.stop()

# ─── Info notice ─────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div style="background:{MEDPORT_TEAL}12;border:1px solid {MEDPORT_TEAL}30;
      border-left:4px solid {MEDPORT_TEAL};border-radius:10px;
      padding:0.75rem 1rem;font-size:0.88rem;color:#065f46;margin-bottom:1.5rem;">
      Changes to team members take effect immediately across all pages (data refreshes within 30 seconds).
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Load members ────────────────────────────────────────────────────────────

members = get_team_members()

# ─── Team Members Grid ───────────────────────────────────────────────────────

st.markdown(f"### Team Members ({len(members)} active)")

if not members:
    st.info("No team members found. Add one below.")
else:
    # Display in rows of 3
    cols_per_row = 3
    for row_start in range(0, len(members), cols_per_row):
        row_members = members[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col_idx, member in enumerate(row_members):
            with cols[col_idx]:
                member_id = member.get("id", "")
                member_name = member.get("name", "")
                member_role = member.get("role", "Team Member")
                member_email = member.get("email", "") or ""
                avatar_color = member.get("avatar_color", MEDPORT_TEAL)
                initials = "".join(w[0].upper() for w in member_name.split()[:2])

                st.markdown(
                    f"""
                    <div class="settings-member-card">
                      <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem;">
                        <div style="width:44px;height:44px;border-radius:50%;flex-shrink:0;
                          background:linear-gradient(135deg,{avatar_color},{MEDPORT_BLUE});
                          color:#fff;font-size:0.95rem;font-weight:700;
                          display:flex;align-items:center;justify-content:center;
                          box-shadow:0 4px 12px rgba(0,184,159,0.25);">{initials}</div>
                        <div>
                          <div style="font-size:0.95rem;font-weight:700;color:{MEDPORT_DARK};
                            font-family:'Syne',sans-serif;">{member_name}</div>
                          <div style="font-size:0.78rem;color:#64748b;font-weight:500;">{member_role}</div>
                          {"<div style='font-size:0.73rem;color:#94a3b8;margin-top:1px;'>" + member_email + "</div>" if member_email else ""}
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Edit expander
                with st.expander("Edit", expanded=False):
                    edit_name = st.text_input(
                        "Name",
                        value=member_name,
                        key=f"edit_name_{member_id}",
                    )
                    edit_role = st.text_input(
                        "Role",
                        value=member_role,
                        key=f"edit_role_{member_id}",
                    )
                    edit_email = st.text_input(
                        "Email (optional)",
                        value=member_email,
                        key=f"edit_email_{member_id}",
                    )
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        if st.button("Save", key=f"save_{member_id}", use_container_width=True, type="primary"):
                            if edit_name.strip():
                                ok = update_team_member(member_id, {
                                    "name": edit_name.strip(),
                                    "role": edit_role.strip() or "Team Member",
                                    "email": edit_email.strip() or None,
                                })
                                if ok:
                                    st.success("Updated.")
                                    st.rerun()
                            else:
                                st.warning("Name cannot be empty.")
                    with edit_col2:
                        if st.button("Remove", key=f"remove_{member_id}", use_container_width=True):
                            st.session_state[f"confirm_remove_{member_id}"] = True

                # Confirm remove
                if st.session_state.get(f"confirm_remove_{member_id}", False):
                    st.warning(f"Remove **{member_name}** from the team?")
                    conf_col1, conf_col2 = st.columns(2)
                    with conf_col1:
                        if st.button("Yes, remove", key=f"confirm_yes_{member_id}", use_container_width=True):
                            ok = delete_team_member(member_id)
                            if ok:
                                st.session_state.pop(f"confirm_remove_{member_id}", None)
                                st.success(f"Removed {member_name}.")
                                st.rerun()
                    with conf_col2:
                        if st.button("Cancel", key=f"confirm_no_{member_id}", use_container_width=True):
                            st.session_state.pop(f"confirm_remove_{member_id}", None)
                            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ─── Add Member form ─────────────────────────────────────────────────────────

st.markdown("### Add Team Member")

with st.container():
    add_col1, add_col2, add_col3 = st.columns(3)
    with add_col1:
        new_name = st.text_input("Name *", key="new_member_name", placeholder="e.g. Sarah")
    with add_col2:
        new_role = st.text_input("Role *", key="new_member_role", placeholder="e.g. CTO & Co-Founder")
    with add_col3:
        new_email = st.text_input("Email (optional)", key="new_member_email", placeholder="sarah@medport.ca")

    if st.button("Add Member", type="primary", key="do_add_member"):
        if new_name.strip() and new_role.strip():
            sort_order = max((m.get("sort_order", 0) for m in members), default=-1) + 1
            member_id = create_team_member({
                "name": new_name.strip(),
                "role": new_role.strip(),
                "email": new_email.strip() or None,
                "avatar_color": MEDPORT_TEAL,
                "is_active": True,
                "sort_order": sort_order,
            })
            if member_id:
                st.success(f"Added {new_name.strip()} to the team.")
                st.rerun()
        else:
            st.warning("Name and Role are required.")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ─── About section ───────────────────────────────────────────────────────────

st.markdown("### About")
st.markdown(
    f"""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1rem 1.2rem;font-size:0.88rem;color:#475569;">
      <b style="color:{MEDPORT_DARK};">MedPort Team Dashboard</b><br>
      Internal operations tool for the MedPort founding team.<br>
      Built with Streamlit + Supabase.
    </div>
    """,
    unsafe_allow_html=True,
)
