"""
MedPort Prospect Dashboard — Team CRM
=======================================
Streamlit dashboard that reads from Supabase (falls back to local CSV).
Provides full CRM functionality: status tracking, assignments, notes, and
outreach angle copy — accessible to the whole 5-person founding team.

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

# ─────────────────────────────────────────────
# Page config — must be first Streamlit call
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="MedPort Prospect Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Auth — Google OAuth via Streamlit built-in
# ─────────────────────────────────────────────

if not st.experimental_user.is_logged_in:
    st.title("MedPort Prospect Dashboard")
    st.markdown("Sign in with your MedPort Google account to access the prospect database.")
    if st.button("Sign in with Google", type="primary"):
        st.login()
    st.stop()

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────

MEDPORT_BLUE = "#1B4F72"

STATUS_COLORS = {
    "not_contacted": MEDPORT_BLUE,
    "contacted": "#2980b9",
    "responded": "#27ae60",
    "meeting_booked": "#f39c12",
    "declined": "#aab4bf",
    "converted": "#1a8a4a",
}

STATUS_ORDER = [
    "not_contacted",
    "contacted",
    "responded",
    "meeting_booked",
    "declined",
    "converted",
]

STATUS_LABELS = {
    "not_contacted": "Not Contacted",
    "contacted": "Contacted",
    "responded": "Responded",
    "meeting_booked": "Meeting Booked",
    "declined": "Declined",
    "converted": "Converted",
}

TEAM_MEMBERS = [
    "Unassigned",
    "Arav",
    "CFO",
    "Team Member 3",
    "Team Member 4",
    "Team Member 5",
]

st.markdown(f"""
<style>
  /* Global */
  .main .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; }}
  h1 {{ color: {MEDPORT_BLUE}; font-weight: 800; letter-spacing: -0.5px; }}
  h2, h3 {{ color: {MEDPORT_BLUE}; }}

  /* Stat cards */
  .stat-card {{
    background: #ffffff;
    border: 1px solid #e0e7ef;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(27,79,114,0.07);
  }}
  .stat-card .stat-value {{
    font-size: 2.2rem;
    font-weight: 800;
    color: {MEDPORT_BLUE};
    line-height: 1;
  }}
  .stat-card .stat-label {{
    font-size: 0.78rem;
    color: #6b7a8d;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 0.3rem;
  }}

  /* Institution card */
  .inst-card {{
    background: #f8fafc;
    border: 1px solid #dde6f0;
    border-left: 4px solid {MEDPORT_BLUE};
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
  }}
  .inst-header {{
    font-size: 1.05rem;
    font-weight: 700;
    color: #1a2a3a;
  }}
  .inst-meta {{
    font-size: 0.8rem;
    color: #5a6a7a;
    margin-top: 0.2rem;
  }}

  /* Score badges */
  .score-green  {{ background:#d4edda; color:#155724; padding:2px 8px; border-radius:20px; font-weight:700; font-size:0.85rem; }}
  .score-yellow {{ background:#fff3cd; color:#856404; padding:2px 8px; border-radius:20px; font-weight:700; font-size:0.85rem; }}
  .score-red    {{ background:#f8d7da; color:#721c24; padding:2px 8px; border-radius:20px; font-weight:700; font-size:0.85rem; }}

  /* Risk badges */
  .risk-none   {{ background:#d4edda; color:#155724; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:600; }}
  .risk-low    {{ background:#d1ecf1; color:#0c5460; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:600; }}
  .risk-medium {{ background:#fff3cd; color:#856404; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:600; }}
  .risk-high   {{ background:#f8d7da; color:#721c24; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:600; }}

  /* Type badge */
  .type-badge {{
    background: {MEDPORT_BLUE}20;
    color: {MEDPORT_BLUE};
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }}

  /* Tier badge */
  .tier-a {{ background:#1B4F72; color:#fff; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:700; }}
  .tier-b {{ background:#2980b9; color:#fff; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:700; }}
  .tier-c {{ background:#aab4bf; color:#fff; padding:2px 9px; border-radius:20px; font-size:0.78rem; font-weight:700; }}

  /* Status badge */
  .status-badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #fff;
  }}

  /* Outreach box */
  .outreach-box {{
    background: #eaf4fb;
    border-left: 3px solid #2980b9;
    border-radius: 6px;
    padding: 0.6rem 0.9rem;
    font-size: 0.88rem;
    color: #1a3a52;
    margin-top: 0.5rem;
  }}

  /* Pipeline funnel row */
  .pipeline-row {{
    display: flex;
    gap: 0.8rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
  }}
  .pipeline-pill {{
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    white-space: nowrap;
    color: #fff;
  }}

  /* Divider */
  hr.subtle {{ border: none; border-top: 1px solid #e8eef4; margin: 0.5rem 0; }}

  /* Sidebar */
  section[data-testid="stSidebar"] {{ background: #f0f5fa; }}
  section[data-testid="stSidebar"] h2 {{ color: {MEDPORT_BLUE}; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Data layer
# ─────────────────────────────────────────────

CSV_PATH = os.path.join(os.path.dirname(__file__), "medport_prospects.csv")


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["innovation_score", "accessibility_score", "fit_score", "priority_rank"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "competitor_risk" in df.columns:
        df["competitor_risk"] = df["competitor_risk"].fillna("none")
    if "country" in df.columns:
        df["country"] = df["country"].fillna("").str.upper()
    if "inst_type" in df.columns:
        df["inst_type"] = df["inst_type"].fillna("unknown")
    if "composite_score" not in df.columns:
        df["composite_score"] = (
            df.get("innovation_score", 0)
            + df.get("accessibility_score", 0)
            + df.get("fit_score", 0)
        )
    if "status" not in df.columns:
        df["status"] = "not_contacted"
    else:
        df["status"] = df["status"].fillna("not_contacted")
    if "assigned_to" not in df.columns:
        df["assigned_to"] = "Unassigned"
    else:
        df["assigned_to"] = df["assigned_to"].fillna("Unassigned")
    if "contact_notes" not in df.columns:
        df["contact_notes"] = ""
    else:
        df["contact_notes"] = df["contact_notes"].fillna("")
    if "outreach_count" not in df.columns:
        df["outreach_count"] = 0
    if "id" not in df.columns:
        df["id"] = df.index.astype(str)
    return df


def _load_csv_fallback() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame()
    df = pd.read_csv(CSV_PATH)
    return _normalize_df(df)


@st.cache_data(ttl=30)
def load_from_supabase() -> pd.DataFrame:
    url = os.environ.get("SUPABASE_URL", "") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "") or st.secrets.get("SUPABASE_ANON_KEY", "")
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
        df = pd.DataFrame(result.data)
        return _normalize_df(df)
    except Exception as e:
        st.warning(f"Supabase load failed, falling back to CSV: {e}")
        return _load_csv_fallback()


def update_prospect_crm(prospect_id: str, updates: dict):
    """Write CRM field updates back to Supabase."""
    url = os.environ.get("SUPABASE_URL", "") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "") or st.secrets.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return  # silently skip — CSV mode has no write-back
    try:
        from supabase import create_client
        client = create_client(url, key)
        client.table("prospects").update(updates).eq("id", prospect_id).execute()
    except Exception as e:
        st.error(f"Failed to save update: {e}")


# ─────────────────────────────────────────────
# Badge helpers
# ─────────────────────────────────────────────

def score_badge(score: int) -> str:
    score = int(score) if score else 0
    if score >= 8:
        return f'<span class="score-green">{score}</span>'
    elif score >= 5:
        return f'<span class="score-yellow">{score}</span>'
    else:
        return f'<span class="score-red">{score}</span>'


def risk_badge(risk: str) -> str:
    risk = (risk or "none").lower()
    css = f"risk-{risk}" if risk in ("none", "low", "medium", "high") else "risk-none"
    return f'<span class="{css}">{risk.capitalize()}</span>'


def tier_badge(rank) -> str:
    tier = {1: "A", 2: "B", 3: "C"}.get(int(rank) if rank else 3, "C")
    return f'<span class="tier-{tier.lower()}">Tier {tier}</span>'


def type_badge(inst_type: str) -> str:
    return f'<span class="type-badge">{inst_type or "?"}</span>'


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, MEDPORT_BLUE)
    label = STATUS_LABELS.get(status, status.replace("_", " ").title())
    return f'<span class="status-badge" style="background:{color};">{label}</span>'


# ─────────────────────────────────────────────
# Institution card renderer
# ─────────────────────────────────────────────

def render_institution_card(row: pd.Series):
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
    inno = row.get("innovation_score", 0)
    access = row.get("accessibility_score", 0)
    fit = row.get("fit_score", 0)
    current_status = row.get("status", "not_contacted")
    current_assigned = row.get("assigned_to", "Unassigned") or "Unassigned"
    current_notes = row.get("contact_notes", "") or ""
    prospect_id = str(row.get("id", ""))
    outreach_count = int(row.get("outreach_count", 0) or 0)

    location = f"{city}, {country}" if city else country
    border_color = STATUS_COLORS.get(current_status, MEDPORT_BLUE)

    # Expander label includes current status badge (plain text since expander label is plain)
    status_label = STATUS_LABELS.get(current_status, current_status)
    expander_label = f"{name}  —  {location}  [{status_label}]"

    with st.expander(expander_label, expanded=False):
        # Inject status-based left border color via inline div wrapper
        st.markdown(
            f'<div style="border-left:4px solid {border_color};padding-left:0.6rem;margin-bottom:0.5rem;">',
            unsafe_allow_html=True,
        )

        # Header row
        col_title, col_tier = st.columns([5, 1])
        with col_title:
            st.markdown(
                f'<div class="inst-header">{name}</div>'
                f'<div class="inst-meta">'
                f'{location} &nbsp; {type_badge(inst_type)} &nbsp; {status_badge(current_status)}'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_tier:
            st.markdown(
                f'<div style="text-align:right;margin-top:4px">{tier_badge(rank)}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="subtle">', unsafe_allow_html=True)

        # Scores row
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(
                "<div style='font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;'>Innovation</div>"
                + score_badge(inno),
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                "<div style='font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;'>Accessibility</div>"
                + score_badge(access),
                unsafe_allow_html=True,
            )
        with s3:
            st.markdown(
                "<div style='font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;'>Fit</div>"
                + score_badge(fit),
                unsafe_allow_html=True,
            )
        with s4:
            st.markdown(
                "<div style='font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;'>Competitor Risk</div>"
                + risk_badge(risk),
                unsafe_allow_html=True,
            )

        st.markdown("")

        # Decision maker
        dm_parts = []
        if dm_name:
            dm_parts.append(f"**{dm_name}**")
        if dm_title:
            dm_parts.append(dm_title)
        if dm_parts:
            st.markdown("**Decision maker:** " + " — ".join(dm_parts))
        if dm_linkedin:
            st.markdown(f"**LinkedIn search:** `{dm_linkedin}`")

        # Outreach angle — copyable via st.code()
        if outreach:
            st.markdown("**Outreach angle:**")
            st.code(outreach, language=None)

        # Research notes
        if notes:
            st.markdown(f"**Notes:** {notes}")

        # Links
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
                "Status",
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
                        "outreach_count": outreach_count + 1,
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

        # Contact notes
        new_notes = st.text_area(
            "Contact notes",
            value=current_notes,
            height=80,
            key=f"notes_{prospect_id}",
            placeholder="Add notes about this contact...",
        )
        if st.button("Save notes", key=f"save_notes_{prospect_id}"):
            update_prospect_crm(prospect_id, {"contact_notes": new_notes})
            st.success("Notes saved.")
            st.cache_data.clear()

        if outreach_count > 0:
            st.caption(f"Outreach count: {outreach_count}")

        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

with st.sidebar:
    # User info
    user_name = getattr(st.experimental_user, "name", "") or "Team Member"
    user_email = getattr(st.experimental_user, "email", "") or ""
    st.markdown(f"## MedPort")
    st.markdown(
        f"<span style='color:{MEDPORT_BLUE};font-size:0.85rem;'>Prospect Intelligence CRM</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='font-size:0.78rem;color:#6b7a8d;'>Signed in as {user_name}</span>",
        unsafe_allow_html=True,
    )
    if st.button("Sign out", use_container_width=False):
        st.logout()

    st.markdown("---")

    # Auto-refresh
    auto_refresh = st.toggle("Auto-refresh (30s)", value=False)

    st.markdown("### Filters")

    # My Prospects toggle
    my_prospects_only = st.toggle("My Prospects only", value=False)

    # Country
    country_opt = st.radio("Country", ["Both", "CA", "US"], horizontal=True)

    # Load data once for filter population
    _df_all = load_from_supabase()
    has_data = len(_df_all) > 0

    # Institution type
    if has_data and "inst_type" in _df_all.columns:
        all_types = sorted(_df_all["inst_type"].unique().tolist())
    else:
        all_types = ["CHC", "university", "FQHC", "walk-in", "specialty", "dental"]
    selected_types = st.multiselect("Institution Type", all_types, default=all_types)

    # Tier
    selected_tiers = st.multiselect("Priority Tier", ["A", "B", "C"], default=["A", "B", "C"])

    # Status filter
    selected_statuses = st.multiselect(
        "Status",
        STATUS_ORDER,
        default=STATUS_ORDER,
        format_func=lambda s: STATUS_LABELS.get(s, s),
    )

    # Assigned-to filter
    all_assignees = ["All"] + TEAM_MEMBERS[1:]  # skip "Unassigned" as filter option
    selected_assignee = st.selectbox("Assigned to", ["All"] + TEAM_MEMBERS)

    # Min composite score
    min_score = st.slider("Min Composite Score", min_value=0, max_value=30, value=0, step=1)

    st.markdown("---")
    st.markdown("### Actions")

    # Run scraper button
    if st.button("Run Scraper + Sync", use_container_width=True, type="primary"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "customer_discovery.py")
        cmd = [
            "python3", script_path,
            "--country", "both",
            "--resume",
            "--supabase",
            "--output", CSV_PATH,
        ]
        with st.spinner("Running discovery scraper and syncing to Supabase..."):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode == 0:
                    st.success("Scraper finished and synced to Supabase.")
                    st.text_area("Output", result.stdout[-3000:] if result.stdout else "", height=200)
                else:
                    st.error("Scraper exited with errors.")
                    st.text_area("stderr", result.stderr[-2000:] if result.stderr else "", height=200)
            except subprocess.TimeoutExpired:
                st.warning("Scraper is taking a long time — check your terminal for progress.")
            except Exception as e:
                st.error(f"Could not run scraper: {e}")
        st.cache_data.clear()
        st.rerun()

    # Refresh data
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Download CSV
    if has_data and os.path.exists(CSV_PATH):
        with open(CSV_PATH, "rb") as f:
            st.download_button(
                label="Download CSV",
                data=f,
                file_name="medport_prospects.csv",
                mime="text/csv",
                use_container_width=True,
            )


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

POSTHOG_KEY = os.environ.get("POSTHOG_API_KEY", "") or st.secrets.get("POSTHOG_API_KEY", "")
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
# Main content
# ─────────────────────────────────────────────

st.markdown("# MedPort Prospect CRM")

df = load_from_supabase()

if df.empty:
    st.info(
        "No data yet. Click **Run Scraper + Sync** in the sidebar, "
        "or run `python customer_discovery.py --country both --supabase` from the terminal."
    )
    st.stop()

# ── Apply filters ──
filtered = df.copy()

if my_prospects_only:
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

# ── Pipeline funnel ──
pipeline_html = '<div class="pipeline-row">'
for status in STATUS_ORDER:
    count = len(df[df["status"] == status])
    color = STATUS_COLORS[status]
    label = STATUS_LABELS[status]
    pipeline_html += (
        f'<span class="pipeline-pill" style="background:{color};">'
        f'{label}: {count}'
        f'</span>'
    )
pipeline_html += "</div>"
st.markdown(pipeline_html, unsafe_allow_html=True)

# ── Stats row ──
total = len(filtered)
tier_a_count = len(filtered[filtered["priority_rank"] == 1])
tier_b_count = len(filtered[filtered["priority_rank"] == 2])
avg_score = round(filtered["composite_score"].mean(), 1) if total > 0 else 0.0
converted_count = len(df[df["status"] == "converted"])

c1, c2, c3, c4, c5 = st.columns(5)
for col, value, label in [
    (c1, total, "Showing"),
    (c2, tier_a_count, "Tier A"),
    (c3, tier_b_count, "Tier B"),
    (c4, f"{avg_score}/30", "Avg Score"),
    (c5, converted_count, "Converted"),
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

# ── Tabs ──
tab_a, tab_b, tab_c, tab_all = st.tabs(["Tier A", "Tier B", "Tier C", "All"])


def render_tier_tab(df_subset: pd.DataFrame, empty_msg: str = "No institutions in this tier."):
    if df_subset.empty:
        st.info(empty_msg)
        return
    df_subset = df_subset.sort_values("composite_score", ascending=False)
    for _, row in df_subset.iterrows():
        render_institution_card(row)


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

with tab_all:
    render_tier_tab(
        filtered.sort_values(["priority_rank", "composite_score"], ascending=[True, False]),
        "No prospects match your current filters.",
    )
