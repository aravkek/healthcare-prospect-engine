"""
MedPort Prospect Dashboard
===========================
Streamlit dashboard that reads medport_prospects.csv and surfaces
prioritised outreach targets with scores, decision-maker info, and pitch angles.

Deploy to Streamlit Community Cloud (free) via GitHub repo.
"""

import os
import subprocess
import time
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="MedPort Prospect Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────

MEDPORT_BLUE = "#1B4F72"

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

  /* Divider */
  hr.subtle {{ border: none; border-top: 1px solid #e8eef4; margin: 0.5rem 0; }}

  /* Sidebar */
  section[data-testid="stSidebar"] {{ background: #f0f5fa; }}
  section[data-testid="stSidebar"] h2 {{ color: {MEDPORT_BLUE}; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

CSV_PATH = os.path.join(os.path.dirname(__file__), "medport_prospects.csv")


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


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame()
    df = pd.read_csv(CSV_PATH)
    # Normalise columns
    for col in ["innovation_score", "accessibility_score", "fit_score", "priority_rank"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "competitor_risk" in df.columns:
        df["competitor_risk"] = df["competitor_risk"].fillna("none")
    if "country" in df.columns:
        df["country"] = df["country"].fillna("").str.upper()
    if "inst_type" in df.columns:
        df["inst_type"] = df["inst_type"].fillna("unknown")
    # Composite score
    df["composite_score"] = df["innovation_score"] + df["accessibility_score"] + df["fit_score"]
    return df


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

    location = f"{city}, {country}" if city else country
    expander_label = f"{name}  —  {location}"

    with st.expander(expander_label, expanded=False):
        # Header row
        col_title, col_tier = st.columns([5, 1])
        with col_title:
            st.markdown(
                f'<div class="inst-header">{name}</div>'
                f'<div class="inst-meta">{location} &nbsp; {type_badge(inst_type)}</div>',
                unsafe_allow_html=True,
            )
        with col_tier:
            st.markdown(f'<div style="text-align:right;margin-top:4px">{tier_badge(rank)}</div>',
                        unsafe_allow_html=True)

        st.markdown('<hr class="subtle">', unsafe_allow_html=True)

        # Scores row
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(
                f"<div style='font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;'>Innovation</div>"
                f"{score_badge(inno)}",
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f"<div style='font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;'>Accessibility</div>"
                f"{score_badge(access)}",
                unsafe_allow_html=True,
            )
        with s3:
            st.markdown(
                f"<div style='font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;'>Fit</div>"
                f"{score_badge(fit)}",
                unsafe_allow_html=True,
            )
        with s4:
            st.markdown(
                f"<div style='font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;'>Competitor Risk</div>"
                f"{risk_badge(risk)}",
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

        # Outreach angle
        if outreach:
            st.markdown(
                f'<div class="outreach-box"><strong>Outreach angle:</strong><br>{outreach}</div>',
                unsafe_allow_html=True,
            )

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


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"## MedPort")
    st.markdown(f"<span style='color:{MEDPORT_BLUE};font-size:0.85rem;'>Prospect Intelligence Dashboard</span>",
                unsafe_allow_html=True)
    st.markdown("---")

    # Auto-refresh
    auto_refresh = st.toggle("Auto-refresh (60s)", value=False)

    st.markdown("### Filters")

    # Country
    country_opt = st.radio("Country", ["Both", "CA", "US"], horizontal=True)

    # Load data once for filter population
    _df_all = load_data()
    has_data = len(_df_all) > 0

    # Institution type
    if has_data and "inst_type" in _df_all.columns:
        all_types = sorted(_df_all["inst_type"].unique().tolist())
    else:
        all_types = ["CHC", "university", "FQHC", "walk-in", "specialty", "dental"]
    selected_types = st.multiselect("Institution Type", all_types, default=all_types)

    # Tier
    selected_tiers = st.multiselect("Priority Tier", ["A", "B", "C"], default=["A", "B", "C"])

    # Min composite score
    min_score = st.slider("Min Composite Score", min_value=0, max_value=30, value=0, step=1)

    st.markdown("---")
    st.markdown("### Actions")

    # Run scraper button
    if st.button("Run Scraper", use_container_width=True, type="primary"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "customer_discovery.py")
        cmd = ["python3", script_path, "--country", "both", "--resume",
               "--output", CSV_PATH]
        with st.spinner("Running discovery scraper..."):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode == 0:
                    st.success("Scraper finished successfully.")
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

    # Download CSV
    if has_data:
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
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()


# ─────────────────────────────────────────────
# Main content
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# PostHog analytics (inject once per session)
# ─────────────────────────────────────────────

POSTHOG_KEY = os.environ.get("POSTHOG_API_KEY", "")
if POSTHOG_KEY:
    components.html(f"""
    <script>
    !function(t,e){{var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){{function g(t,e){{var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){{t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){{var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e}},u.people.toString=function(){{return u.toString(1)+".people (stub)"}},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])}}e.__SV=1}}(document,window.posthog||[]);
    posthog.init('{POSTHOG_KEY}', {{api_host:'https://app.posthog.com'}});
    posthog.capture('dashboard_viewed');
    </script>
    """, height=0)

st.markdown("# MedPort Prospect Dashboard")

# ── Email capture banner ──
with st.container():
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,{MEDPORT_BLUE} 0%,#2980b9 100%);
                border-radius:12px;padding:1.1rem 1.6rem;margin-bottom:1.2rem;
                display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.8rem;">
      <div>
        <div style="color:#fff;font-weight:700;font-size:1.05rem;">
          Get weekly AI-ready clinic updates for Ontario & US
        </div>
        <div style="color:#cfe2f3;font-size:0.82rem;margin-top:0.2rem;">
          New high-fit prospects scored every week — free, no spam.
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Inline email capture via Formspree (replace YOUR_FORM_ID with your Formspree endpoint)
    FORMSPREE_ID = os.environ.get("FORMSPREE_ID", "")
    if FORMSPREE_ID:
        components.html(f"""
        <form action="https://formspree.io/f/{FORMSPREE_ID}" method="POST"
              style="display:flex;gap:8px;flex-wrap:wrap;margin-top:-0.5rem;">
          <input type="email" name="email" placeholder="your@email.com" required
                 style="flex:1;min-width:200px;padding:8px 12px;border:1px solid #d0dce8;
                        border-radius:8px;font-size:0.9rem;outline:none;">
          <button type="submit"
                  style="background:#1B4F72;color:#fff;border:none;border-radius:8px;
                         padding:8px 18px;font-size:0.9rem;cursor:pointer;font-weight:600;">
            Get Updates
          </button>
        </form>
        """, height=55)

df = load_data()

if df.empty:
    st.info(
        "No data yet. Click **Run Scraper** in the sidebar to get started, "
        "or run `python customer_discovery.py --country both` from the terminal."
    )
    st.stop()

# ── Apply filters ──
filtered = df.copy()

if country_opt != "Both":
    filtered = filtered[filtered["country"] == country_opt]

if selected_types:
    filtered = filtered[filtered["inst_type"].isin(selected_types)]

tier_rank_map = {"A": 1, "B": 2, "C": 3}
selected_ranks = [tier_rank_map[t] for t in selected_tiers if t in tier_rank_map]
if selected_ranks:
    filtered = filtered[filtered["priority_rank"].isin(selected_ranks)]

if min_score > 0:
    filtered = filtered[filtered["composite_score"] >= min_score]

# ── Stats row ──
total = len(filtered)
tier_a_count = len(filtered[filtered["priority_rank"] == 1])
tier_b_count = len(filtered[filtered["priority_rank"] == 2])
avg_score = round(filtered["composite_score"].mean(), 1) if total > 0 else 0.0

c1, c2, c3, c4 = st.columns(4)
for col, value, label in [
    (c1, total, "Total Prospects"),
    (c2, tier_a_count, "Tier A"),
    (c3, tier_b_count, "Tier B"),
    (c4, f"{avg_score}/30", "Avg Composite Score"),
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
    # Sort by composite score descending within tier
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
