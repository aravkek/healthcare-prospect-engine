"""
MedPort Prospect Profile — full intelligence dossier + action center for a single prospect.
Loaded via query param: ?id=<prospect_id>
"""

import os
import sys
import json
from datetime import datetime, timezone, date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="Prospect Profile — MedPort",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

from lib.auth import check_auth, is_admin, render_logout_button
from lib.styles import (
    inject_css,
    MEDPORT_TEAL, MEDPORT_DARK, MEDPORT_BLUE,
    STATUS_COLORS, STATUS_LABELS, STATUS_ORDER,
    page_header,
)
from lib.db import (
    get_prospect_by_id, update_prospect, save_prospect_research,
    add_email_draft, log_outreach_event, load_prospects, get_team_members,
)
from lib.ai import (
    research_institution, research_decision_maker, analyze_fit,
    draft_outreach_email, draft_followup_email, has_ai_configured,
)

inject_css()
name, email = check_auth()
admin = is_admin(email)

# ─── Query param ─────────────────────────────────────────────────────────────

prospect_id = st.query_params.get("id")

if not prospect_id:
    st.markdown(
        f'<div style="padding:3rem 0;text-align:center;">'
        f'<div style="font-size:2rem;margin-bottom:0.5rem;">🎯</div>'
        f'<div class="page-title" style="margin-bottom:0.75rem;">No prospect selected</div>'
        f'<div style="color:#64748b;margin-bottom:1.5rem;">Go back to the CRM and click a prospect to view its profile.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Outreach_CRM.py", label="← Back to Outreach CRM")
    st.stop()

# ─── Load prospect ────────────────────────────────────────────────────────────

prospect = get_prospect_by_id(prospect_id)

if not prospect:
    st.markdown(
        f'<div style="padding:3rem 0;text-align:center;">'
        f'<div style="font-size:2rem;margin-bottom:0.5rem;">404</div>'
        f'<div class="page-title" style="margin-bottom:0.75rem;">Prospect not found</div>'
        f'<div style="color:#64748b;margin-bottom:1.5rem;">This prospect may have been deleted, or the ID is invalid.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Outreach_CRM.py", label="← Back to Outreach CRM")
    st.stop()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _s(key: str, fallback="") -> str:
    """Safe string getter from prospect dict."""
    v = prospect.get(key)
    return str(v) if v not in (None, "") else fallback


def _i(key: str, fallback: int = 0) -> int:
    v = prospect.get(key)
    try:
        return int(v) if v is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _json_list(key: str) -> list:
    """Parse a JSONB list field — returns [] on None / bad data."""
    v = prospect.get(key)
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _relative_date(iso_str: str) -> str:
    """Convert ISO date string to 'X days ago' / 'today'."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        days = delta.days
        if days == 0:
            return "today"
        if days == 1:
            return "yesterday"
        if days < 7:
            return f"{days} days ago"
        if days < 30:
            return f"{days // 7}w ago"
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso_str[:10]


def _fmt_date(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M UTC")
    except Exception:
        return iso_str[:16]


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


def type_badge(inst_type: str) -> str:
    return f'<span class="type-badge">{inst_type or "?"}</span>'


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, MEDPORT_BLUE)
    label = STATUS_LABELS.get(status, status.replace("_", " ").title())
    return f'<span class="status-badge" style="background:{color};">{label}</span>'


def tier_badge(rank) -> str:
    tier = {1: "A", 2: "B", 3: "C"}.get(int(rank) if rank else 3, "C")
    return f'<span class="tier-{tier.lower()}">Tier {tier}</span>'


def country_flag(country: str) -> str:
    return {"CA": "🇨🇦", "US": "🇺🇸"}.get((country or "").upper(), "🌎")


def event_type_color(event_type: str) -> str:
    return {
        "email_sent": MEDPORT_BLUE,
        "follow_up_sent": "#60a5fa",
        "call_made": "#8b5cf6",
        "meeting_held": MEDPORT_TEAL,
        "email_opened": "#06b6d4",
        "responded": "#22c55e",
        "demo_given": "#f59e0b",
    }.get(event_type, "#94a3b8")


def event_type_label(event_type: str) -> str:
    return {
        "email_sent": "Email Sent",
        "follow_up_sent": "Follow-up Sent",
        "call_made": "Call Made",
        "meeting_held": "Meeting Held",
        "email_opened": "Email Opened",
        "responded": "Responded",
        "demo_given": "Demo Given",
    }.get(event_type, event_type.replace("_", " ").title())


# ─── Extract prospect fields ──────────────────────────────────────────────────

p_name = _s("name", "Unnamed Prospect")
p_city = _s("city")
p_country = _s("country")
p_inst_type = _s("inst_type")
p_status = _s("status", "not_contacted")
p_rank = _i("priority_rank", 3)
p_website = _s("website")
p_phone = _s("phone")
p_emr = _s("emr_system")
p_patient_vol = _s("patient_volume")
p_ai_tools = _s("existing_ai_tools")
p_phone_evidence = _s("phone_intake_evidence")
p_inno = _i("innovation_score")
p_access = _i("accessibility_score")
p_fit = _i("fit_score")
p_startup_rx = _i("startup_receptiveness")
p_research_brief = _s("research_brief")
p_dm_research = _s("dm_research")
p_fit_analysis = _s("fit_analysis")
p_research_updated_at = _s("research_updated_at")
p_dm_name = _s("decision_maker_name")
p_dm_title = _s("decision_maker_title")
p_dm_email = _s("decision_maker_email")
p_dm_phone = _s("decision_maker_phone")
p_dm_linkedin = _s("decision_maker_linkedin")
p_contact_notes = _s("contact_notes")
p_assigned = _s("assigned_to", "Unassigned")
p_outreach_count = _i("outreach_count")
p_last_contacted_at = _s("last_contacted_at")
p_next_followup_at = _s("next_followup_at")
p_response_type = _s("response_type", "none")

email_drafts = _json_list("email_drafts")
outreach_timeline = _json_list("outreach_timeline")

_team_members_raw = get_team_members()
_team_member_names = ["Unassigned"] + [m["name"] for m in _team_members_raw]

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">MedPort CRM</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='font-size:0.8rem;color:#94a3b8;'>Signed in as {name}</div>", unsafe_allow_html=True)
    st.markdown("---")
    render_logout_button()
    st.markdown("---")
    st.page_link("pages/2_Outreach_CRM.py", label="← Back to Outreach CRM")
    st.markdown("---")

    # Quick stats in sidebar
    st.markdown(
        f'<div style="font-size:0.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-bottom:0.5rem;">Quick Info</div>',
        unsafe_allow_html=True,
    )
    if p_outreach_count:
        st.markdown(f"<div style='font-size:0.8125rem;color:#cbd5e1;'>Outreach sent: <b style='color:white;'>{p_outreach_count}x</b></div>", unsafe_allow_html=True)
    if p_last_contacted_at:
        st.markdown(f"<div style='font-size:0.8125rem;color:#cbd5e1;'>Last contact: <b style='color:white;'>{_relative_date(p_last_contacted_at)}</b></div>", unsafe_allow_html=True)
    if p_next_followup_at:
        st.markdown(f"<div style='font-size:0.8125rem;color:#cbd5e1;'>Next follow-up: <b style='color:white;'>{p_next_followup_at[:10]}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.8125rem;color:#cbd5e1;'>Drafts saved: <b style='color:white;'>{len(email_drafts)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.8125rem;color:#cbd5e1;'>Timeline events: <b style='color:white;'>{len(outreach_timeline)}</b></div>", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────

st.page_link("pages/2_Outreach_CRM.py", label="← Outreach CRM")

st.markdown(
    f'<div class="page-title" style="margin-top:0.25rem;">{p_name}</div>',
    unsafe_allow_html=True,
)

# Badge row
location_str = f"{country_flag(p_country)} {p_city}, {p_country}" if p_city else country_flag(p_country)
badges_html = (
    f'{type_badge(p_inst_type)}&nbsp;&nbsp;'
    f'{status_badge(p_status)}&nbsp;&nbsp;'
    f'{tier_badge(p_rank)}&nbsp;&nbsp;'
    f'<span style="font-size:0.875rem;color:#64748b;">{location_str}</span>'
)
st.markdown(badges_html, unsafe_allow_html=True)

if p_research_updated_at:
    st.markdown(
        f'<div style="font-size:0.8125rem;color:#94a3b8;margin-top:0.3rem;">Last researched: {_relative_date(p_research_updated_at)}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_overview, tab_research, tab_dm, tab_emails, tab_timeline = st.tabs([
    "Overview",
    "Research",
    "Decision Maker",
    "Email Drafts",
    "Outreach Timeline",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════

with tab_overview:
    col_main, col_side = st.columns([2, 1], gap="large")

    # ── Left: scores, pills, briefs ──────────────────────────────────────────
    with col_main:
        st.markdown("### Scores")

        score_bd_str = _s("score_breakdown")
        score_bd: dict = {}
        if score_bd_str:
            for part in score_bd_str.split("|"):
                part = part.strip()
                if ":" in part:
                    k, rest = part.split(":", 1)
                    score_bd[k.strip().lower()] = rest.strip()

        def _reason(keys: list[str]) -> str:
            for k in keys:
                if k in score_bd:
                    return score_bd[k].split("—", 1)[-1].strip()
            return ""

        bars_html = (
            score_bar("Innovation", p_inno, _reason(["innovation"]))
            + score_bar("Accessibility", p_access, _reason(["access", "accessibility"]))
            + score_bar("Product Fit", p_fit, _reason(["fit"]))
            + score_bar("Startup Receptiveness", p_startup_rx, _reason(["startup_fit", "startup"]))
        )
        st.markdown(bars_html, unsafe_allow_html=True)

        # Composite score
        composite = p_inno + p_access + p_fit + p_startup_rx
        st.markdown(
            f'<div style="font-size:0.8125rem;color:#94a3b8;margin-top:0.35rem;">Composite: <b style="color:#475569;">{composite}/40</b></div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Info pills
        pills = []
        if p_emr and p_emr.lower() not in ("unknown", ""):
            pills.append(f'<span class="info-pill"><b>EMR:</b> {p_emr}</span>')
        if p_patient_vol:
            pills.append(f'<span class="info-pill"><b>Volume:</b> {p_patient_vol}</span>')
        if p_ai_tools and p_ai_tools.lower() not in ("none detected", "none", ""):
            pills.append(f'<span class="info-pill" style="background:#fde8e8;"><b>AI tools:</b> {p_ai_tools}</span>')
        if p_phone_evidence:
            pills.append(f'<span class="info-pill" style="background:#e8f4fd;"><b>Phone evidence:</b> "{p_phone_evidence}"</span>')
        if pills:
            st.markdown(" ".join(pills), unsafe_allow_html=True)
            st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

        # Outreach angle
        p_outreach_angle = _s("outreach_angle")
        if p_outreach_angle:
            st.markdown("**Outreach angle:**")
            st.code(p_outreach_angle, language=None)

        st.markdown("---")
        st.markdown("### Research Brief")

        if p_research_brief:
            st.markdown(
                f'<div class="outreach-box" style="max-height:300px;overflow-y:auto;">{p_research_brief}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="color:#94a3b8;font-size:0.9375rem;padding:0.75rem 0;">'
                'No research yet — run it in the <b>Research</b> tab.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("### Fit Analysis")

        if p_fit_analysis:
            st.markdown(
                f'<div class="outreach-box" style="max-height:240px;overflow-y:auto;">{p_fit_analysis}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="color:#94a3b8;font-size:0.9375rem;padding:0.75rem 0;">'
                'Run Research first — Fit Analysis will appear here once generated.</div>',
                unsafe_allow_html=True,
            )

    # ── Right: CRM controls ──────────────────────────────────────────────────
    with col_side:
        st.markdown("### Pipeline Controls")

        # Status selector
        try:
            status_idx = STATUS_ORDER.index(p_status)
        except ValueError:
            status_idx = 0

        new_status = st.selectbox(
            "Pipeline Status",
            STATUS_ORDER,
            index=status_idx,
            format_func=lambda s: STATUS_LABELS.get(s, s),
            key="pp_status",
        )
        if new_status != p_status:
            updates: dict = {"status": new_status}
            if new_status == "email_sent":
                updates["last_contacted_at"] = datetime.now(timezone.utc).isoformat()
                updates["outreach_count"] = p_outreach_count + 1
            update_prospect(prospect_id, updates)
            st.cache_data.clear()
            st.rerun()

        # Assigned to
        try:
            assign_idx = _team_member_names.index(p_assigned)
        except ValueError:
            assign_idx = 0

        new_assigned = st.selectbox(
            "Assigned to",
            _team_member_names,
            index=assign_idx,
            key="pp_assigned",
        )
        if new_assigned != p_assigned:
            update_prospect(prospect_id, {"assigned_to": new_assigned})
            st.cache_data.clear()
            st.rerun()

        # Next follow-up date
        followup_val = None
        if p_next_followup_at:
            try:
                followup_val = date.fromisoformat(p_next_followup_at[:10])
            except Exception:
                followup_val = None

        new_followup = st.date_input(
            "Next Follow-up Date",
            value=followup_val,
            key="pp_followup_date",
        )
        if st.button("Save Follow-up Date", key="pp_save_followup", use_container_width=True):
            iso = new_followup.isoformat() if new_followup else None
            update_prospect(prospect_id, {"next_followup_at": iso})
            st.success("Follow-up date saved.")
            st.cache_data.clear()

        st.markdown("---")

        # Response type
        response_opts = ["none", "no_response", "interested", "meeting_booked", "declined", "bounced"]
        response_labels = {
            "none": "No response logged",
            "no_response": "No Response",
            "interested": "Interested",
            "meeting_booked": "Meeting Booked",
            "declined": "Declined",
            "bounced": "Bounced",
        }
        try:
            resp_idx = response_opts.index(p_response_type)
        except ValueError:
            resp_idx = 0

        new_response = st.selectbox(
            "Response Type",
            response_opts,
            index=resp_idx,
            format_func=lambda s: response_labels.get(s, s),
            key="pp_response_type",
        )
        if new_response != p_response_type:
            update_prospect(prospect_id, {"response_type": new_response})
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        # Contact notes
        new_notes = st.text_area(
            "Contact Notes",
            value=p_contact_notes,
            height=130,
            key="pp_contact_notes",
            placeholder="e.g. Emailed on Apr 3. Director asked for a demo video...",
        )
        if st.button("Save Notes", key="pp_save_notes", use_container_width=True):
            update_prospect(prospect_id, {"contact_notes": new_notes})
            st.success("Notes saved.")
            st.cache_data.clear()

        st.markdown("---")

        # Quick links
        st.markdown("**Quick Links**")
        links = []
        if p_website:
            links.append(f"[Website]({p_website})")
        if p_phone:
            links.append(f"Phone: `{p_phone}`")
        if p_dm_linkedin:
            links.append(f"[LinkedIn]({p_dm_linkedin})")
        if links:
            st.markdown("  |  ".join(links))
        else:
            st.caption("No links saved yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RESEARCH
# ═══════════════════════════════════════════════════════════════════════════════

with tab_research:
    if not has_ai_configured():
        st.warning("AI is not configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your secrets to enable AI research.")

    # ── Institution Research ─────────────────────────────────────────────────
    st.markdown("## Institution Research")

    if p_research_brief:
        st.markdown(
            f'<div class="outreach-box" style="white-space:pre-wrap;">{p_research_brief}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Last updated: {_fmt_date(p_research_updated_at)}")
        run_research_label = "Re-run Institution Research"
    else:
        st.markdown(
            "Run AI-powered deep research on this institution. The research brief will summarize their structure, "
            "priorities, digital health maturity, and how MedPort maps to their needs."
        )
        run_research_label = "Run Institution Research"

    if st.button(run_research_label, key="pp_run_research", type="primary"):
        with st.spinner(f"Researching {p_name}..."):
            try:
                result = research_institution(prospect)
                save_prospect_research(prospect_id, research_brief=result)
                st.success("Research saved.")
                st.cache_data.clear()
                st.rerun()
            except Exception as exc:
                st.error(f"Research failed: {exc}")

    st.markdown("---")

    # ── Fit Analysis ─────────────────────────────────────────────────────────
    st.markdown("## Fit Analysis")

    if p_fit_analysis:
        st.markdown(
            f'<div class="outreach-box" style="white-space:pre-wrap;">{p_fit_analysis}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Last updated: {_fmt_date(p_research_updated_at)}")
        fit_btn_label = "Re-run Fit Analysis"
    else:
        st.markdown(
            "AI-powered fit analysis scores this prospect against MedPort's ideal customer profile, "
            "flags objections to anticipate, and suggests the sharpest outreach angle."
        )
        fit_btn_label = "Run Fit Analysis"

    if st.button(fit_btn_label, key="pp_run_fit", type="primary"):
        with st.spinner("Analyzing fit..."):
            try:
                result = analyze_fit(prospect, p_research_brief, p_dm_research)
                save_prospect_research(prospect_id, fit_analysis=result)
                st.success("Fit analysis saved.")
                st.cache_data.clear()
                st.rerun()
            except Exception as exc:
                st.error(f"Fit analysis failed: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — DECISION MAKER
# ═══════════════════════════════════════════════════════════════════════════════

with tab_dm:

    # ── Prominent research button ────────────────────────────────────────────
    dm_btn_label = "Re-run Decision Maker Research" if p_dm_research else "Find & Research Decision Maker"
    if not has_ai_configured():
        st.warning("AI not configured — set ANTHROPIC_API_KEY to enable DM research.")
    else:
        if st.button(
            f"🔎 {dm_btn_label}",
            key="pp_run_dm_research",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("Identifying and profiling decision maker..."):
                try:
                    result = research_decision_maker(prospect, institution_research=p_research_brief)
                    # Build DB update: autofill any fields that are currently blank
                    db_updates: dict = {}
                    if result.get("name") and not p_dm_name:
                        db_updates["decision_maker_name"] = result["name"]
                    if result.get("title") and not p_dm_title:
                        db_updates["decision_maker_title"] = result["title"]
                    if result.get("email") and not p_dm_email:
                        db_updates["decision_maker_email"] = result["email"]
                    if result.get("phone") and not p_dm_phone:
                        db_updates["decision_maker_phone"] = result["phone"]
                    if result.get("linkedin") and not p_dm_linkedin:
                        db_updates["decision_maker_linkedin"] = result["linkedin"]
                    if db_updates:
                        update_prospect(prospect_id, db_updates)
                    save_prospect_research(prospect_id, dm_research=result.get("brief", ""))
                    st.success("Decision maker identified and fields autofilled.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as exc:
                    st.error(f"DM research failed: {exc}")

    st.markdown("---")

    col_dm_form, col_dm_research = st.columns([1, 1], gap="large")

    # ── Left: edit DM details ────────────────────────────────────────────────
    with col_dm_form:
        st.markdown("### Decision Maker Details")

        dm_name_input = st.text_input("Full Name", value=p_dm_name, key="pp_dm_name")
        dm_title_input = st.text_input("Title / Role", value=p_dm_title, key="pp_dm_title")
        dm_email_input = st.text_input("Email", value=p_dm_email, key="pp_dm_email")
        dm_phone_input = st.text_input("Phone", value=p_dm_phone, key="pp_dm_phone")
        dm_linkedin_input = st.text_input("LinkedIn URL", value=p_dm_linkedin, key="pp_dm_linkedin")

        if st.button("Save Decision Maker", key="pp_save_dm", type="secondary", use_container_width=True):
            update_prospect(prospect_id, {
                "decision_maker_name": dm_name_input.strip(),
                "decision_maker_title": dm_title_input.strip(),
                "decision_maker_email": dm_email_input.strip(),
                "decision_maker_phone": dm_phone_input.strip(),
                "decision_maker_linkedin": dm_linkedin_input.strip(),
            })
            st.success("Saved.")
            st.cache_data.clear()

        if dm_name_input or p_dm_name:
            display_name = dm_name_input or p_dm_name
            display_title = dm_title_input or p_dm_title
            st.markdown("---")
            st.markdown("**Current DM:**")
            st.markdown(
                f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid {MEDPORT_TEAL};'
                f'border-radius:8px;padding:0.75rem 1rem;">'
                f'<div style="font-weight:700;font-size:1rem;color:{MEDPORT_DARK};">{display_name}</div>'
                f'<div style="font-size:0.875rem;color:#64748b;">{display_title}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Right: DM research brief ─────────────────────────────────────────────
    with col_dm_research:
        st.markdown("### Research Brief")

        if p_dm_research:
            st.markdown(
                f'<div class="outreach-box" style="white-space:pre-wrap;">{p_dm_research}</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"Last updated: {_fmt_date(p_research_updated_at)}")
        else:
            st.info("Click **Find & Research Decision Maker** above to identify the right contact and get a brief.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — EMAIL DRAFTS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_emails:

    # ── Generate new draft ───────────────────────────────────────────────────
    st.markdown("## Generate New Draft")

    if not has_ai_configured():
        st.warning("AI not configured. Set your API key to generate email drafts.")

    gen_col1, gen_col2 = st.columns(2)
    with gen_col1:
        sender_name = st.text_input("Sender Name", value="Ahan", key="pp_sender_name")
    with gen_col2:
        sender_title = st.text_input("Sender Title", value="CMO & Co-Founder, MedPort", key="pp_sender_title")

    variant_labels = {
        1: "Variant 1: Direct value prop",
        2: "Variant 2: Problem-first hook",
        3: "Variant 3: Research-based personalization",
    }
    variant_choice = st.radio(
        "Email Variant",
        options=[1, 2, 3],
        format_func=lambda v: variant_labels[v],
        horizontal=True,
        key="pp_email_variant",
    )

    if st.button("Generate Email", key="pp_generate_email", type="primary"):
        with st.spinner("Drafting email..."):
            try:
                subject, body = draft_outreach_email(
                    prospect,
                    p_research_brief,
                    p_dm_research,
                    p_fit_analysis,
                    sender_name=sender_name,
                    sender_title=sender_title,
                    variant=variant_choice,
                )
                st.session_state["pp_draft_subject"] = subject
                st.session_state["pp_draft_body"] = body
                st.session_state["pp_draft_variant"] = variant_choice
            except Exception as exc:
                st.error(f"Email generation failed: {exc}")

    # Preview generated draft
    if "pp_draft_subject" in st.session_state and st.session_state["pp_draft_subject"]:
        draft_subject = st.session_state["pp_draft_subject"]
        draft_body = st.session_state["pp_draft_body"]
        draft_variant = st.session_state.get("pp_draft_variant", 1)

        st.markdown("**Preview:**")
        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid {MEDPORT_BLUE};'
            f'border-radius:10px;padding:1rem 1.25rem;">'
            f'<div style="font-size:0.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;font-weight:600;margin-bottom:0.4rem;">Subject</div>'
            f'<div style="font-weight:700;font-size:1rem;color:{MEDPORT_DARK};margin-bottom:0.75rem;">{draft_subject}</div>'
            f'<div style="font-size:0.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;font-weight:600;margin-bottom:0.4rem;">Body</div>'
            f'<div style="white-space:pre-wrap;font-size:0.9375rem;color:#334155;line-height:1.6;">{draft_body}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.button("Save This Draft", key="pp_save_draft", type="primary"):
            success = add_email_draft(
                prospect_id,
                subject=draft_subject,
                body=draft_body,
                variant=draft_variant,
            )
            if success:
                st.success("Draft saved.")
                # Clear preview
                del st.session_state["pp_draft_subject"]
                del st.session_state["pp_draft_body"]
                st.cache_data.clear()
                st.rerun()

    # ── Saved drafts ─────────────────────────────────────────────────────────
    if email_drafts:
        st.markdown("---")
        st.markdown("## Saved Drafts")
        st.caption(f"{len(email_drafts)} draft{'s' if len(email_drafts) != 1 else ''} saved")

        for i, draft in enumerate(reversed(email_drafts)):
            draft_id = draft.get("id", str(i))
            d_subject = draft.get("subject", "No subject")
            d_body = draft.get("body", "")
            d_variant = draft.get("variant", 1)
            d_created = draft.get("created_at", "")

            with st.container():
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:1rem 1.25rem;margin-bottom:0.75rem;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem;">'
                    f'<div>'
                    f'<span style="background:#eff6ff;color:#1e40af;padding:2px 9px;border-radius:6px;font-size:0.75rem;font-weight:600;">Variant {d_variant}</span>'
                    f'&nbsp;<span style="font-size:0.8125rem;color:#94a3b8;">{_relative_date(d_created)}</span>'
                    f'</div>'
                    f'</div>'
                    f'<div style="font-weight:700;font-size:0.9375rem;color:{MEDPORT_DARK};margin-bottom:0.5rem;">{d_subject}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                dc1, dc2, dc3 = st.columns([2, 2, 2])
                with dc1:
                    # Subject copy field
                    with st.expander("Copy subject", expanded=False):
                        st.text_input(
                            "Subject line",
                            value=d_subject,
                            key=f"pp_subj_copy_{draft_id}",
                            label_visibility="collapsed",
                        )
                with dc2:
                    with st.expander("View / copy body", expanded=False):
                        st.text_area(
                            "Email body",
                            value=d_body,
                            height=200,
                            key=f"pp_body_copy_{draft_id}",
                            label_visibility="collapsed",
                        )
                with dc3:
                    if st.button(
                        "Use as Follow-up Base",
                        key=f"pp_followup_base_{draft_id}",
                        use_container_width=True,
                    ):
                        st.session_state["pp_followup_orig_subject"] = d_subject
                        st.toast("Subject loaded into Follow-up section below.")

    # ── Generate Follow-up ───────────────────────────────────────────────────
    if email_drafts or outreach_timeline:
        st.markdown("---")
        st.markdown("## Generate Follow-up")

        # Auto-fill subject from most recent draft or session state
        default_subject = ""
        if "pp_followup_orig_subject" in st.session_state:
            default_subject = st.session_state["pp_followup_orig_subject"]
        elif email_drafts:
            default_subject = email_drafts[-1].get("subject", "")

        fu_subject = st.text_input(
            "Subject of original email",
            value=default_subject,
            key="pp_followup_subject",
        )

        # Auto-calculate days since
        default_days = 7
        if p_last_contacted_at:
            try:
                last = datetime.fromisoformat(p_last_contacted_at.replace("Z", "+00:00"))
                default_days = max(1, (datetime.now(timezone.utc) - last).days)
            except Exception:
                default_days = 7

        fu_days = st.number_input(
            "Days since original email",
            min_value=1,
            max_value=90,
            value=default_days,
            key="pp_followup_days",
        )

        fu_outcome = st.selectbox(
            "Situation / Outcome",
            options=["no_response", "opened", "interested", "asked_for_info", "bounced"],
            format_func=lambda s: {
                "no_response": "No response",
                "opened": "Opened but no reply",
                "interested": "Showed interest, no commit",
                "asked_for_info": "Asked for more info",
                "bounced": "Email bounced",
            }.get(s, s),
            key="pp_followup_outcome",
        )

        if st.button("Generate Follow-up Email", key="pp_gen_followup", type="primary"):
            with st.spinner("Drafting follow-up..."):
                try:
                    fu_subj, fu_body = draft_followup_email(
                        prospect,
                        original_subject=fu_subject,
                        days_since=int(fu_days),
                        outcome=fu_outcome,
                        sender_name=st.session_state.get("pp_sender_name", "Ahan"),
                    )
                    st.session_state["pp_fu_subject"] = fu_subj
                    st.session_state["pp_fu_body"] = fu_body
                except Exception as exc:
                    st.error(f"Follow-up generation failed: {exc}")

        if "pp_fu_subject" in st.session_state:
            fu_s = st.session_state["pp_fu_subject"]
            fu_b = st.session_state["pp_fu_body"]
            st.markdown("**Follow-up Preview:**")
            st.markdown(
                f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid {MEDPORT_TEAL};'
                f'border-radius:10px;padding:1rem 1.25rem;">'
                f'<div style="font-weight:700;font-size:0.9375rem;color:{MEDPORT_DARK};margin-bottom:0.5rem;">{fu_s}</div>'
                f'<div style="white-space:pre-wrap;font-size:0.9375rem;color:#334155;line-height:1.6;">{fu_b}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Save Follow-up Draft", key="pp_save_fu", type="primary"):
                add_email_draft(prospect_id, subject=fu_s, body=fu_b, variant=0)
                st.success("Follow-up draft saved.")
                del st.session_state["pp_fu_subject"]
                del st.session_state["pp_fu_body"]
                st.cache_data.clear()
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — OUTREACH TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════

with tab_timeline:

    # ── Log new event ────────────────────────────────────────────────────────
    with st.expander("Log New Outreach Event", expanded=not outreach_timeline):
        ev_type = st.selectbox(
            "Event Type",
            options=["email_sent", "follow_up_sent", "call_made", "meeting_held", "email_opened", "responded", "demo_given"],
            format_func=event_type_label,
            key="pp_ev_type",
        )
        ev_subject = st.text_input(
            "Subject / Topic",
            placeholder="e.g. Cold outreach — patient intake automation",
            key="pp_ev_subject",
        )
        ev_notes = st.text_area(
            "Notes",
            height=80,
            placeholder="Details about the touchpoint...",
            key="pp_ev_notes",
        )
        ev_outcome = st.text_input(
            "Outcome",
            placeholder="e.g. Interested, asked for a deck. No response after 5 days.",
            key="pp_ev_outcome",
        )

        if st.button("Log Event", key="pp_log_event", type="primary"):
            if not ev_subject.strip() and not ev_notes.strip():
                st.warning("Add a subject or notes before logging.")
            else:
                ok = log_outreach_event(
                    prospect_id=prospect_id,
                    event_type=ev_type,
                    subject=ev_subject.strip(),
                    notes=ev_notes.strip(),
                    outcome=ev_outcome.strip(),
                    logged_by=name,
                )
                if ok:
                    # Auto-update status when email is sent
                    if ev_type in ("email_sent", "follow_up_sent") and p_status == "not_contacted":
                        update_prospect(prospect_id, {"status": "email_sent"})
                    st.success("Event logged.")
                    st.cache_data.clear()
                    st.rerun()

    st.markdown("---")

    # ── Timeline display ─────────────────────────────────────────────────────
    if outreach_timeline:
        st.markdown(f"## Timeline &nbsp; <span style='font-size:0.875rem;color:#94a3b8;font-weight:400;'>{len(outreach_timeline)} events</span>", unsafe_allow_html=True)

        # Reverse-chrono
        for event in reversed(outreach_timeline):
            ev_date = event.get("date", "")
            ev_t = event.get("type", "")
            ev_subj = event.get("subject", "")
            ev_n = event.get("notes", "")
            ev_out = event.get("outcome", "")
            ev_by = event.get("logged_by", "")
            ev_color = event_type_color(ev_t)
            ev_label = event_type_label(ev_t)

            _by_html = f'<span style="font-size:0.8125rem;color:#94a3b8;"> · by {ev_by}</span>' if ev_by else ""
            _subj_html = f'<div style="font-weight:600;font-size:0.9375rem;color:#1e293b;margin-bottom:0.2rem;">{ev_subj}</div>' if ev_subj else ""
            _notes_html = f'<div style="font-size:0.875rem;color:#475569;">{ev_n}</div>' if ev_n else ""
            _out_html = f'<div style="font-size:0.8125rem;color:#64748b;margin-top:0.2rem;"><b>Outcome:</b> {ev_out}</div>' if ev_out else ""
            st.markdown(
                f'<div class="activity-item" style="border-left:3px solid {ev_color};">'
                f'<div style="flex:1;">'
                f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">'
                f'<span style="background:{ev_color};color:#fff;padding:2px 9px;border-radius:6px;font-size:0.75rem;font-weight:600;">{ev_label}</span>'
                f'<span style="font-size:0.8125rem;color:#94a3b8;">{_relative_date(ev_date)}</span>'
                f'{_by_html}'
                f'</div>'
                f'{_subj_html}'
                f'{_notes_html}'
                f'{_out_html}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        # Stats row
        tl1, tl2 = st.columns(2)
        with tl1:
            st.markdown(
                f'<div class="stat-card" style="padding:1rem 1.25rem;">'
                f'<div class="stat-value">{p_outreach_count}</div>'
                f'<div class="stat-label">Total Outreach</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with tl2:
            last_label = _relative_date(p_last_contacted_at) if p_last_contacted_at else "Never"
            st.markdown(
                f'<div class="stat-card" style="padding:1rem 1.25rem;">'
                f'<div class="stat-value" style="font-size:1.5rem;">{last_label}</div>'
                f'<div class="stat-label">Last Contacted</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    else:
        st.markdown(
            '<div style="padding:3rem 0;text-align:center;color:#94a3b8;">'
            '<div style="font-size:2rem;margin-bottom:0.5rem;">📭</div>'
            '<div style="font-size:1rem;font-weight:600;margin-bottom:0.4rem;">No outreach logged yet</div>'
            '<div style="font-size:0.875rem;">Start by sending your first email, then log it above.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
