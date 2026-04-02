"""
MedPort Intelligence Engine — advanced prospect research, competitor mapping,
clear lane finder, advanced scoring, prospect hunter, and outreach reports.
"""

import os
import sys
import json
from datetime import datetime

import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import (
    inject_css, MEDPORT_TEAL, MEDPORT_BLUE, MEDPORT_DARK,
    MEDPORT_LIGHT_TEAL, STATUS_COLORS, STATUS_LABELS,
)
from lib.auth import check_auth, is_admin
from lib.db import load_prospects, update_prospect, create_task
from lib.ai import call_ai, has_ai_configured, ai_provider_badge, MODEL

st.set_page_config(
    page_title="Intelligence — MedPort",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)

# ─── Competitor data ─────────────────────────────────────────────────────────

KNOWN_COMPETITORS = {
    "Care Cru": {"focus": "dental practices, DSOs", "markets": ["US"], "threat": "high"},
    "Novoflow": {"focus": "primary care, family medicine", "markets": ["CA", "US"], "threat": "high"},
    "Medi": {"focus": "walk-in clinics, urgent care", "markets": ["CA"], "threat": "medium"},
    "Decoda Health": {"focus": "CHCs, community health", "markets": ["CA"], "threat": "high"},
    "Waive Medical": {"focus": "specialty clinics", "markets": ["US"], "threat": "medium"},
    "Luma Health": {"focus": "health systems, hospitals", "markets": ["US"], "threat": "medium"},
    "Klara": {"focus": "dermatology, specialty", "markets": ["US"], "threat": "low"},
    "Hyro": {"focus": "hospitals, large health systems", "markets": ["US"], "threat": "low"},
    "Nuance/Microsoft": {"focus": "hospitals, EHR-integrated", "markets": ["US", "CA"], "threat": "low"},
}

# Keywords to match competitor focus against inst_type
COMPETITOR_TYPE_KEYWORDS = {
    "Care Cru": ["dental", "dso"],
    "Novoflow": ["primary care", "family medicine", "family health", "chc", "fqhc"],
    "Medi": ["walk-in", "urgent care", "walk_in"],
    "Decoda Health": ["chc", "community health", "fqhc", "indigenous"],
    "Waive Medical": ["specialty", "specialist"],
    "Luma Health": ["hospital", "health system", "health centre"],
    "Klara": ["dermatology", "specialty", "specialist"],
    "Hyro": ["hospital", "health system"],
    "Nuance/Microsoft": ["hospital", "health system", "ehren"],
}


def _count_at_risk(df: pd.DataFrame, competitor: str) -> int:
    """Count prospects whose inst_type matches competitor's focus keywords."""
    if df.empty or "inst_type" not in df.columns:
        return 0
    keywords = COMPETITOR_TYPE_KEYWORDS.get(competitor, [])
    if not keywords:
        return 0
    mask = df["inst_type"].str.lower().apply(
        lambda t: any(kw in t for kw in keywords)
    )
    # Also filter by markets
    markets = KNOWN_COMPETITORS[competitor]["markets"]
    if "country" in df.columns and "CA" not in markets and "US" not in markets:
        pass
    elif "country" in df.columns:
        country_mask = df["country"].isin(markets)
        mask = mask & country_mask
    return int(mask.sum())


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _df_to_text(df: pd.DataFrame, max_rows: int = 108) -> str:
    """Convert prospect dataframe to compact text for Claude context."""
    if df.empty:
        return "No prospects in database."
    cols = ["name", "city", "country", "inst_type", "status", "priority_rank",
            "innovation_score", "accessibility_score", "fit_score",
            "startup_receptiveness", "competitor_risk", "existing_ai_tools",
            "outreach_angle", "research_notes"]
    available = [c for c in cols if c in df.columns]
    subset = df[available].head(max_rows)
    lines = []
    for _, row in subset.iterrows():
        parts = []
        for col in available:
            val = row.get(col, "")
            if val and str(val) not in ("nan", "0", ""):
                parts.append(f"{col}={val}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _prospect_row_to_text(row: pd.Series) -> str:
    parts = []
    for col in row.index:
        val = row[col]
        if val and str(val) not in ("nan", "0", ""):
            parts.append(f"{col}: {val}")
    return "\n".join(parts)


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">Intelligence</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='font-size:0.8rem;color:#94a3b8;'>{name}</div>", unsafe_allow_html=True)
    st.markdown("---")

    try:
        auth_configured = bool(st.secrets.get("auth", {}))
    except Exception:
        auth_configured = False
    if auth_configured and os.environ.get("LOCAL_DEV", "false").lower() != "true":
        if st.button("Sign out"):
            st.logout()

    st.markdown("---")
    provider = ai_provider_badge()
    if "Claude" in provider:
        st.markdown(
            f'<span style="background:{MEDPORT_TEAL};color:#fff;border-radius:6px;padding:2px 10px;font-size:0.75rem;font-weight:700;">Claude Sonnet</span>',
            unsafe_allow_html=True,
        )
    elif "Groq" in provider:
        st.markdown(
            '<span style="background:#f59e0b;color:#fff;border-radius:6px;padding:2px 10px;font-size:0.75rem;font-weight:700;">Groq Fallback</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span style="background:#fef2f2;color:#991b1b;border-radius:6px;padding:2px 10px;font-size:0.75rem;font-weight:700;">No AI Key</span>',
            unsafe_allow_html=True,
        )

# ─── Load data ───────────────────────────────────────────────────────────────

df = load_prospects()

# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown(
    f'<div style="font-size:1.9rem;font-weight:800;color:{MEDPORT_DARK};font-family:Syne,sans-serif;margin-bottom:0.2rem;">Intelligence Engine</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div style="color:#64748b;font-size:0.88rem;margin-bottom:1.5rem;">Competitor mapping, clear-lane prospects, advanced scoring, and prospect hunting — all AI-powered.</div>',
    unsafe_allow_html=True,
)

if not has_ai_configured():
    st.warning("No AI API key configured. Add ANTHROPIC_API_KEY to Streamlit secrets to use AI features. Competitor map will still work.")

# ─── Tabs ────────────────────────────────────────────────────────────────────

tab_threat, tab_clearlane, tab_scoring, tab_hunter, tab_report = st.tabs([
    "Competitor Threat Map",
    "Clear Lane Finder",
    "Advanced Scoring",
    "Prospect Hunter",
    "Weekly Report",
])

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1: Competitor Threat Map
# ═════════════════════════════════════════════════════════════════════════════

with tab_threat:
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.3rem;">Competitor Threat Map</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.82rem;color:#64748b;margin-bottom:1rem;">How many of our 108 prospects are each competitor likely targeting? Based on institution type and market overlap.</div>',
        unsafe_allow_html=True,
    )

    # Build table data
    rows = []
    for comp_name, comp_data in KNOWN_COMPETITORS.items():
        at_risk = _count_at_risk(df, comp_name)
        rows.append({
            "Competitor": comp_name,
            "Focus": comp_data["focus"],
            "Markets": ", ".join(comp_data["markets"]),
            "Threat": comp_data["threat"],
            "Prospects at Risk": at_risk,
        })

    threat_df = pd.DataFrame(rows)

    # Render as styled HTML table
    def threat_badge(level: str) -> str:
        cls = f"threat-{level}"
        return f'<span class="{cls}">{level.upper()}</span>'

    table_html = '<table class="mp-table"><thead><tr>'
    for col in ["Competitor", "Focus", "Markets", "Threat", "Prospects at Risk"]:
        table_html += f"<th>{col}</th>"
    table_html += "</tr></thead><tbody>"

    for _, row in threat_df.sort_values("Prospects at Risk", ascending=False).iterrows():
        table_html += "<tr>"
        table_html += f'<td><strong>{row["Competitor"]}</strong></td>'
        table_html += f'<td style="color:#475569;">{row["Focus"]}</td>'
        table_html += f'<td><span class="mp-badge" style="background:#f1f5f9;color:#475569;">{row["Markets"]}</span></td>'
        table_html += f'<td>{threat_badge(row["Threat"])}</td>'
        at_risk_val = row["Prospects at Risk"]
        color = "#991b1b" if at_risk_val > 10 else ("#92400e" if at_risk_val > 5 else "#065f46")
        table_html += f'<td><strong style="color:{color};">{at_risk_val}</strong></td>'
        table_html += "</tr>"
    table_html += "</tbody></table>"

    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Summary insights
    total_at_risk_prospects = set()
    for comp_name in KNOWN_COMPETITORS:
        keywords = COMPETITOR_TYPE_KEYWORDS.get(comp_name, [])
        markets = KNOWN_COMPETITORS[comp_name]["markets"]
        if keywords and not df.empty and "inst_type" in df.columns:
            mask = df["inst_type"].str.lower().apply(lambda t: any(kw in t for kw in keywords))
            if "country" in df.columns:
                mask = mask & df["country"].isin(markets)
            matching_ids = df[mask]["id"].tolist()
            total_at_risk_prospects.update(str(i) for i in matching_ids)

    safe_count = len(df) - len(total_at_risk_prospects) if not df.empty else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value">{len(total_at_risk_prospects)}</div><div class="stat-label">Prospects Contested</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value" style="color:{MEDPORT_TEAL};">{safe_count}</div><div class="stat-label">Likely Clear Lane</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        high_threat = sum(1 for c in KNOWN_COMPETITORS.values() if c["threat"] == "high")
        st.markdown(
            f'<div class="stat-card"><div class="stat-value">{high_threat}</div><div class="stat-label">High-Threat Competitors</div></div>',
            unsafe_allow_html=True,
        )

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2: Clear Lane Finder
# ═════════════════════════════════════════════════════════════════════════════

with tab_clearlane:
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.3rem;">Clear Lane Finder</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.82rem;color:#64748b;margin-bottom:1rem;">Claude analyzes your full prospect database and surfaces the 10–15 institutions least likely to have competitor coverage — your best shots at uncontested deals.</div>',
        unsafe_allow_html=True,
    )

    if st.button("Find Clear Lane Prospects", type="primary", key="do_clear_lane"):
        if df.empty:
            st.warning("No prospects loaded.")
        elif not has_ai_configured():
            st.error("No AI key configured.")
        else:
            with st.spinner("Claude is analyzing your full database for clear-lane opportunities..."):
                prospect_text = _df_to_text(df)
                competitors_text = "\n".join(
                    f"- {k}: focuses on {v['focus']}, markets {v['markets']}, threat={v['threat']}"
                    for k, v in KNOWN_COMPETITORS.items()
                )
                system = """You are a strategic sales intelligence analyst for MedPort, an AI voice agent startup for clinic phone intake.
Your job: identify the prospects with the lowest competitor coverage risk — the "clear lane" opportunities.

MedPort targets: appointment booking AI, phone intake automation, triage support.
Key differentiator: full call handling, not just scheduling widgets."""

                prompt = f"""Here is MedPort's full prospect database ({len(df)} institutions):

{prospect_text}

Known competitors and their focus areas:
{competitors_text}

Identify the 12-15 BEST "clear lane" prospects — those least likely to have competitor coverage.

Selection criteria (in order of importance):
1. Institution type NOT in any competitor's sweet spot
2. Canadian market (most competitors are US-focused)
3. Niche institution types: universities, FQHCs, CHCs, Indigenous health centres, student wellness
4. Small-to-medium volume (below enterprise threshold for Nuance/Hyro)
5. No existing_ai_tools detected
6. High startup_receptiveness score (7+)
7. Not yet contacted (status=not_contacted)

For each clear-lane prospect, output in this exact format:
---
PROSPECT: [name]
CITY: [city, country]
WHY CLEAR LANE: [2-3 specific reasons — reference their type, market, and competitor gap]
FIRST MESSAGE: [One sharp, specific opening line for cold outreach — reference their specific context]
SCORE: [estimated composite score /40]
---

Rank them best first. Be specific and tactical."""

                try:
                    result, provider = call_ai(system, [{"role": "user", "content": prompt}], max_tokens=3000)
                    st.session_state["clear_lane_result"] = result
                    st.session_state["clear_lane_provider"] = provider
                except Exception as e:
                    st.error(f"AI request failed: {e}")

    # Display cached result
    if "clear_lane_result" in st.session_state:
        provider = st.session_state.get("clear_lane_provider", "Claude")
        if provider != "Claude":
            st.caption(f"Generated by {provider}")

        raw = st.session_state["clear_lane_result"]

        # Parse and render as cards
        blocks = [b.strip() for b in raw.split("---") if b.strip()]
        rendered = 0
        for block in blocks:
            lines = block.strip().split("\n")
            card_data = {}
            for line in lines:
                if line.startswith("PROSPECT:"):
                    card_data["name"] = line.replace("PROSPECT:", "").strip()
                elif line.startswith("CITY:"):
                    card_data["city"] = line.replace("CITY:", "").strip()
                elif line.startswith("WHY CLEAR LANE:"):
                    card_data["why"] = line.replace("WHY CLEAR LANE:", "").strip()
                elif line.startswith("FIRST MESSAGE:"):
                    card_data["msg"] = line.replace("FIRST MESSAGE:", "").strip()
                elif line.startswith("SCORE:"):
                    card_data["score"] = line.replace("SCORE:", "").strip()

            if card_data.get("name"):
                st.markdown(
                    f"""
                    <div class="intel-card">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                          <div class="intel-card-header">{card_data.get('name', '?')}</div>
                          <div class="intel-card-sub">{card_data.get('city', '')}</div>
                        </div>
                        <span style="background:rgba(0,184,159,0.1);color:{MEDPORT_TEAL};border-radius:6px;padding:2px 9px;font-size:0.75rem;font-weight:700;">CLEAR LANE</span>
                      </div>
                      <div style="margin-top:0.6rem;font-size:0.83rem;color:#1e293b;"><strong>Why clear lane:</strong> {card_data.get('why', '')}</div>
                      <div style="margin-top:0.5rem;background:#f8fafc;border-left:3px solid {MEDPORT_TEAL};border:1px solid #e2e8f0;border-left:3px solid {MEDPORT_TEAL};border-radius:6px;padding:0.5rem 0.75rem;font-size:0.82rem;color:{MEDPORT_DARK};font-style:italic;">"{card_data.get('msg', '')}"</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                rendered += 1

        if rendered == 0:
            # Fallback: show raw markdown
            st.markdown(raw)

        if st.button("Clear results", key="clear_lane_reset"):
            del st.session_state["clear_lane_result"]
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3: Advanced Scoring Model
# ═════════════════════════════════════════════════════════════════════════════

with tab_scoring:
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.3rem;">Advanced Scoring Model</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.82rem;color:#64748b;margin-bottom:1rem;">Claude re-scores unscored or low-confidence prospects with two new dimensions: Champion Likelihood and Deal Velocity.</div>',
        unsafe_allow_html=True,
    )

    if not df.empty:
        # Find top 20 unscored or low-composite prospects
        low_threshold = 15
        low_df = df[df["composite_score"] <= low_threshold].sort_values("priority_rank").head(20)
        st.caption(f"{len(low_df)} prospects with composite score ≤ {low_threshold} identified for re-scoring.")

        if st.button("Re-score All Prospects with Claude", type="primary", key="do_rescoring"):
            if not has_ai_configured():
                st.error("No AI key configured.")
            elif low_df.empty:
                st.info("All prospects already have strong scores.")
            else:
                with st.spinner(f"Claude is scoring {len(low_df)} prospects..."):
                    system = """You are a healthcare sales intelligence analyst for MedPort, an AI voice agent startup for clinic phone intake.
Score each prospect on 6 dimensions (0-10 each). Be precise and evidence-based."""

                    results = []
                    progress = st.progress(0)
                    for i, (_, row) in enumerate(low_df.iterrows()):
                        prospect_text = _prospect_row_to_text(row)
                        prompt = f"""Score this prospect for MedPort (AI voice agent for clinic phone intake):

{prospect_text}

Return ONLY a JSON object with these keys:
{{
  "innovation_score": 0-10,
  "accessibility_score": 0-10,
  "fit_score": 0-10,
  "startup_receptiveness": 0-10,
  "champion_likelihood": 0-10,
  "deal_velocity": 0-10,
  "rationale": "2 sentence explanation"
}}

Scoring guide:
- innovation_score: how tech-forward is this institution type?
- accessibility_score: how reachable is the decision maker?
- fit_score: how well does MedPort's phone intake AI solve their problem?
- startup_receptiveness: how open are they to working with an early-stage startup?
- champion_likelihood: how likely is there an internal champion who will push for adoption?
- deal_velocity: how fast could this deal close (budget cycles, procurement complexity)?

Return valid JSON only."""

                        try:
                            raw_score, _ = call_ai(system, [{"role": "user", "content": prompt}], max_tokens=400)
                            # Extract JSON
                            raw_score = raw_score.strip()
                            if raw_score.startswith("```"):
                                raw_score = raw_score.split("```")[1]
                                if raw_score.startswith("json"):
                                    raw_score = raw_score[4:]
                            scores = json.loads(raw_score.strip())
                            results.append({
                                "id": str(row.get("id", "")),
                                "name": row.get("name", ""),
                                "before": {
                                    "innovation_score": int(row.get("innovation_score", 0) or 0),
                                    "accessibility_score": int(row.get("accessibility_score", 0) or 0),
                                    "fit_score": int(row.get("fit_score", 0) or 0),
                                    "startup_receptiveness": int(row.get("startup_receptiveness", 0) or 0),
                                },
                                "after": scores,
                            })
                        except Exception as e:
                            results.append({
                                "id": str(row.get("id", "")),
                                "name": row.get("name", ""),
                                "error": str(e),
                                "before": {},
                                "after": {},
                            })
                        progress.progress((i + 1) / len(low_df))

                    st.session_state["scoring_results"] = results
                    progress.empty()
                    st.success(f"Scored {len([r for r in results if 'error' not in r])} prospects.")

    if "scoring_results" in st.session_state:
        results = st.session_state["scoring_results"]
        valid = [r for r in results if "error" not in r]

        if valid:
            st.markdown("#### Before / After Comparison")

            # Render comparison table
            table_html = """<table class="mp-table">
<thead><tr>
<th>Prospect</th>
<th>Fit (before→after)</th>
<th>Innovation</th>
<th>Startup Fit</th>
<th>Champion Likelihood</th>
<th>Deal Velocity</th>
<th>Rationale</th>
</tr></thead><tbody>"""

            for r in valid:
                b = r.get("before", {})
                a = r.get("after", {})

                def delta(key_b, key_a=None):
                    key_a = key_a or key_b
                    bv = b.get(key_b, 0)
                    av = a.get(key_a, 0)
                    diff = av - bv
                    color = "#065f46" if diff > 0 else ("#991b1b" if diff < 0 else "#64748b")
                    sign = "+" if diff > 0 else ""
                    return f'<strong style="color:{MEDPORT_DARK};">{av}</strong> <span style="color:{color};font-size:0.72rem;">({sign}{diff})</span>'

                table_html += f"""<tr>
<td><strong>{r['name']}</strong></td>
<td>{delta('fit_score')}</td>
<td>{delta('innovation_score')}</td>
<td>{delta('startup_receptiveness')}</td>
<td><strong style="color:{MEDPORT_TEAL};">{a.get('champion_likelihood', '?')}</strong></td>
<td><strong>{a.get('deal_velocity', '?')}</strong></td>
<td style="font-size:0.76rem;color:#64748b;max-width:200px;">{a.get('rationale', '')}</td>
</tr>"""

            table_html += "</tbody></table>"
            st.markdown(table_html, unsafe_allow_html=True)

            # Apply scores button
            st.markdown("")
            if st.button("Apply Scores to Database", type="primary", key="apply_scores"):
                applied = 0
                for r in valid:
                    a = r.get("after", {})
                    updates = {}
                    if "innovation_score" in a:
                        updates["innovation_score"] = int(a["innovation_score"])
                    if "accessibility_score" in a:
                        updates["accessibility_score"] = int(a["accessibility_score"])
                    if "fit_score" in a:
                        updates["fit_score"] = int(a["fit_score"])
                    if "startup_receptiveness" in a:
                        updates["startup_receptiveness"] = int(a["startup_receptiveness"])
                    if updates and r.get("id"):
                        if update_prospect(r["id"], updates):
                            applied += 1
                if applied > 0:
                    st.success(f"Applied scores to {applied} prospects. Refresh CRM to see updates.")
                    st.cache_data.clear()
                else:
                    st.warning("No scores applied — check Supabase connection.")

        errors = [r for r in results if "error" in r]
        if errors:
            with st.expander(f"{len(errors)} scoring errors"):
                for e in errors:
                    st.caption(f"{e['name']}: {e.get('error', 'unknown error')}")

        if st.button("Clear scoring results", key="clear_scoring"):
            del st.session_state["scoring_results"]
            st.rerun()
    else:
        if df.empty:
            st.info("No prospects loaded.")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4: Prospect Hunter
# ═════════════════════════════════════════════════════════════════════════════

with tab_hunter:
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.3rem;">Prospect Hunter</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.82rem;color:#64748b;margin-bottom:1rem;">Describe what you\'re looking for in plain English. Claude generates new prospect suggestions your team hasn\'t found yet.</div>',
        unsafe_allow_html=True,
    )

    example_queries = [
        "Find 5 more prospects like Flemingdon Health Centre — CHCs in Ontario that are government-funded and serve marginalized populations",
        "Find urgent care clinics in the GTA that opened in the last 3 years",
        "Find university student health centres in Canada that would benefit from AI phone intake",
        "Find FQHCs or look-alike community health centers in the US Midwest",
    ]

    st.markdown("**Example queries:**")
    for i, ex in enumerate(example_queries):
        if st.button(ex, key=f"hunter_example_{i}"):
            st.session_state["hunter_query"] = ex
            st.rerun()

    hunter_query = st.text_area(
        "Describe what you're looking for",
        value=st.session_state.get("hunter_query", ""),
        height=90,
        placeholder="e.g. Find community health centres in Ontario similar to Flemingdon that serve low-income populations...",
        key="hunter_input",
    )

    if st.button("Hunt for Prospects", type="primary", key="do_hunt"):
        if not hunter_query.strip():
            st.warning("Please describe what you're looking for.")
        elif not has_ai_configured():
            st.error("No AI key configured.")
        else:
            with st.spinner("Claude is hunting for new prospects..."):
                existing_names = ", ".join(df["name"].dropna().head(30).tolist()) if not df.empty else "none"
                system = """You are a healthcare market intelligence specialist for MedPort, an AI voice agent startup for clinic phone intake.
Generate new prospect suggestions that the team hasn't found yet. Be specific with real institutions."""

                prompt = f"""MedPort is looking for new prospects. Here's what they want:

"{hunter_query.strip()}"

Already in database (don't repeat): {existing_names}

Generate 8 specific new prospect suggestions. For each one:

---
NAME: [Full institution name]
CITY: [City, Province/State, Country]
WHY IT FITS: [2-3 specific reasons this institution needs phone intake AI]
WEBSITE: [Likely website URL to verify — educated guess OK]
DECISION MAKER: [Most likely title of the person who owns this decision]
ESTIMATED SCORE: [X/40 composite — innovation + accessibility + fit + startup receptiveness]
---

Be specific. Name real institutions that actually exist. Prioritize Canadian CHCs, university wellness centres, and niche clinic types competitors aren't covering."""

                try:
                    result, provider = call_ai(system, [{"role": "user", "content": prompt}], max_tokens=2500)
                    st.session_state["hunter_result"] = result
                    st.session_state["hunter_provider"] = provider
                    st.session_state["hunter_query_used"] = hunter_query.strip()
                except Exception as e:
                    st.error(f"AI request failed: {e}")

    if "hunter_result" in st.session_state:
        provider = st.session_state.get("hunter_provider", "Claude")
        query_used = st.session_state.get("hunter_query_used", "")

        st.markdown(f"**Results for:** _{query_used}_")
        if provider != "Claude":
            st.caption(f"Generated by {provider}")

        raw = st.session_state["hunter_result"]
        blocks = [b.strip() for b in raw.split("---") if b.strip()]

        rendered_prospects = []
        for block in blocks:
            lines = block.strip().split("\n")
            card = {}
            for line in lines:
                for key, prefix in [
                    ("name", "NAME:"), ("city", "CITY:"), ("why", "WHY IT FITS:"),
                    ("website", "WEBSITE:"), ("dm", "DECISION MAKER:"), ("score", "ESTIMATED SCORE:"),
                ]:
                    if line.startswith(prefix):
                        card[key] = line.replace(prefix, "").strip()

            if card.get("name"):
                rendered_prospects.append(card)
                col_card, col_btn = st.columns([5, 1])
                with col_card:
                    st.markdown(
                        f"""
                        <div class="intel-card">
                          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;">
                            <div>
                              <div class="intel-card-header">{card.get('name','?')}</div>
                              <div class="intel-card-sub">{card.get('city','')}</div>
                            </div>
                            <span style="background:#f1f5f9;color:#475569;border-radius:6px;padding:2px 9px;font-size:0.75rem;font-weight:700;white-space:nowrap;">{card.get('score','?')}</span>
                          </div>
                          <div style="margin-top:0.55rem;font-size:0.82rem;color:#1e293b;"><strong>Why it fits:</strong> {card.get('why','')}</div>
                          <div style="margin-top:0.35rem;font-size:0.78rem;color:#64748b;">
                            <strong>Decision maker:</strong> {card.get('dm','')} &nbsp;·&nbsp;
                            <strong>Website:</strong> <a href="{card.get('website','#')}" target="_blank" style="color:{MEDPORT_TEAL};">{card.get('website','')}</a>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    if st.button("Add to Pipeline", key=f"add_prospect_{card.get('name','')[:20]}"):
                        # Create a draft prospect in Supabase
                        from lib.db import get_client
                        client = get_client()
                        if client:
                            try:
                                city_parts = card.get("city", "").split(",")
                                country = "CA" if len(city_parts) > 1 and "CA" in city_parts[-1].upper() else "US"
                                city_name = city_parts[0].strip() if city_parts else ""
                                client.table("prospects").insert({
                                    "name": card.get("name", ""),
                                    "city": city_name,
                                    "country": country,
                                    "website": card.get("website", ""),
                                    "status": "not_contacted",
                                    "research_notes": f"Added via Prospect Hunter. Why it fits: {card.get('why', '')}. Likely DM: {card.get('dm', '')}",
                                    "assigned_to": name,
                                    "priority_rank": 2,
                                }).execute()
                                st.success(f"Added {card.get('name','')} to pipeline.")
                                st.cache_data.clear()
                            except Exception as e:
                                st.error(f"Could not add to Supabase: {e}")
                        else:
                            st.warning("Supabase not configured — prospect not saved.")

        if not rendered_prospects:
            st.markdown(raw)

        if st.button("Clear results", key="hunter_clear"):
            for k in ["hunter_result", "hunter_provider", "hunter_query_used"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5: Weekly Outreach Intelligence Report
# ═════════════════════════════════════════════════════════════════════════════

with tab_report:
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.3rem;">Weekly Outreach Intelligence Report</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.82rem;color:#64748b;margin-bottom:1rem;">One-page strategic report: pipeline health, top prospects to focus on, cold prospects to re-engage, and tactical recommendations.</div>',
        unsafe_allow_html=True,
    )

    if st.button("Generate Weekly Report", type="primary", key="do_weekly_report"):
        if df.empty:
            st.warning("No prospects loaded.")
        elif not has_ai_configured():
            st.error("No AI key configured.")
        else:
            with st.spinner("Claude is generating your weekly intelligence report..."):
                # Build pipeline summary
                stage_counts = {}
                for stage in ["not_contacted", "email_sent", "pending_response", "demo_booked", "converted", "declined"]:
                    stage_counts[stage] = int(len(df[df["status"] == stage]))

                top_prospects = df[df["priority_rank"] == 1].sort_values("composite_score", ascending=False).head(10)
                top_text = _df_to_text(top_prospects, max_rows=10)

                # Prospects not contacted recently (approximation: email_sent or pending, high score)
                stale_candidates = df[df["status"].isin(["email_sent", "pending_response"])].sort_values("composite_score", ascending=False).head(10)
                stale_text = _df_to_text(stale_candidates, max_rows=10)

                system = """You are MedPort's Chief of Staff and strategic advisor. Generate a direct, tactical weekly intelligence report.
No fluff. Talk like a sharp startup advisor, not a consultant."""

                prompt = f"""Generate MedPort's weekly outreach intelligence report for the week of {datetime.now().strftime('%B %d, %Y')}.

PIPELINE SNAPSHOT:
{chr(10).join(f"  {k.replace('_',' ').title()}: {v}" for k,v in stage_counts.items())}
Total prospects: {len(df)}

TOP TIER A PROSPECTS (by score):
{top_text}

PROSPECTS IN ACTIVE STAGES (email sent / pending response):
{stale_text}

Known upcoming demos: Flemingdon Health Centre (April 8), McMaster Wellness Centre (TBD).

Generate a 1-page markdown report with these sections:

## Pipeline Health
[2-3 bullet points on current pipeline velocity and stage distribution]

## Top 3 Prospects to Focus on THIS WEEK
[For each: name, specific reason why NOW, exact recommended action]

## 3 Prospects That Have Gone Cold
[Name 3 specific prospects that need re-engagement, suggest a re-engagement tactic for each]

## Competitor Risk This Week
[1-2 sentences on most pressing competitive threat]

## Recommended Team Assignments
[Which team members should own which prospect types this week]

## This Week's One Tactical Recommendation
[One specific, actionable thing the team should do differently this week]

Be direct, specific, and use actual prospect names from the data."""

                try:
                    result, provider = call_ai(system, [{"role": "user", "content": prompt}], max_tokens=2000)
                    st.session_state["weekly_report"] = result
                    st.session_state["weekly_report_provider"] = provider
                    st.session_state["weekly_report_date"] = datetime.now().strftime("%B %d, %Y")
                except Exception as e:
                    st.error(f"Report generation failed: {e}")

    if "weekly_report" in st.session_state:
        provider = st.session_state.get("weekly_report_provider", "Claude")
        report_date = st.session_state.get("weekly_report_date", "")

        st.markdown(f"**Generated:** {report_date}")
        if provider != "Claude":
            st.caption(f"Generated by {provider}")

        st.markdown("---")
        st.markdown(st.session_state["weekly_report"])
        st.markdown("---")

        col_dl, col_clear = st.columns([2, 2])
        with col_dl:
            st.download_button(
                "Download Report (.md)",
                data=st.session_state["weekly_report"],
                file_name=f"medport_weekly_report_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                key="dl_report",
            )
        with col_clear:
            if st.button("Clear report", key="clear_report"):
                for k in ["weekly_report", "weekly_report_provider", "weekly_report_date"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
