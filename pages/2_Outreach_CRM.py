"""
MedPort Outreach CRM — prospect cards, pipeline tabs, saved searches.
All original CRM functionality from medport_dashboard.py, enhanced with
activity logging, saved searches, and CSV export.
"""

import os
import sys
import time
import io
from datetime import datetime, timezone

from datetime import date as _date

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import (
    inject_css, MEDPORT_BLUE, MEDPORT_GREEN, MEDPORT_TEAL, MEDPORT_LIGHT_BLUE,
    STATUS_ORDER, STATUS_LABELS, STATUS_COLORS, PIPELINE_STAGES, TEAM_MEMBERS,
)
from lib.auth import check_auth, is_admin, render_logout_button
from lib.db import (
    load_prospects, update_prospect, add_prospect, log_activity,
    get_saved_searches, save_search, delete_saved_search, increment_search_use_count,
    get_team_members,
)

st.set_page_config(
    page_title="Outreach CRM — MedPort",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)

# ─── Apply any pending preset BEFORE widgets render ──────────────────────────
# Preset buttons can't set widget-bound keys directly in newer Streamlit.
# Instead they store the desired values in _crm_preset, which we consume here.
if "_crm_preset" in st.session_state:
    for _pk, _pv in st.session_state.pop("_crm_preset").items():
        st.session_state[_pk] = _pv

# ─── Dynamic team members ────────────────────────────────────────────────────
_team_members_dynamic = get_team_members()
_dynamic_member_names = ["Unassigned"] + [m["name"] for m in _team_members_dynamic]

# ─── Badge helpers ───────────────────────────────────────────────────────────

def score_badge(score: int) -> str:
    score = int(score) if score else 0
    if score >= 8:
        return f'<span class="score-green">{score}/10</span>'
    elif score >= 5:
        return f'<span class="score-yellow">{score}/10</span>'
    return f'<span class="score-red">{score}/10</span>'


def score_bar(label: str, score: int, reason: str = "") -> str:
    score = max(0, min(10, int(score) if score else 0))
    pct = score * 10
    color = "#27ae60" if score >= 8 else ("#f39c12" if score >= 5 else "#e74c3c")
    tip = f' title="{reason}"' if reason else ""
    return (
        f'<div class="score-bar-container"{tip}>'
        f'<span class="score-bar-label">{label}</span>'
        f'<span class="score-bar-outer"><span class="score-bar-inner" style="width:{pct}%;background:{color};"></span></span>'
        f'<span class="score-bar-val" style="color:{color};">{score}/10</span>'
        f'</div>'
    )


def risk_badge(risk: str) -> str:
    risk = (risk or "none").lower()
    css = f"risk-{risk}" if risk in ("none", "low", "medium", "high") else "risk-none"
    return f'<span class="{css}">{risk.upper()}</span>'


def tier_badge(rank) -> str:
    tier = {1: "A", 2: "B", 3: "C"}.get(int(rank) if rank else 3, "C")
    return f'<span class="tier-{tier.lower()}">Tier {tier}</span>'


def type_badge(inst_type: str) -> str:
    return f'<span class="type-badge">{inst_type or "?"}</span>'


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, MEDPORT_BLUE)
    label = STATUS_LABELS.get(status, status.replace("_", " ").title())
    return f'<span class="status-badge" style="background:{color};">{label}</span>'


def country_flag(country: str) -> str:
    return {"CA": "🇨🇦", "US": "🇺🇸"}.get((country or "").upper(), "🌎")


def _parse_score_breakdown(breakdown_str: str) -> dict:
    result = {}
    if not breakdown_str:
        return result
    for part in breakdown_str.split("|"):
        part = part.strip()
        if ":" in part:
            key, rest = part.split(":", 1)
            result[key.strip().lower()] = rest.strip()
    return result


# ─── Institution card ────────────────────────────────────────────────────────

def render_institution_card(row: pd.Series, queue_mode: bool = False, key_prefix: str = ""):
    prospect_id = str(row.get("id", ""))
    name_p = row.get("name", "Unknown")
    city = row.get("city", "")
    country = row.get("country", "")
    inst_type = row.get("inst_type", "")
    website = row.get("website", "")
    phone = row.get("phone", "")
    dm_name = row.get("decision_maker_name", "")
    dm_title = row.get("decision_maker_title", "")
    dm_email = row.get("decision_maker_email", "") or ""
    dm_phone = row.get("decision_maker_phone", "") or ""
    dm_linkedin = row.get("decision_maker_linkedin", "") or ""
    dm_research = row.get("dm_research", "") or ""
    # outreach_angle is old scraped data — we never display it raw
    notes = row.get("research_notes", "")
    risk = row.get("competitor_risk", "none")
    rank = row.get("priority_rank", 3)
    def _int(val):
        """Safe int coercion — handles NaN, None, empty string."""
        try:
            import math
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return 0
            return int(val) if val else 0
        except (ValueError, TypeError):
            return 0

    inno = _int(row.get("innovation_score"))
    access = _int(row.get("accessibility_score"))
    fit = _int(row.get("fit_score"))
    startup_rx = _int(row.get("startup_receptiveness"))
    emr = row.get("emr_system", "")
    patient_vol = row.get("patient_volume", "")
    ai_tools = row.get("existing_ai_tools", "")
    phone_evidence = row.get("phone_intake_evidence", "")
    score_bd_str = row.get("score_breakdown", "")
    current_status = row.get("status", "not_contacted")
    current_assigned = row.get("assigned_to", "Unassigned") or "Unassigned"
    current_notes = row.get("contact_notes", "") or ""
    outreach_count = _int(row.get("outreach_count"))

    location = f"{country_flag(country)} {city}, {country}" if city else country_flag(country)
    border_color = STATUS_COLORS.get(current_status, MEDPORT_BLUE)
    status_label = STATUS_LABELS.get(current_status, current_status)
    composite = inno + access + fit + startup_rx

    has_research = bool(row.get("research_brief", ""))
    has_dm_research = bool(row.get("dm_research", ""))
    has_email_draft = bool((row.get("email_drafts") or []))
    next_followup = row.get("next_followup_at", "")
    followup_due = False
    if next_followup:
        try:
            followup_due = _date.fromisoformat(str(next_followup)) <= _date.today()
        except Exception:
            pass

    research_icon = "🔬" if has_research else ""
    dm_icon = "👤" if has_dm_research else ""
    email_icon = "✉️" if has_email_draft else ""
    followup_icon = "⏰" if followup_due else ""
    icons = " ".join(i for i in [research_icon, dm_icon, email_icon, followup_icon] if i)

    expander_label = f"{name_p}  —  {city}, {country}  [{status_label}]  {icons}".strip()
    if queue_mode:
        expander_label = f"📧 {name_p}  —  {city}, {country}  {icons}".strip()

    with st.expander(expander_label, expanded=queue_mode):
        st.markdown(f'<div style="border-left:4px solid {border_color};padding-left:0.7rem;">', unsafe_allow_html=True)

        col_title, col_tier = st.columns([5, 1])
        with col_title:
            st.markdown(
                f'<div class="inst-header">{location} &nbsp; {name_p}</div>'
                f'<div class="inst-meta">{type_badge(inst_type)} &nbsp; {status_badge(current_status)} &nbsp; {risk_badge(risk)}</div>',
                unsafe_allow_html=True,
            )
        with col_tier:
            st.markdown(
                f'<div style="text-align:right;margin-top:4px;">{tier_badge(rank)}<br>'
                f'<span style="font-size:0.72rem;color:#6b7a8d;">{composite}/40</span></div>',
                unsafe_allow_html=True,
            )

        # Research status badges + profile link
        badge_parts = []
        if has_research:
            badge_parts.append('<span style="background:#f0fdf9;color:#059669;border:1px solid #bbf7d0;border-radius:6px;padding:2px 8px;font-size:0.72rem;font-weight:600;">🔬 Researched</span>')
        else:
            badge_parts.append('<span style="background:#f8fafc;color:#94a3b8;border:1px solid #e2e8f0;border-radius:6px;padding:2px 8px;font-size:0.72rem;font-weight:600;">Research needed</span>')
        if has_dm_research:
            badge_parts.append('<span style="background:#eff6ff;color:#2563EB;border:1px solid #bfdbfe;border-radius:6px;padding:2px 8px;font-size:0.72rem;font-weight:600;">👤 DM profiled</span>')
        if has_email_draft:
            badge_parts.append('<span style="background:#faf5ff;color:#7C3AED;border:1px solid #e9d5ff;border-radius:6px;padding:2px 8px;font-size:0.72rem;font-weight:600;">✉️ Draft ready</span>')
        if followup_due:
            badge_parts.append('<span style="background:#fef2f2;color:#DC2626;border:1px solid #fecaca;border-radius:6px;padding:2px 8px;font-size:0.72rem;font-weight:700;">⏰ Follow-up due</span>')

        if badge_parts:
            st.markdown(" &nbsp;".join(badge_parts), unsafe_allow_html=True)

        st.markdown('<hr class="subtle">', unsafe_allow_html=True)

        score_bd = _parse_score_breakdown(score_bd_str)
        fit_reason = score_bd.get("fit", "").split("—", 1)[-1].strip() if "fit" in score_bd else ""
        inno_reason = score_bd.get("innovation", "").split("—", 1)[-1].strip() if "innovation" in score_bd else ""
        access_reason = score_bd.get("access", score_bd.get("accessibility", "")).split("—", 1)[-1].strip()
        startup_reason = score_bd.get("startup_fit", score_bd.get("startup", "")).split("—", 1)[-1].strip()

        bar_html = (
            score_bar("Phone Fit", fit, fit_reason)
            + score_bar("Innovation", inno, inno_reason)
            + score_bar("Accessibility", access, access_reason)
            + score_bar("Startup Fit", startup_rx, startup_reason)
        )
        st.markdown(bar_html, unsafe_allow_html=True)

        pills = []
        if patient_vol:
            pills.append(f'<span class="info-pill"><b>Volume:</b> {patient_vol}</span>')
        if emr and emr.lower() not in ("unknown", ""):
            pills.append(f'<span class="info-pill"><b>EMR:</b> {emr}</span>')
        if ai_tools and ai_tools.lower() not in ("none detected", ""):
            pills.append(f'<span class="info-pill" style="background:#fde8e8;"><b>AI tools:</b> {ai_tools}</span>')
        if phone_evidence:
            pills.append(f'<span class="info-pill" style="background:#e8f4fd;"><b>Phone evidence:</b> "{phone_evidence}"</span>')
        if pills:
            st.markdown(" ".join(pills) + "<br>", unsafe_allow_html=True)

        st.markdown("")

        # ── Decision Maker section ──────────────────────────────────────────
        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;'
            'padding:0.75rem 1rem;margin:0.5rem 0;">',
            unsafe_allow_html=True,
        )
        st.markdown("**Contact Person**")

        if dm_name or dm_title:
            _dm_header = f"**{dm_name}**" if dm_name else ""
            _dm_sub = f" &nbsp;·&nbsp; {dm_title}" if dm_title else ""
            st.markdown(
                f'<div style="font-size:0.95rem;color:#0F172A;">{_dm_header}'
                f'<span style="font-weight:400;color:#64748b;">{_dm_sub}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No contact identified yet — add one in Full Profile")

        # Contact details row
        _contact_parts = []
        if dm_email:
            _contact_parts.append(f'📧 <a href="mailto:{dm_email}" style="color:{MEDPORT_TEAL};font-weight:600;">{dm_email}</a>')
        if dm_phone:
            _contact_parts.append(f'📞 <span style="color:#475569;">{dm_phone}</span>')
        if dm_linkedin:
            _contact_parts.append(f'🔗 <a href="https://www.linkedin.com/search/results/all/?keywords={dm_linkedin}" target="_blank" style="color:{MEDPORT_BLUE};">LinkedIn</a>')
        if _contact_parts:
            st.markdown(
                '<div style="font-size:0.82rem;margin-top:0.3rem;">' +
                " &nbsp;&nbsp; ".join(_contact_parts) + "</div>",
                unsafe_allow_html=True,
            )
        elif dm_name:
            st.caption("Add their email and phone in Full Profile →")

        # DM personality brief (from AI research)
        if dm_research:
            # Extract just the key approach sections — first 600 chars or up to a section break
            _brief = dm_research[:700].strip()
            # Try to find the approach/hooks section
            for _marker in ["HOW TO REACH", "HOW TO WRITE", "WHAT RESONATES", "PERSONALIZATION HOOKS", "SUGGESTED EMAIL OPENER"]:
                _idx = dm_research.upper().find(_marker)
                if _idx != -1:
                    _brief = dm_research[_idx:_idx + 600].strip()
                    break
            st.markdown(
                f'<div style="margin-top:0.5rem;padding:0.5rem 0.75rem;background:#fff;'
                f'border-left:3px solid {MEDPORT_TEAL};border-radius:0 6px 6px 0;'
                f'font-size:0.8rem;color:#334155;white-space:pre-wrap;max-height:120px;overflow-y:auto;">'
                f'{_brief}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="margin-top:0.4rem;font-size:0.8rem;color:#94a3b8;">'
                f'No personality brief yet — click <b>Full Profile →</b> then run <b>Decision Maker Research</b> '
                f'to get a bio, communication style, and best approach for this person.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if notes:
            with st.expander("Research notes", expanded=False):
                st.markdown(notes)

        if score_bd_str and score_bd_str not in ("-", ""):
            with st.expander("Score breakdown details", expanded=False):
                st.markdown(f"```\n{score_bd_str}\n```")

        link_parts = []
        if website:
            link_parts.append(f"[Website]({website})")
        if phone:
            link_parts.append(f"Phone: `{phone}`")
        if link_parts:
            st.markdown(" &nbsp; | &nbsp; ".join(link_parts), unsafe_allow_html=True)

        st.markdown('<hr class="subtle">', unsafe_allow_html=True)

        crm1, crm2 = st.columns(2)
        with crm1:
            try:
                status_idx = STATUS_ORDER.index(current_status)
            except ValueError:
                status_idx = 0
            new_status = st.selectbox(
                "Pipeline status",
                STATUS_ORDER,
                index=status_idx,
                format_func=lambda s: STATUS_LABELS.get(s, s),
                key=f"{key_prefix}status_{prospect_id}",
            )
            if new_status != current_status:
                update_prospect(
                    prospect_id,
                    {
                        "status": new_status,
                        "last_contacted_at": datetime.now(timezone.utc).isoformat(),
                        "outreach_count": outreach_count + (1 if new_status == "email_sent" else 0),
                    },
                )
                log_activity(
                    actor_email=email,
                    actor_name=name,
                    action_type="status_change",
                    entity_type="prospect",
                    entity_id=prospect_id,
                    entity_name=name_p,
                    details={"old_status": current_status, "new_status": new_status},
                )
                st.cache_data.clear()
                st.rerun()

        with crm2:
            try:
                assign_idx = _dynamic_member_names.index(current_assigned)
            except ValueError:
                assign_idx = 0
            new_assigned = st.selectbox(
                "Assigned to",
                _dynamic_member_names,
                index=assign_idx,
                key=f"{key_prefix}assign_{prospect_id}",
            )
            if new_assigned != current_assigned:
                update_prospect(prospect_id, {"assigned_to": new_assigned})
                st.cache_data.clear()
                st.rerun()

        new_notes = st.text_area(
            "Contact notes",
            value=current_notes,
            height=75,
            key=f"{key_prefix}notes_{prospect_id}",
            placeholder="e.g. Emailed director on Apr 3. She asked for a demo video...",
        )
        if st.button("Save notes", key=f"{key_prefix}save_{prospect_id}"):
            update_prospect(prospect_id, {"contact_notes": new_notes})
            log_activity(
                actor_email=email,
                actor_name=name,
                action_type="note_added",
                entity_type="prospect",
                entity_id=prospect_id,
                entity_name=name_p,
            )
            st.success("Saved.")
            st.cache_data.clear()

        if outreach_count > 0:
            st.caption(f"Outreach sent {outreach_count}x")

        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        st.page_link(
            "pages/16_Prospect_Profile.py",
            label="🔍 Open Full Profile — Research, DM Bio & Email Drafts",
            use_container_width=True,
            query_params={"id": prospect_id},
        )

        st.markdown("</div>", unsafe_allow_html=True)


# ─── Sidebar with filters ────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">MedPort CRM</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='font-size:0.8rem;color:#94a3b8;'>{name}</div>", unsafe_allow_html=True)
    st.markdown("---")

    render_logout_button()

    auto_refresh = st.toggle("Auto-refresh (30s)", value=False, key="crm_refresh")

    st.markdown("### Filters")
    my_only = st.toggle("My Prospects only", value=False, key="crm_my_only")
    country_opt = st.radio("Market", ["Both", "US", "CA"], horizontal=True, key="crm_country")

    _df_all = load_prospects()
    has_data = len(_df_all) > 0

    if has_data and "inst_type" in _df_all.columns:
        all_types = sorted(_df_all["inst_type"].unique().tolist())
    else:
        all_types = ["CHC", "FQHC", "hospital", "university", "walk-in", "specialty"]
    selected_types = st.multiselect("Institution Type", all_types, default=all_types, key="crm_types")
    selected_tiers = st.multiselect("Tier", ["A", "B", "C"], default=["A", "B"], key="crm_tiers")
    selected_statuses = st.multiselect(
        "Status", STATUS_ORDER, default=STATUS_ORDER,
        format_func=lambda s: STATUS_LABELS.get(s, s), key="crm_statuses",
    )
    selected_assignee = st.selectbox("Assigned to", ["All"] + _dynamic_member_names, key="crm_assignee")
    min_score = st.slider("Min Score (out of 40)", 0, 40, 0, 1, key="crm_min_score")
    needs_research = st.toggle("Needs research only", value=False, key="crm_needs_research")
    followup_due_filter = st.toggle("Follow-up due", value=False, key="crm_followup_due")

    st.markdown("---")
    st.markdown("### Saved Searches")

    saved = get_saved_searches(email)
    personal = [s for s in saved if s.get("owner_email") == email]
    shared = [s for s in saved if s.get("is_team_shared") and s.get("owner_email") != email]

    def _load_search(s: dict):
        f = s.get("filters", {})
        if "my_only" in f:
            st.session_state["crm_my_only"] = f["my_only"]
        if "country" in f:
            st.session_state["crm_country"] = f["country"]
        if "tiers" in f:
            st.session_state["crm_tiers"] = f["tiers"]
        if "statuses" in f:
            st.session_state["crm_statuses"] = f["statuses"]
        if "assignee" in f:
            st.session_state["crm_assignee"] = f["assignee"]
        if "min_score" in f:
            st.session_state["crm_min_score"] = f["min_score"]
        increment_search_use_count(s["id"])
        st.rerun()

    if personal:
        st.markdown("**My searches:**")
        for s in personal[:5]:
            col_a, col_b = st.columns([4, 1])
            with col_a:
                if st.button(s["name"], key=f"load_search_{s['id']}", use_container_width=True):
                    _load_search(s)
            with col_b:
                if st.button("✕", key=f"del_search_{s['id']}"):
                    delete_saved_search(s["id"])
                    st.rerun()

    if shared:
        st.markdown("**Team searches:**")
        for s in shared[:5]:
            if st.button(f"[Team] {s['name']}", key=f"load_shared_{s['id']}", use_container_width=True):
                _load_search(s)

    st.markdown("---")
    st.markdown("### Actions")
    if st.button("Refresh Data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()

# ─── Load and filter ─────────────────────────────────────────────────────────

df = load_prospects()
if df.empty:
    st.info("No data yet. Add prospects to your Supabase database.")
    st.stop()

# Apply filters
filtered = df.copy()
if my_only:
    filtered = filtered[filtered["assigned_to"] == name]
if country_opt != "Both":
    filtered = filtered[filtered["country"] == country_opt]
if selected_types:
    filtered = filtered[filtered["inst_type"].isin(selected_types)]
tier_rank_map = {"A": 1, "B": 2, "C": 3}
selected_ranks = [tier_rank_map[t] for t in selected_tiers if t in tier_rank_map]
if selected_ranks:
    filtered = filtered[filtered["priority_rank"].isin(selected_ranks)]
if selected_statuses:
    filtered = filtered[filtered["status"].isin(selected_statuses)]
if selected_assignee != "All":
    if selected_assignee == "Unassigned":
        filtered = filtered[filtered["assigned_to"].isin(["Unassigned", "", None])]
    else:
        filtered = filtered[filtered["assigned_to"] == selected_assignee]
if min_score > 0:
    filtered = filtered[filtered["composite_score"] >= min_score]
if needs_research and "research_brief" in filtered.columns:
    filtered = filtered[filtered["research_brief"].fillna("") == ""]
if followup_due_filter and "next_followup_at" in filtered.columns:
    today_str = _date.today().isoformat()
    filtered = filtered[filtered["next_followup_at"].fillna("").astype(str) <= today_str]
    filtered = filtered[filtered["next_followup_at"].fillna("").astype(str) != ""]

# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown("# Outreach CRM")

# Save / export row
save_col, export_col, _ = st.columns([2, 2, 6])
with save_col:
    with st.popover("Save this search"):
        search_name = st.text_input("Search name", key="new_search_name")
        share_search = st.checkbox("Share with team", key="share_search_toggle")
        if st.button("Save", key="do_save_search"):
            if search_name.strip():
                save_search({
                    "owner_email": email,
                    "name": search_name.strip(),
                    "filters": {
                        "my_only": my_only,
                        "country": country_opt,
                        "types": selected_types,
                        "tiers": selected_tiers,
                        "statuses": selected_statuses,
                        "assignee": selected_assignee,
                        "min_score": min_score,
                    },
                    "is_team_shared": share_search,
                })
                log_activity(
                    actor_email=email, actor_name=name,
                    action_type="search_run", entity_type="search",
                    entity_name=search_name.strip(),
                )
                st.success("Search saved.")
                get_saved_searches.clear()

with export_col:
    csv_buf = io.StringIO()
    filtered.to_csv(csv_buf, index=False)
    st.download_button(
        "Export CSV",
        data=csv_buf.getvalue(),
        file_name=f"medport_prospects_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="export_csv",
    )

# ─── Funnel ──────────────────────────────────────────────────────────────────

funnel_html = '<div class="funnel-row">'
for stage in PIPELINE_STAGES:
    count = len(df[df["status"] == stage])
    color = STATUS_COLORS[stage]
    label = STATUS_LABELS[stage]
    funnel_html += (
        f'<div class="funnel-step" style="background:{color};">'
        f'<span class="funnel-count">{count}</span>'
        f'<span class="funnel-label">{label}</span>'
        f'</div>'
    )
declined = len(df[df["status"] == "declined"])
funnel_html += (
    f'<div class="funnel-step" style="background:{STATUS_COLORS["declined"]};min-width:70px;flex:0.6;">'
    f'<span class="funnel-count">{declined}</span>'
    f'<span class="funnel-label">Declined</span>'
    f'</div>'
)
funnel_html += "</div>"
st.markdown(funnel_html, unsafe_allow_html=True)

# ─── Stats row ───────────────────────────────────────────────────────────────

total = len(filtered)
tier_a = len(filtered[filtered["priority_rank"] == 1])
us_count = len(filtered[filtered["country"] == "US"])
ca_count = len(filtered[filtered["country"] == "CA"])
avg_score = round(filtered["composite_score"].mean(), 1) if total > 0 else 0.0
converted_count = len(df[df["status"] == "converted"])
uncontacted_a = len(df[(df["priority_rank"] == 1) & (df["status"] == "not_contacted")])

c1, c2, c3, c4, c5, c6 = st.columns(6)
for col, val, label in [
    (c1, total, "Showing"),
    (c2, tier_a, "Tier A"),
    (c3, f"{us_count} / {ca_count}", "US / CA"),
    (c4, f"{avg_score}/40", "Avg Score"),
    (c5, converted_count, "Converted"),
    (c6, uncontacted_a, "Tier A Queue"),
]:
    with col:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value">{val}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("")

# ─── Filter status bar ───────────────────────────────────────────────────────

active_filters = []
if country_opt != "Both":
    active_filters.append(f"Market: {country_opt}")
if my_only:
    active_filters.append("My prospects only")
if selected_tiers != ["A", "B", "C"]:
    active_filters.append(f"Tier: {', '.join(selected_tiers)}")
if min_score > 0:
    active_filters.append(f"Score ≥ {min_score}")
if selected_assignee != "All":
    active_filters.append(f"Assigned: {selected_assignee}")

if active_filters:
    tags_html = " ".join(f'<span class="filter-tag">{f}</span>' for f in active_filters)
    st.markdown(
        f'<div class="filter-bar">'
        f'<span style="font-weight:600;color:#475569;">Showing {len(filtered)} of {len(df)}</span>'
        f'<span style="color:#cbd5e1;">·</span>'
        f'{tags_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ─── Queue alert ─────────────────────────────────────────────────────────────

QUEUE_SIZE = 15
if uncontacted_a > 0:
    st.markdown(
        f'<div class="alert-box"><b>Outreach Queue:</b> {uncontacted_a} Tier A prospects not yet contacted. '
        f'Work through the <b>Queue</b> tab — as you email them, new ones appear automatically.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("")

# ─── Tabs ────────────────────────────────────────────────────────────────────

# ── Quick-filter presets ──────────────────────────────────────────────────────
st.markdown("**Quick filters:**")
qf_cols = st.columns(8)
_PRESETS = [
    ("🇨🇦 Tier A", {"crm_country": "CA", "crm_tiers": ["A"]}),
    ("🇺🇸 Tier A", {"crm_country": "US", "crm_tiers": ["A"]}),
    ("🇨🇦 Tier B", {"crm_country": "CA", "crm_tiers": ["B"]}),
    ("🇺🇸 Tier B", {"crm_country": "US", "crm_tiers": ["B"]}),
    ("📬 Follow-up", {"crm_followup_due": True}),
    ("🔬 Needs Research", {"crm_needs_research": True}),
    ("📅 Demo Stage", {"crm_statuses": ["demo_booked"]}),
    ("🔄 Reset", {"crm_country": "Both", "crm_tiers": ["A", "B", "C"], "crm_statuses": STATUS_ORDER, "crm_my_only": False, "crm_needs_research": False, "crm_followup_due": False}),
]
for _pi, (_plabel, _pstate) in enumerate(_PRESETS):
    with qf_cols[_pi]:
        if st.button(_plabel, key=f"preset_{_pi}", use_container_width=True):
            st.session_state["_crm_preset"] = _pstate
            st.rerun()

st.markdown("")

tab_queue, tab_a, tab_b, tab_c, tab_ca, tab_us, tab_pipeline, tab_add = st.tabs([
    f"Queue ({uncontacted_a})", "Tier A", "Tier B", "Tier C", "🇨🇦 Canadian", "🇺🇸 American", "Pipeline", "➕ Add Contact"
])


def render_tier_tab(df_subset: pd.DataFrame, empty_msg: str = "No institutions here.", tab_key: str = "tier"):
    if df_subset.empty:
        st.info(empty_msg)
        return
    df_subset = df_subset.sort_values("composite_score", ascending=False)
    for _, row in df_subset.iterrows():
        render_institution_card(row, key_prefix=f"{tab_key}_")


with tab_queue:
    st.markdown(
        "**Your Outreach Queue** — Top uncontacted Tier A prospects, sorted by score. "
        "Email them, then move the status to *Email Sent*. The queue auto-refills as you work through it."
    )
    queue_show = filtered[(filtered["priority_rank"] == 1) & (filtered["status"] == "not_contacted")].sort_values(
        "composite_score", ascending=False
    ).head(QUEUE_SIZE)
    if queue_show.empty:
        st.success("All Tier A prospects have been contacted. Check Tier B next.")
    else:
        for _, row in queue_show.iterrows():
            render_institution_card(row, queue_mode=True, key_prefix="queue_")

with tab_a:
    render_tier_tab(filtered[filtered["priority_rank"] == 1], "No Tier A prospects match your current filters.", "ta")

with tab_b:
    render_tier_tab(filtered[filtered["priority_rank"] == 2], "No Tier B prospects match your current filters.", "tb")

with tab_c:
    render_tier_tab(filtered[filtered["priority_rank"] == 3], "No Tier C prospects match your current filters.", "tc")

with tab_ca:
    st.markdown("### 🇨🇦 Canadian Prospects")
    ca_df = filtered[filtered["country"] == "CA"].sort_values(["priority_rank", "composite_score"], ascending=[True, False])
    if ca_df.empty:
        st.info("No Canadian prospects match current filters.")
    else:
        ca_a = len(ca_df[ca_df["priority_rank"] == 1])
        ca_b = len(ca_df[ca_df["priority_rank"] == 2])
        ca_contacted = len(ca_df[ca_df["status"] != "not_contacted"])
        c1, c2, c3 = st.columns(3)
        c1.metric("CA Tier A", ca_a)
        c2.metric("CA Tier B", ca_b)
        c3.metric("CA Contacted", ca_contacted)
        st.markdown("")
        for _, row in ca_df.iterrows():
            render_institution_card(row, key_prefix="ca_")

with tab_us:
    st.markdown("### 🇺🇸 American Prospects")
    us_df = filtered[filtered["country"] == "US"].sort_values(["priority_rank", "composite_score"], ascending=[True, False])
    if us_df.empty:
        st.info("No US prospects match current filters.")
    else:
        us_a = len(us_df[us_df["priority_rank"] == 1])
        us_b = len(us_df[us_df["priority_rank"] == 2])
        us_contacted = len(us_df[us_df["status"] != "not_contacted"])
        u1, u2, u3 = st.columns(3)
        u1.metric("US Tier A", us_a)
        u2.metric("US Tier B", us_b)
        u3.metric("US Contacted", us_contacted)
        st.markdown("")
        for _, row in us_df.iterrows():
            render_institution_card(row, key_prefix="us_")

with tab_pipeline:
    st.markdown("### Pipeline — All Institutions by Stage")
    st.caption("Move prospects between stages by opening their card and changing the Pipeline Status dropdown. Everyone on the team can update this.")
    for stage in STATUS_ORDER:
        stage_df = df[df["status"] == stage].sort_values("composite_score", ascending=False)
        count = len(stage_df)
        color = STATUS_COLORS[stage]
        label = STATUS_LABELS[stage]
        st.markdown(
            f'<div style="border-left:4px solid {color};padding-left:0.8rem;margin:1rem 0 0.3rem 0;">'
            f'<b style="color:{color};">{label}</b> &nbsp; <span style="color:#6b7a8d;">'
            f'{count} institution{"s" if count != 1 else ""}</span></div>',
            unsafe_allow_html=True,
        )
        if count > 0:
            for _, row in stage_df.iterrows():
                render_institution_card(row, key_prefix=f"pipe_{stage}_")
        else:
            st.caption("None yet.")
        st.markdown("")

# ─── Add Contact Tab ──────────────────────────────────────────────────────────

with tab_add:
    st.markdown("### Add a New Contact")
    st.markdown(
        '<div style="color:#64748b;font-size:0.9rem;margin-bottom:1.25rem;">'
        "Manually add any clinic, hospital, dental, physio, mental health, or university contact "
        "you've met or communicated with. They'll appear in the CRM instantly."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("add_contact_form", clear_on_submit=True):

        # ── Institution info ──────────────────────────────────────────────────
        st.markdown("#### Institution")
        ac_col1, ac_col2 = st.columns(2)
        with ac_col1:
            ac_name = st.text_input("Institution / Clinic Name *", placeholder="e.g. UHN Toronto General", max_chars=200)
            ac_type = st.selectbox(
                "Type *",
                ["clinic", "university_health", "hospital", "dental", "physio",
                 "mental_health", "walk_in", "specialist", "other"],
                format_func=lambda t: {
                    "clinic": "Clinic (GP / Family Medicine)",
                    "university_health": "University Health Centre",
                    "hospital": "Hospital / Health System",
                    "dental": "Dental Practice",
                    "physio": "Physiotherapy / Rehab",
                    "mental_health": "Mental Health / Counselling",
                    "walk_in": "Walk-in Clinic",
                    "specialist": "Specialist Clinic",
                    "other": "Other",
                }.get(t, t),
            )
            ac_city = st.text_input("City *", placeholder="e.g. Windsor", max_chars=100)
        with ac_col2:
            ac_province = st.selectbox(
                "Province / State",
                ["ON", "BC", "AB", "QC", "MB", "SK", "NS", "NB", "NL", "PE", "NT", "YT", "NU",
                 "CA (Other)", "NY", "MI", "OH", "PA", "IL", "TX", "CA (US)", "US (Other)"],
            )
            ac_country = st.selectbox("Country", ["CA", "US"])
            ac_website = st.text_input("Website", placeholder="https://", max_chars=300)
            ac_phone = st.text_input("Main Phone", placeholder="(519) 555-0100", max_chars=30)

        ac_emr = st.text_input(
            "EMR / Booking System (if known)",
            placeholder="e.g. Jane App, OSCAR, Accuro, phone only…",
            max_chars=100,
        )

        st.markdown("---")

        # ── Decision maker ────────────────────────────────────────────────────
        st.markdown("#### Decision Maker (if known)")
        dm_col1, dm_col2 = st.columns(2)
        with dm_col1:
            ac_dm_name = st.text_input("Full Name", placeholder="e.g. Dr. Mohsan Beg", max_chars=150)
            ac_dm_title = st.text_input("Title / Role", placeholder="e.g. Executive Director", max_chars=150)
            ac_dm_email = st.text_input("Email", placeholder="mbeg@uwindsor.ca", max_chars=200)
        with dm_col2:
            ac_dm_phone = st.text_input("Phone (direct)", placeholder="(519) 555-0101", max_chars=30)
            ac_dm_linkedin = st.text_input("LinkedIn URL", placeholder="linkedin.com/in/...", max_chars=300)

        st.markdown("---")

        # ── CRM settings ──────────────────────────────────────────────────────
        st.markdown("#### CRM Settings")
        crm_col1, crm_col2, crm_col3 = st.columns(3)
        with crm_col1:
            ac_tier = st.selectbox(
                "Tier",
                ["A", "B", "C"],
                index=1,
                format_func=lambda t: {"A": "A — High priority", "B": "B — Medium priority", "C": "C — Low priority"}.get(t, t),
            )
        with crm_col2:
            ac_score = st.slider("Initial Score (1–10)", min_value=1, max_value=10, value=5)
        with crm_col3:
            ac_assigned = st.selectbox(
                "Assign to",
                _dynamic_member_names,
                index=0,
            )

        ac_notes = st.text_area(
            "Notes (context, how you met, what was discussed)",
            placeholder="Met at MedHacks Toronto. They mentioned wanting to reduce phone calls…",
            max_chars=1000,
            height=100,
        )

        submitted = st.form_submit_button("Add to CRM", type="primary", use_container_width=True)

    if submitted:
        if not ac_name.strip():
            st.error("Institution name is required.")
        else:
            new_id = add_prospect({
                "name":             ac_name.strip(),
                "inst_type":        ac_type,
                "city":             ac_city.strip(),
                "province":         ac_province,
                "country":          ac_country,
                "website":          ac_website.strip(),
                "phone":            ac_phone.strip(),
                "emr_system":       ac_emr.strip(),
                "tier":             ac_tier,
                "composite_score":  ac_score,
                "assigned_to":      ac_assigned,
                "contact_notes":    ac_notes.strip(),
                "decision_maker_name":     ac_dm_name.strip(),
                "decision_maker_title":    ac_dm_title.strip(),
                "decision_maker_email":    ac_dm_email.strip(),
                "decision_maker_phone":    ac_dm_phone.strip(),
                "decision_maker_linkedin": ac_dm_linkedin.strip(),
            })
            if new_id:
                log_activity(
                    actor_email=email, actor_name=name,
                    action_type="prospect_added", entity_type="prospect",
                    entity_id=new_id, entity_name=ac_name.strip(),
                    details={"tier": ac_tier, "type": ac_type, "city": ac_city},
                )
                st.success(f"✅ **{ac_name.strip()}** added to CRM as Tier {ac_tier}.")
                st.info("Find them in the Tier tabs above. Run Institution Research and DM Research from their Full Profile.")
