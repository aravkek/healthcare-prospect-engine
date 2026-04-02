"""
MedPort Settings — team directory (visible to all) and team management (admins only).
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import inject_css, MEDPORT_TEAL, MEDPORT_BLUE, MEDPORT_DARK, DEPT_COLORS, DEPT_LABELS
from lib.auth import check_auth, is_admin, render_logout_button
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
    st.markdown(
        f"<div style='font-size:0.8rem;color:#94a3b8;margin-bottom:0.5rem;'>Signed in as <b>{name}</b></div>",
        unsafe_allow_html=True,
    )
    render_logout_button()
    st.markdown("---")
    if st.button("Refresh", use_container_width=True):
        get_team_members.clear()
        st.rerun()

# ─── Page header ─────────────────────────────────────────────────────────────

_settings_subtitle = "Admin controls — add, edit, and remove team members" if admin else "Team directory — contact Arav to make changes"
st.markdown(
    f"""
    <div style="margin-bottom:1.5rem;">
      <div class="page-title">Team Settings</div>
      <div class="page-subtitle">{_settings_subtitle}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

members = get_team_members()

# ─── Quick-seed founding team (admin, empty DB only) ─────────────────────────

if admin and not members:
    st.warning("No team members found. Add your founding team below, or use Quick Seed to add all 5 co-founders at once.")
    if st.button("Quick Seed — Add MedPort Founding Team", type="primary", key="quick_seed"):
        # Pre-populate the 5 co-founders. Emails are placeholders — edit after seeding.
        founding_team = [
            {"name": "Arav Kekane",   "role": "CEO & Co-Founder",  "email": "aravkekane@gmail.com",   "department": "leadership"},
            {"name": "Advait",        "role": "CFO & Co-Founder",  "email": "",                       "department": "finance"},
            {"name": "Ahan",          "role": "CMO & Co-Founder",  "email": "",                       "department": "marketing"},
            {"name": "Aarya",         "role": "CTO & Co-Founder",  "email": "",                       "department": "tech"},
            {"name": "Nathen",        "role": "COO & Co-Founder",  "email": "",                       "department": "operations"},
        ]
        from lib.styles import DEPT_COLORS as _DC
        for i, p in enumerate(founding_team):
            dc = _DC.get(p["department"], MEDPORT_TEAL)
            create_team_member({
                "name": p["name"], "role": p["role"],
                "email": p["email"] or None,
                "department": p["department"],
                "department_color": dc, "avatar_color": dc,
                "is_active": True, "sort_order": i,
            })
        get_team_members.clear()
        st.success("Founding team seeded! Edit each member to add their login emails.")
        st.rerun()
    st.markdown("---")

# ─── Team Directory (visible to everyone) ────────────────────────────────────

st.markdown(f"### Team ({len(members)} members)")

if not members:
    st.info("No team members found.")
else:
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
                member_dept = member.get("department", "unassigned") or "unassigned"
                avatar_color = member.get("department_color") or member.get("avatar_color", MEDPORT_TEAL)
                initials = "".join(w[0].upper() for w in member_name.split()[:2])
                email_html = f"<div style='font-size:0.75rem;color:#94a3b8;margin-top:2px;'>{member_email}</div>" if member_email else ""
                dept_color = DEPT_COLORS.get(member_dept, "#94a3b8")
                dept_badge = f"<span style='background:{dept_color}22;color:{dept_color};border:1px solid {dept_color}55;border-radius:999px;padding:1px 9px;font-size:0.7rem;font-weight:600;margin-top:4px;display:inline-block;'>{DEPT_LABELS.get(member_dept, member_dept.capitalize())}</span>"

                st.markdown(
                    f"""
                    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:1rem;
                      padding:1rem 1.1rem;box-shadow:0 1px 2px rgba(0,0,0,0.04);margin-bottom:0.5rem;">
                      <div style="display:flex;align-items:center;gap:0.75rem;">
                        <div style="width:44px;height:44px;border-radius:50%;flex-shrink:0;
                          background:{avatar_color};
                          color:#fff;font-size:0.95rem;font-weight:700;
                          display:flex;align-items:center;justify-content:center;">
                          {initials}
                        </div>
                        <div>
                          <div style="font-size:0.95rem;font-weight:700;color:#0F172A;
                            font-family:'Plus Jakarta Sans',sans-serif;">{member_name}</div>
                          <div style="font-size:0.78rem;color:#64748b;font-weight:500;">{member_role}</div>
                          {email_html}
                          {dept_badge}
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Edit/remove — admins only
                if admin:
                    with st.expander("Edit", expanded=False):
                        edit_name = st.text_input("Name", value=member_name, key=f"edit_name_{member_id}")
                        edit_role = st.text_input("Role", value=member_role, key=f"edit_role_{member_id}")
                        edit_email = st.text_input("Email", value=member_email, key=f"edit_email_{member_id}")
                        dept_options = list(DEPT_LABELS.keys())
                        current_dept = member.get("department", "unassigned") or "unassigned"
                        dept_idx = dept_options.index(current_dept) if current_dept in dept_options else dept_options.index("unassigned")
                        edit_dept = st.selectbox(
                            "Department",
                            options=dept_options,
                            format_func=lambda d: DEPT_LABELS.get(d, d.capitalize()),
                            index=dept_idx,
                            key=f"edit_dept_{member_id}",
                        )
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Save", key=f"save_{member_id}", type="primary", use_container_width=True):
                                if edit_name.strip():
                                    ok = update_team_member(member_id, {
                                        "name": edit_name.strip(),
                                        "role": edit_role.strip() or "Team Member",
                                        "email": edit_email.strip() or None,
                                        "department": edit_dept,
                                        "department_color": DEPT_COLORS.get(edit_dept, MEDPORT_TEAL),
                                    })
                                    if ok:
                                        st.success("Saved.")
                                        st.rerun()
                                else:
                                    st.warning("Name required.")
                        with c2:
                            if st.button("Remove", key=f"remove_{member_id}", use_container_width=True):
                                st.session_state[f"confirm_{member_id}"] = True

                    if st.session_state.get(f"confirm_{member_id}"):
                        st.warning(f"Remove **{member_name}**?")
                        y, n = st.columns(2)
                        with y:
                            if st.button("Yes, remove", key=f"yes_{member_id}", use_container_width=True):
                                delete_team_member(member_id)
                                st.session_state.pop(f"confirm_{member_id}", None)
                                st.rerun()
                        with n:
                            if st.button("Cancel", key=f"no_{member_id}", use_container_width=True):
                                st.session_state.pop(f"confirm_{member_id}", None)
                                st.rerun()

# ─── Add Member (admins only) ─────────────────────────────────────────────────

if admin:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Add Team Member")

    st.markdown(
        f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;'
        f'padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.85rem;color:#1e40af;">'
        f'<b>Email = login identity.</b> Enter the exact Gmail address this person uses to sign into MedPort. '
        f'This is how the system knows which team member is which when they log in. '
        f'Cards, tasks, and activity will be linked to this email.'
        f'</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        new_name = st.text_input("Full Name *", key="new_name", placeholder="e.g. Ahan Sharma")
    with c2:
        new_role = st.text_input("Title / Position *", key="new_role", placeholder="e.g. CMO & Co-Founder")
    with c3:
        new_email = st.text_input("Login Email *", key="new_email", placeholder="ahan@gmail.com",
                                   help="The Gmail they use to sign in. Must match exactly.")
    with c4:
        new_dept = st.selectbox(
            "Department",
            options=list(DEPT_LABELS.keys()),
            format_func=lambda d: DEPT_LABELS.get(d, d.capitalize()),
            index=list(DEPT_LABELS.keys()).index("unassigned"),
            key="new_dept",
        )

    if st.button("Add Member", type="primary", key="do_add"):
        if not new_name.strip():
            st.warning("Full name is required.")
        elif not new_role.strip():
            st.warning("Title / Position is required.")
        elif not new_email.strip():
            st.warning("Login email is required — it's how the system identifies this person.")
        else:
            sort_order = max((m.get("sort_order", 0) for m in members), default=-1) + 1
            dept_color = DEPT_COLORS.get(new_dept, MEDPORT_TEAL)
            mid = create_team_member({
                "name": new_name.strip(),
                "role": new_role.strip(),
                "email": new_email.strip().lower(),
                "department": new_dept,
                "department_color": dept_color,
                "avatar_color": dept_color,
                "is_active": True,
                "sort_order": sort_order,
            })
            if mid:
                st.success(f"Added {new_name.strip()}. They can now sign in with {new_email.strip().lower()}.")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        f"""
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;
          padding:1rem 1.2rem;font-size:0.85rem;color:#475569;">
          <b style="color:{MEDPORT_DARK};">Admin tip:</b> Add your teammates here once.
          Their names will appear in Task assignments, CRM filters, Cards, and the Team Hub automatically.
          To grant a teammate admin access, add their email to the
          <code>ADMIN_EMAILS</code> secret in Streamlit Cloud.
        </div>
        """,
        unsafe_allow_html=True,
    )
