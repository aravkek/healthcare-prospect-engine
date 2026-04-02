"""
MedPort Prospect Dashboard — Team CRM
=======================================
Streamlit dashboard that reads from Supabase (falls back to local CSV).
Provides full CRM: status tracking, assignments, notes, score breakdown,
and an outreach queue that auto-replenishes as the team works through prospects.

Deploy to Streamlit Community Cloud via GitHub repo.
Requires Streamlit >= 1.37.0 for built-in Google OAuth.
"""

import os
import subprocess
import time
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def _secret(key: str, default: str = "") -> str:
    """Read from env first, then st.secrets if available, else return default."""
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

# ─────────────────────────────────────────────
# Page config — must be first Streamlit call
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="MedPort Prospect CRM",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Auth — Google OAuth via Streamlit built-in
# ─────────────────────────────────────────────

LOCAL_DEV = os.environ.get("LOCAL_DEV", "false").lower() == "true"
try:
    _auth_configured = bool(st.secrets.get("auth", {}))
except Exception:
    _auth_configured = False

if not LOCAL_DEV and _auth_configured:
    try:
        _is_logged_in = st.experimental_user.is_logged_in
    except AttributeError:
        _is_logged_in = False

    if not _is_logged_in:
        st.title("MedPort Prospect CRM")
        st.markdown("Sign in with your MedPort Google account to access the prospect database.")
        if st.button("Sign in with Google", type="primary"):
            st.login()
        st.stop()
    else:
        _allowed_raw = _secret("ALLOWED_EMAILS", "")
        if _allowed_raw:
            _allowed = [e.strip().lower() for e in _allowed_raw.split(",") if e.strip()]
            try:
                _user_email = (st.experimental_user.email or "").lower()
            except AttributeError:
                _user_email = ""
            if _user_email not in _allowed:
                st.error(f"Access denied. {_user_email} is not on the MedPort team list.")
                st.info("Contact Arav to request access.")
                if st.button("Sign out"):
                    st.logout()
                st.stop()

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

MEDPORT_BLUE = "#1B4F72"

# Status pipeline — in order of progression
STATUS_ORDER = [
    "not_contacted",
    "email_sent",
    "pending_response",
    "demo_booked",
    "converted",
    "declined",
]

STATUS_LABELS = {
    "not_contacted": "Not Contacted",
    "email_sent": "Email Sent",
    "pending_response": "Pending Response",
    "demo_booked": "Demo Booked",
    "converted": "Converted",
    "declined": "Declined",
}

STATUS_COLORS = {
    "not_contacted": "#8e9db4",
    "email_sent": "#2980b9",
    "pending_response": "#f39c12",
    "demo_booked": "#8e44ad",
    "converted": "#1a8a4a",
    "declined": "#c0392b",
}

# Forward pipeline stages (not declined)
PIPELINE_STAGES = ["not_contacted", "email_sent", "pending_response", "demo_booked", "converted"]

TEAM_MEMBERS = ["Unassigned", "Arav", "CFO", "Team Member 3", "Team Member 4", "Team Member 5"]

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────

st.markdown(f"""
<style>
  .main .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; }}
  h1 {{ color: {MEDPORT_BLUE}; font-weight: 800; letter-spacing: -0.5px; }}
  h2, h3 {{ color: {MEDPORT_BLUE}; }}

  .stat-card {{
    background: #fff;
    border: 1px solid #e0e7ef;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(27,79,114,0.07);
  }}
  .stat-card .stat-value {{ font-size: 2rem; font-weight: 800; color: {MEDPORT_BLUE}; line-height: 1; }}
  .stat-card .stat-label {{ font-size: 0.75rem; color: #6b7a8d; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.3rem; }}

  .funnel-row {{ display: flex; gap: 0; flex-wrap: nowrap; margin-bottom: 1rem; overflow-x: auto; }}
  .funnel-step {{
    flex: 1; min-width: 90px; padding: 0.55rem 0.4rem;
    text-align: center; font-size: 0.75rem; font-weight: 600; color: #fff;
    position: relative;
  }}
  .funnel-step .funnel-count {{ font-size: 1.4rem; font-weight: 800; display: block; line-height: 1; }}
  .funnel-step .funnel-label {{ font-size: 0.7rem; opacity: 0.9; margin-top: 2px; display: block; }}
  .funnel-step:not(:last-child)::after {{
    content: '›'; position: absolute; right: -6px; top: 50%; transform: translateY(-50%);
    font-size: 1.2rem; color: rgba(255,255,255,0.6); z-index: 10;
  }}
  .funnel-step:first-child {{ border-radius: 8px 0 0 8px; }}
  .funnel-step:last-child {{ border-radius: 0 8px 8px 0; }}

  .queue-badge {{
    background: #fff3cd; color: #856404;
    border: 1px solid #ffc107;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.8rem; font-weight: 700; display: inline-block;
  }}

  .score-bar-container {{ margin: 2px 0; }}
  .score-bar-label {{ font-size: 0.7rem; color: #6b7a8d; display: inline-block; width: 80px; }}
  .score-bar-outer {{ display: inline-block; width: 80px; height: 8px; background: #e8eef4; border-radius: 4px; vertical-align: middle; }}
  .score-bar-inner {{ height: 8px; border-radius: 4px; }}
  .score-bar-val {{ font-size: 0.72rem; font-weight: 700; margin-left: 4px; display: inline-block; }}

  .inst-header {{ font-size: 1.05rem; font-weight: 700; color: #1a2a3a; }}
  .inst-meta {{ font-size: 0.8rem; color: #5a6a7a; margin-top: 0.15rem; }}

  .score-green  {{ background:#d4edda; color:#155724; padding:2px 8px; border-radius:20px; font-weight:700; font-size:0.82rem; }}
  .score-yellow {{ background:#fff3cd; color:#856404; padding:2px 8px; border-radius:20px; font-weight:700; font-size:0.82rem; }}
  .score-red    {{ background:#f8d7da; color:#721c24; padding:2px 8px; border-radius:20px; font-weight:700; font-size:0.82rem; }}

  .risk-none   {{ background:#d4edda; color:#155724; padding:2px 8px; border-radius:20px; font-size:0.75rem; font-weight:600; }}
  .risk-low    {{ background:#d1ecf1; color:#0c5460; padding:2px 8px; border-radius:20px; font-size:0.75rem; font-weight:600; }}
  .risk-medium {{ background:#fff3cd; color:#856404; padding:2px 8px; border-radius:20px; font-size:0.75rem; font-weight:600; }}
  .risk-high   {{ background:#f8d7da; color:#721c24; padding:2px 8px; border-radius:20px; font-size:0.75rem; font-weight:600; }}

  .type-badge {{
    background: {MEDPORT_BLUE}18; color: {MEDPORT_BLUE};
    padding: 2px 8px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
  }}
  .tier-a {{ background:#1B4F72; color:#fff; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:700; }}
  .tier-b {{ background:#2980b9; color:#fff; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:700; }}
  .tier-c {{ background:#aab4bf; color:#fff; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:700; }}

  .status-badge {{ display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; color:#fff; }}

  .outreach-box {{
    background: #eaf4fb; border-left: 3px solid #2980b9;
    border-radius: 6px; padding: 0.6rem 0.9rem;
    font-size: 0.88rem; color: #1a3a52; margin-top: 0.4rem;
  }}
  .info-pill {{
    background: #f0f4f8; color: #3a4a5a;
    border-radius: 6px; padding: 4px 10px; font-size: 0.78rem;
    display: inline-block; margin: 2px 4px 2px 0;
  }}
  .info-pill b {{ color: {MEDPORT_BLUE}; }}

  .alert-box {{
    background: #fff9e6; border-left: 4px solid #f39c12;
    border-radius: 8px; padding: 0.8rem 1rem;
    font-size: 0.88rem; color: #5d4037;
  }}

  hr.subtle {{ border: none; border-top: 1px solid #e8eef4; margin: 0.5rem 0; }}
  section[data-testid="stSidebar"] {{ background: #f0f5fa; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Data layer
# ─────────────────────────────────────────────

CSV_PATH = os.path.join(os.path.dirname(__file__), "medport_prospects.csv")


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    int_cols = ["innovation_score", "accessibility_score", "fit_score",
                "startup_receptiveness", "priority_rank", "outreach_count"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    str_cols = ["competitor_risk", "emr_system", "patient_volume", "existing_ai_tools",
                "phone_intake_evidence", "score_breakdown", "contact_notes",
                "research_notes", "outreach_angle"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna("")
        else:
            df[col] = ""

    if "country" in df.columns:
        df["country"] = df["country"].fillna("").str.upper()
    if "inst_type" in df.columns:
        df["inst_type"] = df["inst_type"].fillna("unknown")
    if "competitor_risk" in df.columns:
        df["competitor_risk"] = df["competitor_risk"].fillna("none")

    # Composite score — 4 dimensions now (40-point max)
    df["composite_score"] = (
        df.get("innovation_score", pd.Series(0, index=df.index)).fillna(0).astype(int)
        + df.get("accessibility_score", pd.Series(0, index=df.index)).fillna(0).astype(int)
        + df.get("fit_score", pd.Series(0, index=df.index)).fillna(0).astype(int)
        + df.get("startup_receptiveness", pd.Series(0, index=df.index)).fillna(0).astype(int)
    )

    if "status" not in df.columns:
        df["status"] = "not_contacted"
    else:
        # Migrate old status values to new names
        status_map = {"contacted": "email_sent", "responded": "pending_response",
                      "meeting_booked": "demo_booked"}
        df["status"] = df["status"].fillna("not_contacted").replace(status_map)

    if "assigned_to" not in df.columns:
        df["assigned_to"] = "Unassigned"
    else:
        df["assigned_to"] = df["assigned_to"].fillna("Unassigned")

    if "id" not in df.columns:
        df["id"] = df.index.astype(str)

    return df


def _load_csv_fallback() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame()
    return _normalize_df(pd.read_csv(CSV_PATH))


@st.cache_data(ttl=30)
def load_from_supabase() -> pd.DataFrame:
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return _load_csv_fallback()
    try:
        from supabase import create_client
        client = create_client(url, key)
        result = (
            client.table("prospects")
            .select("*")
            .order("priority_rank")
            .order("composite_score", desc=True)
            .execute()
        )
        if not result.data:
            return _load_csv_fallback()
        return _normalize_df(pd.DataFrame(result.data))
    except Exception as e:
        st.warning(f"Supabase load failed, falling back to CSV: {e}")
        return _load_csv_fallback()


def update_prospect_crm(prospect_id: str, updates: dict):
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return
    try:
        from supabase import create_client
        client = create_client(url, key)
        client.table("prospects").update(updates).eq("id", prospect_id).execute()
    except Exception as e:
        st.error(f"Failed to save update: {e}")


# ─────────────────────────────────────────────
# Badge + visual helpers
# ─────────────────────────────────────────────

def score_badge(score: int) -> str:
    score = int(score) if score else 0
    if score >= 8:
        return f'<span class="score-green">{score}/10</span>'
    elif score >= 5:
        return f'<span class="score-yellow">{score}/10</span>'
    else:
        return f'<span class="score-red">{score}/10</span>'


def score_bar(label: str, score: int, reason: str = "") -> str:
    score = max(0, min(10, int(score) if score else 0))
    pct = score * 10
    if score >= 8:
        color = "#27ae60"
    elif score >= 5:
        color = "#f39c12"
    else:
        color = "#e74c3c"
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
    """Parse 'fit: 8/10 — reason | innovation: 6/10 — reason | ...' into dict."""
    result = {}
    if not breakdown_str:
        return result
    for part in breakdown_str.split("|"):
        part = part.strip()
        if ":" in part:
            key, rest = part.split(":", 1)
            key = key.strip().lower()
            result[key] = rest.strip()
    return result


# ─────────────────────────────────────────────
# Institution card renderer
# ─────────────────────────────────────────────

def render_institution_card(row: pd.Series, queue_mode: bool = False):
    name = row.get("name", "Unknown")
    city = row.get("city", "")
    country = row.get("country", "")
    inst_type = row.get("inst_type", "")
    website = row.get("website", "")
    phone = row.get("phone", "")
    dm_name = row.get("decision_maker_name", "")
    dm_title = row.get("decision_maker_title", "")
    dm_linkedin = row.get("decision_maker_linkedin", "")
    outreach = row.get("outreach_angle", "")
    notes = row.get("research_notes", "")
    risk = row.get("competitor_risk", "none")
    rank = row.get("priority_rank", 3)
    inno = int(row.get("innovation_score", 0) or 0)
    access = int(row.get("accessibility_score", 0) or 0)
    fit = int(row.get("fit_score", 0) or 0)
    startup_rx = int(row.get("startup_receptiveness", 0) or 0)
    emr = row.get("emr_system", "")
    patient_vol = row.get("patient_volume", "")
    ai_tools = row.get("existing_ai_tools", "")
    phone_evidence = row.get("phone_intake_evidence", "")
    score_bd_str = row.get("score_breakdown", "")
    current_status = row.get("status", "not_contacted")
    current_assigned = row.get("assigned_to", "Unassigned") or "Unassigned"
    current_notes = row.get("contact_notes", "") or ""
    prospect_id = str(row.get("id", ""))
    outreach_count = int(row.get("outreach_count", 0) or 0)

    location = f"{country_flag(country)} {city}, {country}" if city else country_flag(country)
    border_color = STATUS_COLORS.get(current_status, MEDPORT_BLUE)
    status_label = STATUS_LABELS.get(current_status, current_status)
    composite = inno + access + fit + startup_rx

    expander_label = f"{name}  —  {city}, {country}  [{status_label}]"
    if queue_mode:
        expander_label = f"📧 {name}  —  {city}, {country}"

    with st.expander(expander_label, expanded=queue_mode):
        st.markdown(
            f'<div style="border-left:4px solid {border_color};padding-left:0.7rem;">',
            unsafe_allow_html=True,
        )

        # ── Header ──
        col_title, col_tier = st.columns([5, 1])
        with col_title:
            st.markdown(
                f'<div class="inst-header">{location} &nbsp; {name}</div>'
                f'<div class="inst-meta">'
                f'{type_badge(inst_type)} &nbsp; {status_badge(current_status)} &nbsp; {risk_badge(risk)}'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_tier:
            st.markdown(
                f'<div style="text-align:right;margin-top:4px;">'
                f'{tier_badge(rank)}<br>'
                f'<span style="font-size:0.72rem;color:#6b7a8d;">{composite}/40</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="subtle">', unsafe_allow_html=True)

        # ── Score bars ──
        score_bd = _parse_score_breakdown(score_bd_str)
        fit_reason = score_bd.get("fit", "").split("—", 1)[-1].strip() if "fit" in score_bd else ""
        inno_reason = score_bd.get("innovation", "").split("—", 1)[-1].strip() if "innovation" in score_bd else ""
        access_reason = score_bd.get("access", score_bd.get("accessibility", "")).split("—", 1)[-1].strip() if ("access" in score_bd or "accessibility" in score_bd) else ""
        startup_reason = score_bd.get("startup_fit", score_bd.get("startup", "")).split("—", 1)[-1].strip() if ("startup_fit" in score_bd or "startup" in score_bd) else ""

        bar_html = (
            score_bar("Phone Fit", fit, fit_reason)
            + score_bar("Innovation", inno, inno_reason)
            + score_bar("Accessibility", access, access_reason)
            + score_bar("Startup Fit", startup_rx, startup_reason)
        )
        st.markdown(bar_html, unsafe_allow_html=True)

        # ── Info pills ──
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

        # ── Decision maker ──
        dm_parts = []
        if dm_name:
            dm_parts.append(f"**{dm_name}**")
        if dm_title:
            dm_parts.append(dm_title)
        if dm_parts:
            st.markdown("**Decision maker:** " + " — ".join(dm_parts))
        if dm_linkedin:
            st.markdown(f"**LinkedIn search:** `{dm_linkedin}`")

        # ── Outreach angle ──
        if outreach:
            st.markdown("**Outreach angle** (click to copy):")
            st.code(outreach, language=None)

        # ── Research notes ──
        if notes:
            with st.expander("Research notes", expanded=False):
                st.markdown(notes)

        # ── Score breakdown detail ──
        if score_bd_str and score_bd_str not in ("-", ""):
            with st.expander("Score breakdown details", expanded=False):
                st.markdown(f"```\n{score_bd_str}\n```")

        # ── Links ──
        link_parts = []
        if website:
            link_parts.append(f"[Website]({website})")
        if phone:
            link_parts.append(f"Phone: `{phone}`")
        if link_parts:
            st.markdown(" &nbsp; | &nbsp; ".join(link_parts), unsafe_allow_html=True)

        st.markdown('<hr class="subtle">', unsafe_allow_html=True)

        # ── CRM controls ──
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
                key=f"status_{prospect_id}",
            )
            if new_status != current_status:
                update_prospect_crm(
                    prospect_id,
                    {
                        "status": new_status,
                        "last_contacted_at": datetime.utcnow().isoformat(),
                        "outreach_count": outreach_count + (1 if new_status == "email_sent" else 0),
                    },
                )
                st.cache_data.clear()
                st.rerun()

        with crm2:
            try:
                assign_idx = TEAM_MEMBERS.index(current_assigned)
            except ValueError:
                assign_idx = 0
            new_assigned = st.selectbox(
                "Assigned to",
                TEAM_MEMBERS,
                index=assign_idx,
                key=f"assign_{prospect_id}",
            )
            if new_assigned != current_assigned:
                update_prospect_crm(prospect_id, {"assigned_to": new_assigned})
                st.cache_data.clear()
                st.rerun()

        new_notes = st.text_area(
            "Contact notes",
            value=current_notes,
            height=75,
            key=f"notes_{prospect_id}",
            placeholder="e.g. Emailed director on Apr 3. She asked for a demo video...",
        )
        if st.button("Save notes", key=f"save_{prospect_id}"):
            update_prospect_crm(prospect_id, {"contact_notes": new_notes})
            st.success("Saved.")
            st.cache_data.clear()

        if outreach_count > 0:
            st.caption(f"Outreach sent {outreach_count}x")

        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

# Default user identity (overwritten inside sidebar if auth available)
user_name = "Team Member"
user_email = ""

with st.sidebar:
    try:
        user_name = getattr(st.experimental_user, "name", "") or "Team Member"
        user_email = getattr(st.experimental_user, "email", "") or ""
    except AttributeError:
        user_name = "Team Member"
        user_email = ""

    st.markdown(f"## MedPort CRM")
    st.markdown(
        f"<span style='color:{MEDPORT_BLUE};font-size:0.82rem;'>Prospect Intelligence</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<span style='font-size:0.76rem;color:#6b7a8d;'>👤 {user_name}</span>", unsafe_allow_html=True)
    if _auth_configured and not LOCAL_DEV:
        if st.button("Sign out", use_container_width=False):
            st.logout()

    st.markdown("---")
    auto_refresh = st.toggle("Auto-refresh (30s)", value=False)
    st.markdown("### Filters")

    my_only = st.toggle("My Prospects only", value=False)
    country_opt = st.radio("Market", ["Both", "US", "CA"], horizontal=True)

    _df_all = load_from_supabase()
    has_data = len(_df_all) > 0

    if has_data and "inst_type" in _df_all.columns:
        all_types = sorted(_df_all["inst_type"].unique().tolist())
    else:
        all_types = ["CHC", "FQHC", "hospital", "university", "walk-in", "specialty"]
    selected_types = st.multiselect("Institution Type", all_types, default=all_types)

    selected_tiers = st.multiselect("Tier", ["A", "B", "C"], default=["A", "B"])
    selected_statuses = st.multiselect(
        "Status",
        STATUS_ORDER,
        default=STATUS_ORDER,
        format_func=lambda s: STATUS_LABELS.get(s, s),
    )
    selected_assignee = st.selectbox("Assigned to", ["All"] + TEAM_MEMBERS)
    min_score = st.slider("Min Score (out of 40)", 0, 40, 0, 1)

    st.markdown("---")
    st.markdown("### Actions")

    if st.button("Refresh Data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

    if st.button("Run Scraper + Sync", use_container_width=True):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cmd = ["python3", os.path.join(script_dir, "customer_discovery.py"),
               "--country", "both", "--resume", "--supabase", "--output", CSV_PATH]
        with st.spinner("Running... (~45 min for full run, check terminal for progress)"):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
                if result.returncode == 0:
                    st.success("Done.")
                else:
                    st.error("Errors — see below")
                    st.text_area("stderr", result.stderr[-2000:], height=150)
            except subprocess.TimeoutExpired:
                st.warning("Still running in background — check terminal.")
            except Exception as e:
                st.error(str(e))
        st.cache_data.clear()
        st.rerun()

    if has_data and os.path.exists(CSV_PATH):
        with open(CSV_PATH, "rb") as f:
            st.download_button("Download CSV", f, "medport_prospects.csv", "text/csv", use_container_width=True)


# ─────────────────────────────────────────────
# Auto-refresh
# ─────────────────────────────────────────────

if auto_refresh:
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()


# ─────────────────────────────────────────────
# PostHog analytics
# ─────────────────────────────────────────────

POSTHOG_KEY = _secret("POSTHOG_API_KEY")
if POSTHOG_KEY:
    components.html(f"""
    <script>
    !function(t,e){{var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){{function g(t,e){{var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){{t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){{var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e}},u.people.toString=function(){{return u.toString(1)+".people (stub)"}},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])}}e.__SV=1}}(document,window.posthog||[]);
    posthog.init('{POSTHOG_KEY}', {{api_host:'https://app.posthog.com'}});
    posthog.identify('{user_email}');
    posthog.capture('crm_viewed');
    </script>
    """, height=0)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

st.markdown("# MedPort Prospect CRM")

df = load_from_supabase()

if df.empty:
    st.info("No data yet. Click **Run Scraper + Sync** in the sidebar.")
    st.stop()

# ── Apply filters ──
filtered = df.copy()
if my_only:
    filtered = filtered[filtered["assigned_to"] == user_name]
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

# ── Pipeline funnel (full dataset, not filtered) ──
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
# Declined separately
declined = len(df[df["status"] == "declined"])
funnel_html += (
    f'<div class="funnel-step" style="background:{STATUS_COLORS["declined"]};min-width:70px;flex:0.6;">'
    f'<span class="funnel-count">{declined}</span>'
    f'<span class="funnel-label">Declined</span>'
    f'</div>'
)
funnel_html += "</div>"
st.markdown(funnel_html, unsafe_allow_html=True)

# ── Stats row ──
total = len(filtered)
tier_a = len(filtered[filtered["priority_rank"] == 1])
us_count = len(filtered[filtered["country"] == "US"])
ca_count = len(filtered[filtered["country"] == "CA"])
avg_score = round(filtered["composite_score"].mean(), 1) if total > 0 else 0.0
converted = len(df[df["status"] == "converted"])
uncontacted_a = len(df[(df["priority_rank"] == 1) & (df["status"] == "not_contacted")])

c1, c2, c3, c4, c5, c6 = st.columns(6)
for col, value, label in [
    (c1, total, "Showing"),
    (c2, tier_a, "Tier A"),
    (c3, f"{us_count} / {ca_count}", "US / CA"),
    (c4, f"{avg_score}/40", "Avg Score"),
    (c5, converted, "Converted"),
    (c6, uncontacted_a, "Tier A Queue"),
]:
    with col:
        st.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-value">{value}</div>'
            f'<div class="stat-label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")

# ── Outreach queue alert ──
QUEUE_SIZE = 15
queue_df = df[(df["priority_rank"] == 1) & (df["status"] == "not_contacted")].head(QUEUE_SIZE)
if not queue_df.empty:
    remaining = len(df[(df["priority_rank"] == 1) & (df["status"] == "not_contacted")])
    st.markdown(
        f'<div class="alert-box">'
        f'<b>Outreach Queue:</b> {remaining} Tier A prospects not yet contacted. '
        f'Work through the <b>Queue</b> tab — as you email them, new ones appear automatically.'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("")


# ── Tabs ──
tab_queue, tab_a, tab_b, tab_c, tab_us, tab_pipeline = st.tabs([
    f"Queue ({uncontacted_a})", "Tier A", "Tier B", "Tier C", "US Market", "Pipeline View"
])


def render_tier_tab(df_subset: pd.DataFrame, empty_msg: str = "No institutions here."):
    if df_subset.empty:
        st.info(empty_msg)
        return
    df_subset = df_subset.sort_values("composite_score", ascending=False)
    for _, row in df_subset.iterrows():
        render_institution_card(row)


with tab_queue:
    st.markdown(
        "**Your Outreach Queue** — Top uncontacted Tier A prospects, sorted by score. "
        "Email them, then move the status to *Email Sent*. The queue auto-refills as you work through it."
    )
    queue_show = df[(df["priority_rank"] == 1) & (df["status"] == "not_contacted")].sort_values(
        "composite_score", ascending=False
    ).head(QUEUE_SIZE)
    if queue_show.empty:
        st.success("All Tier A prospects have been contacted! Check Tier B next.")
    else:
        for _, row in queue_show.iterrows():
            render_institution_card(row, queue_mode=True)

with tab_a:
    render_tier_tab(
        filtered[filtered["priority_rank"] == 1],
        "No Tier A prospects match your current filters.",
    )

with tab_b:
    render_tier_tab(
        filtered[filtered["priority_rank"] == 2],
        "No Tier B prospects match your current filters.",
    )

with tab_c:
    render_tier_tab(
        filtered[filtered["priority_rank"] == 3],
        "No Tier C prospects match your current filters.",
    )

with tab_us:
    st.markdown("### US Market Prospects")
    us_df = filtered[filtered["country"] == "US"].sort_values(
        ["priority_rank", "composite_score"], ascending=[True, False]
    )
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
            render_institution_card(row)

with tab_pipeline:
    st.markdown("### Pipeline — All Institutions by Stage")
    for stage in STATUS_ORDER:
        stage_df = df[df["status"] == stage].sort_values("composite_score", ascending=False)
        count = len(stage_df)
        color = STATUS_COLORS[stage]
        label = STATUS_LABELS[stage]
        st.markdown(
            f'<div style="border-left:4px solid {color};padding-left:0.8rem;margin:1rem 0 0.3rem 0;">'
            f'<b style="color:{color};">{label}</b> &nbsp; <span style="color:#6b7a8d;">{count} institution{"s" if count != 1 else ""}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if count > 0:
            for _, row in stage_df.iterrows():
                render_institution_card(row)
        else:
            st.caption("None yet.")
        st.markdown("")
