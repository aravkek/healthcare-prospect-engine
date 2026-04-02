"""
MedPort Marketing Hub — Ahan's command center for outreach and pipeline.
Access: marketing dept or admin only.
"""

import os
import sys
import pandas as pd
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
    page_header,
)
from lib.auth import check_auth, is_admin, render_logout_button, get_department
from lib.db import (
    load_prospects,
    update_prospect,
    get_activity_feed,
    get_team_members,
    log_activity,
    get_active_sprint,
    get_sprint_tasks,
)
from lib.sprint_widget import render_sprint_widget, render_create_sprint_form

st.set_page_config(
    page_title="Marketing Hub — MedPort",
    page_icon="📣",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)
dept = get_department(email)

# ─── Access control ───────────────────────────────────────────────────────────

if dept not in ("marketing", "leadership") and not admin:
    st.markdown(
        f"""
        <div style="padding:2rem;background:#1e293b;border-radius:1rem;
          border-left:4px solid #ef4444;margin-top:2rem;max-width:560px;">
          <div style="font-size:1.1rem;font-weight:700;color:#ef4444;margin-bottom:0.5rem;">
            Access Denied
          </div>
          <div style="font-size:0.9rem;color:#94a3b8;">
            The Marketing Hub is only available to the marketing team.
            Contact Arav if you believe this is an error.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ─── Sidebar ─────────────────────────────────────────────────────────────────

MARKETING_COLOR = DEPT_COLORS["marketing"]

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
        f'<span style="display:inline-block;background:{MARKETING_COLOR}22;color:{MARKETING_COLOR};'
        f'border:1px solid {MARKETING_COLOR}55;border-radius:999px;padding:2px 10px;'
        f'font-size:0.72rem;font-weight:600;margin-top:4px;">Marketing</span>',
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
        ("Outreach CRM", "pages/2_Outreach_CRM.py"),
        ("Tasks", "pages/3_Tasks.py"),
        ("AI Research", "pages/5_AI_Research.py"),
        ("Announcements", "pages/6_Settings.py"),
        ("Standups", "pages/7_Intelligence.py"),
        ("Settings", "pages/6_Settings.py"),
    ]
    if admin:
        nav_pages += [
            ("Finance Hub", "pages/9_Finance_Hub.py"),
        ]

    for label, page_path in nav_pages:
        try:
            st.page_link(page_path, label=label)
        except Exception:
            pass

    if st.button("Refresh data", use_container_width=True, key="mkt_refresh_btn"):
        st.cache_data.clear()
        st.rerun()

# ─── Load data ────────────────────────────────────────────────────────────────

df = load_prospects()
activities = get_activity_feed(limit=8)
members = get_team_members()

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_overview, tab_queue, tab_pipeline, tab_mine = st.tabs(
    ["Overview", "Outreach Queue", "Pipeline", "My Prospects"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview
# ══════════════════════════════════════════════════════════════════════════════

with tab_overview:
    st.markdown(
        page_header("Marketing Hub", "Ahan's command center for outreach and pipeline"),
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
        emails_sent = len(df[df["status"] == "email_sent"])
        demos_booked = len(df[df["status"] == "demo_booked"])
        converted = len(df[df["status"] == "converted"])
        denom = len(df[df["status"] != "not_contacted"])
        conv_rate = round(converted / denom * 100, 1) if denom > 0 else 0.0
    else:
        total_prospects = emails_sent = demos_booked = converted = 0
        conv_rate = 0.0

    sc1, sc2, sc3, sc4 = st.columns(4)
    for col, val, label in [
        (sc1, total_prospects, "Total Prospects"),
        (sc2, emails_sent, "Emails Sent"),
        (sc3, demos_booked, "Demos Booked"),
        (sc4, f"{conv_rate}%", "Conversion Rate"),
    ]:
        with col:
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{val}</div>'
                f'<div class="stat-label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Recent CRM activity ───────────────────────────────────────────────────

    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown("### Recent CRM Activity")

        crm_actions = {"status_change", "note_added"}
        crm_feed = [a for a in activities if a.get("action_type") in crm_actions]

        if not crm_feed:
            st.markdown(
                '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">No recent CRM activity.</div>',
                unsafe_allow_html=True,
            )
        else:
            for act in crm_feed:
                action = act.get("action_type", "")
                actor = act.get("actor_name", "Someone")
                entity = act.get("entity_name", "")
                details = act.get("details") or {}
                ts = act.get("created_at", "")

                if action == "status_change":
                    old_s = details.get("old_status", "").replace("_", " ").title()
                    new_s = details.get("new_status", "").replace("_", " ").title()
                    desc = f'moved <b>{entity}</b> {old_s} &rarr; {new_s}'
                elif action == "note_added":
                    desc = f'added a note on <b>{entity}</b>'
                else:
                    desc = f'updated <b>{entity}</b>'

                dot_color = MARKETING_COLOR if action == "status_change" else "#8b5cf6"

                st.markdown(
                    f"""
                    <div style="display:flex;align-items:flex-start;gap:0.7rem;
                      padding:0.55rem 0;border-bottom:1px solid #1e293b;">
                      <div style="width:8px;height:8px;border-radius:50%;
                        background:{dot_color};margin-top:5px;flex-shrink:0;"></div>
                      <div>
                        <span style="font-weight:600;font-size:0.85rem;color:#e2e8f0;">{actor}</span>
                        <span style="font-size:0.85rem;color:#94a3b8;"> {desc}</span>
                        {"<div style='font-size:0.72rem;color:#64748b;margin-top:1px;'>" + ts[:10] + "</div>" if ts else ""}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with right_col:
        st.markdown("### Marketing Team")
        mkt_members = [m for m in members if m.get("department") == "marketing"]
        if not mkt_members:
            mkt_members = members  # fallback to show all if no dept filtering

        for m in mkt_members:
            m_name = m.get("name", "")
            m_role = m.get("role", "")
            avatar_color = m.get("avatar_color", MARKETING_COLOR)
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:0.7rem;
                  padding:0.5rem 0.8rem;background:{MEDPORT_DARK_CARD};
                  border-radius:0.6rem;margin-bottom:0.5rem;">
                  <div style="width:34px;height:34px;border-radius:50%;
                    background:{avatar_color};display:flex;align-items:center;
                    justify-content:center;font-weight:700;font-size:0.85rem;
                    color:#fff;flex-shrink:0;">{m_name[0].upper() if m_name else "?"}</div>
                  <div>
                    <div style="font-weight:600;font-size:0.88rem;color:#e2e8f0;">{m_name}</div>
                    <div style="font-size:0.75rem;color:#64748b;">{m_role}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Outreach Queue
# ══════════════════════════════════════════════════════════════════════════════

with tab_queue:
    st.markdown("### Outreach Queue")
    st.markdown(
        '<div style="font-size:0.88rem;color:#64748b;margin-bottom:1rem;">'
        'Top uncontacted Tier A prospects — ready to reach out</div>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("No prospect data available.")
    else:
        # Sidebar-style filters within the tab
        filter_col, table_col = st.columns([1, 4])

        with filter_col:
            all_types = sorted(df["inst_type"].dropna().unique().tolist())
            mkt_type_filter = st.multiselect(
                "Institution type",
                all_types,
                key="mkt_queue_type_filter",
            )
            all_countries = sorted(df["country"].dropna().unique().tolist())
            mkt_country_filter = st.multiselect(
                "Country",
                all_countries,
                key="mkt_queue_country_filter",
            )

        queue_df = df[
            (df["priority_rank"] == 1) & (df["status"] == "not_contacted")
        ].copy()

        if mkt_type_filter:
            queue_df = queue_df[queue_df["inst_type"].isin(mkt_type_filter)]
        if mkt_country_filter:
            queue_df = queue_df[queue_df["country"].isin(mkt_country_filter)]

        queue_df = queue_df.nlargest(20, "composite_score")

        with table_col:
            if queue_df.empty:
                st.markdown(
                    '<div style="color:#8a9ab0;font-size:0.88rem;">No prospects match this filter.</div>',
                    unsafe_allow_html=True,
                )
            else:
                for _, row in queue_df.iterrows():
                    prospect_id = str(row.get("id", ""))
                    p_name = row.get("name", "Unknown")
                    p_type = row.get("inst_type", "")
                    p_city = row.get("city", "")
                    p_score = int(row.get("composite_score", 0))
                    p_rank = int(row.get("priority_rank", 3))
                    tier = {1: "A", 2: "B", 3: "C"}.get(p_rank, "C")
                    tier_bg = {"A": "#00B89F22", "B": "#3B7EFF22", "C": "#94a3b822"}.get(tier, "#94a3b822")
                    tier_color = {"A": MEDPORT_TEAL, "B": MEDPORT_BLUE, "C": "#94a3b8"}.get(tier, "#94a3b8")

                    row_left, row_right = st.columns([5, 1])
                    with row_left:
                        st.markdown(
                            f"""
                            <div style="padding:0.6rem 0.9rem;background:{MEDPORT_DARK_CARD};
                              border-radius:0.6rem;margin-bottom:0.3rem;
                              display:flex;align-items:center;gap:1rem;">
                              <div style="flex:1;">
                                <span style="font-weight:600;font-size:0.9rem;color:#e2e8f0;">{p_name}</span>
                                <span style="font-size:0.8rem;color:#64748b;margin-left:0.5rem;">{p_type} &middot; {p_city}</span>
                              </div>
                              <div style="display:flex;align-items:center;gap:0.6rem;">
                                <span style="font-size:0.8rem;color:#94a3b8;">Score: <b style="color:#e2e8f0;">{p_score}/40</b></span>
                                <span style="background:{tier_bg};color:{tier_color};border:1px solid {tier_color}55;
                                  border-radius:999px;padding:1px 9px;font-size:0.72rem;font-weight:700;">Tier {tier}</span>
                              </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with row_right:
                        if st.button(
                            "Mark Email Sent",
                            key=f"mkt_email_{prospect_id}",
                            use_container_width=True,
                        ):
                            success = update_prospect(prospect_id, {"status": "email_sent"})
                            if success:
                                log_activity(
                                    actor_email=email,
                                    actor_name=name,
                                    action_type="status_change",
                                    entity_type="prospect",
                                    entity_id=prospect_id,
                                    entity_name=p_name,
                                    details={"old_status": "not_contacted", "new_status": "email_sent"},
                                )
                                load_prospects.clear()
                                st.rerun()
                            else:
                                st.error("Failed to update. Check Supabase connection.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Pipeline
# ══════════════════════════════════════════════════════════════════════════════

with tab_pipeline:
    st.markdown("### Pipeline Funnel")

    if df.empty:
        st.info("No prospect data available.")
    else:
        # ── Funnel visualization ───────────────────────────────────────────────

        stage_counts = {}
        for stage in PIPELINE_STAGES:
            stage_counts[stage] = int((df["status"] == stage).sum())

        max_count = max(stage_counts.values()) if stage_counts else 1
        max_count = max(max_count, 1)

        funnel_html = '<div style="max-width:520px;margin:0 auto 2rem;">'
        for i, stage in enumerate(PIPELINE_STAGES):
            count = stage_counts[stage]
            pct = count / max_count
            # Funnel narrows: 100% wide at top, 40% at bottom
            width_pct = max(40, int(100 - i * 12))
            bar_color = STATUS_COLORS.get(stage, MEDPORT_TEAL)
            label = STATUS_LABELS.get(stage, stage)
            funnel_html += f"""
            <div style="width:{width_pct}%;margin:0 auto 3px;">
              <div style="background:{bar_color};border-radius:4px;padding:7px 14px;
                display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:0.82rem;font-weight:600;color:#fff;">{label}</span>
                <span style="font-size:0.88rem;font-weight:700;color:#fff;">{count}</span>
              </div>
            </div>
            """
        funnel_html += "</div>"

        st.markdown(funnel_html, unsafe_allow_html=True)

        # ── Demo booked prospects table ────────────────────────────────────────

        st.markdown("### Demos Booked")

        demo_df = df[df["status"] == "demo_booked"].copy()
        if demo_df.empty:
            st.markdown(
                '<div style="color:#8a9ab0;font-size:0.88rem;">No demos booked yet.</div>',
                unsafe_allow_html=True,
            )
        else:
            for _, row in demo_df.iterrows():
                p_name = row.get("name", "Unknown")
                p_type = row.get("inst_type", "")
                p_city = row.get("city", "")
                p_score = int(row.get("composite_score", 0))
                notes = row.get("contact_notes", "") or row.get("research_notes", "")

                st.markdown(
                    f"""
                    <div style="padding:0.75rem 1rem;background:{MEDPORT_DARK_CARD};
                      border-radius:0.7rem;margin-bottom:0.5rem;
                      border-left:3px solid #8b5cf6;">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                          <span style="font-weight:700;font-size:0.92rem;color:#e2e8f0;">{p_name}</span>
                          <span style="font-size:0.8rem;color:#64748b;margin-left:0.5rem;">{p_type} &middot; {p_city}</span>
                        </div>
                        <span style="font-size:0.8rem;color:#94a3b8;">Score: <b style="color:#e2e8f0;">{p_score}/40</b></span>
                      </div>
                      {"<div style='font-size:0.8rem;color:#64748b;margin-top:4px;'>" + notes[:120] + ("..." if len(notes) > 120 else "") + "</div>" if notes else ""}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — My Prospects
# ══════════════════════════════════════════════════════════════════════════════

with tab_mine:
    st.markdown("### My Prospects")

    if df.empty:
        st.info("No prospect data available.")
    else:
        mine_col, controls_col = st.columns([4, 1])

        with controls_col:
            mkt_show_unassigned = st.checkbox(
                "Include unassigned",
                value=False,
                key="mkt_mine_unassigned",
            )
            mkt_status_options = ["all"] + [s.replace("_", " ").title() for s in PIPELINE_STAGES]
            mkt_mine_status = st.selectbox(
                "Status filter",
                mkt_status_options,
                key="mkt_mine_status",
            )

        with mine_col:
            if mkt_show_unassigned:
                my_df = df[
                    (df["assigned_to"] == name) | (df["assigned_to"] == "Unassigned") | (df["assigned_to"] == email)
                ].copy()
            else:
                my_df = df[
                    (df["assigned_to"] == name) | (df["assigned_to"] == email)
                ].copy()

            if mkt_mine_status != "all":
                status_key = mkt_mine_status.lower().replace(" ", "_")
                my_df = my_df[my_df["status"] == status_key]

            if my_df.empty:
                st.markdown(
                    '<div style="color:#8a9ab0;font-size:0.88rem;padding:0.5rem 0;">No prospects assigned to you.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="font-size:0.82rem;color:#64748b;margin-bottom:0.8rem;">'
                    f'{len(my_df)} prospect{"s" if len(my_df) != 1 else ""}</div>',
                    unsafe_allow_html=True,
                )
                for _, row in my_df.iterrows():
                    p_name = row.get("name", "Unknown")
                    p_status = row.get("status", "not_contacted")
                    p_type = row.get("inst_type", "")
                    p_city = row.get("city", "")
                    p_score = int(row.get("composite_score", 0))
                    p_assigned = row.get("assigned_to", "Unassigned")
                    notes = row.get("contact_notes", "") or ""
                    status_color = STATUS_COLORS.get(p_status, "#64748b")
                    status_label = STATUS_LABELS.get(p_status, p_status)

                    st.markdown(
                        f"""
                        <div style="padding:0.75rem 1rem;background:{MEDPORT_DARK_CARD};
                          border-radius:0.7rem;margin-bottom:0.5rem;
                          border-left:3px solid {status_color};">
                          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                            <div>
                              <span style="font-weight:700;font-size:0.92rem;color:#e2e8f0;">{p_name}</span>
                              <span style="font-size:0.78rem;color:#64748b;margin-left:0.5rem;">{p_type} &middot; {p_city}</span>
                            </div>
                            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:3px;">
                              <span style="background:{status_color}22;color:{status_color};
                                border:1px solid {status_color}55;border-radius:999px;
                                padding:1px 9px;font-size:0.72rem;font-weight:600;">{status_label}</span>
                              <span style="font-size:0.75rem;color:#64748b;">Score: {p_score}/40</span>
                            </div>
                          </div>
                          {"<div style='font-size:0.78rem;color:#64748b;margin-top:5px;'>" + notes[:100] + ("..." if len(notes) > 100 else "") + "</div>" if notes else ""}
                          {"<div style='font-size:0.72rem;color:#475569;margin-top:3px;'>Unassigned</div>" if p_assigned in ("Unassigned", "", None) else ""}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
