"""
MedPort shared styles — brand colors, CSS, and theme constants.
Import inject_css() at the top of every page after set_page_config().
"""

import streamlit as st

# ─── Brand colors ───────────────────────────────────────────────────────────
MEDPORT_BLUE = "#1B4F72"
MEDPORT_GREEN = "#1a8a4a"
MEDPORT_WHITE = "#ffffff"
MEDPORT_LIGHT_GREEN = "#f0f8f4"
MEDPORT_LIGHT_BLUE = "#eaf4fb"

# ─── Card system colors ──────────────────────────────────────────────────────
CARD_GREY = "#9e9e9e"
CARD_YELLOW = "#f39c12"
CARD_RED = "#e74c3c"

# ─── Status pipeline ────────────────────────────────────────────────────────
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

PIPELINE_STAGES = ["not_contacted", "email_sent", "pending_response", "demo_booked", "converted"]

# ─── Team constants ──────────────────────────────────────────────────────────
TEAM_MEMBERS = ["Unassigned", "Arav", "CFO", "Team Member 3", "Team Member 4", "Team Member 5"]

TEAM_EMAILS = {
    "Arav": "aravkekane@gmail.com",
    # Others loaded from TEAM_MEMBER_EMAILS secret at runtime
}

PRIORITY_COLORS = {
    "low": "#6c757d",
    "medium": "#2980b9",
    "high": "#f39c12",
    "urgent": "#e74c3c",
}

TASK_STATUS_COLORS = {
    "open": "#2980b9",
    "in_progress": "#8e44ad",
    "completed": "#1a8a4a",
    "blocked": "#e74c3c",
}


def get_css() -> str:
    return f"""
<style>
/* ── Base ── */
.main .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; }}
h1 {{ color: {MEDPORT_BLUE}; font-weight: 800; letter-spacing: -0.5px; }}
h2, h3 {{ color: {MEDPORT_BLUE}; }}
section[data-testid="stSidebar"] {{ background: {MEDPORT_LIGHT_GREEN}; }}

/* ── Stat cards ── */
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

/* ── Funnel ── */
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

/* ── Score bars ── */
.score-bar-container {{ margin: 2px 0; }}
.score-bar-label {{ font-size: 0.7rem; color: #6b7a8d; display: inline-block; width: 80px; }}
.score-bar-outer {{ display: inline-block; width: 80px; height: 8px; background: #e8eef4; border-radius: 4px; vertical-align: middle; }}
.score-bar-inner {{ height: 8px; border-radius: 4px; }}
.score-bar-val {{ font-size: 0.72rem; font-weight: 700; margin-left: 4px; display: inline-block; }}

/* ── Goal progress bars ── */
.goal-card {{
  background: #fff;
  border: 1px solid #e0e7ef;
  border-radius: 10px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.6rem;
  box-shadow: 0 1px 4px rgba(27,79,114,0.06);
}}
.goal-title {{ font-size: 0.95rem; font-weight: 700; color: {MEDPORT_BLUE}; }}
.goal-meta {{ font-size: 0.74rem; color: #6b7a8d; margin-top: 2px; }}
.goal-progress-outer {{
  width: 100%; height: 10px; background: #e8eef4; border-radius: 5px;
  margin: 0.5rem 0 0.3rem 0; overflow: hidden;
}}
.goal-progress-inner {{ height: 10px; border-radius: 5px; transition: width 0.4s ease; }}
.goal-pct {{ font-size: 0.78rem; font-weight: 700; color: {MEDPORT_BLUE}; }}

/* ── Activity feed ── */
.activity-item {{
  display: flex; align-items: flex-start; gap: 0.6rem;
  padding: 0.55rem 0.75rem; border-radius: 8px;
  background: #fff; border: 1px solid #f0f4f8;
  margin-bottom: 0.4rem;
}}
.activity-avatar {{
  width: 32px; height: 32px; border-radius: 50%;
  background: {MEDPORT_BLUE}; color: #fff;
  font-size: 0.72rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}}
.activity-avatar.green {{ background: {MEDPORT_GREEN}; }}
.activity-avatar.orange {{ background: {CARD_YELLOW}; }}
.activity-avatar.red {{ background: {CARD_RED}; }}
.activity-dot {{
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; margin-top: 4px;
}}
.activity-text {{ font-size: 0.82rem; color: #1a2a3a; line-height: 1.4; }}
.activity-time {{ font-size: 0.72rem; color: #8a9ab0; margin-top: 1px; }}

/* ── Task cards ── */
.task-card {{
  background: #fff;
  border: 1px solid #e0e7ef;
  border-left: 4px solid {MEDPORT_BLUE};
  border-radius: 8px;
  padding: 0.7rem 0.9rem;
  margin-bottom: 0.5rem;
  box-shadow: 0 1px 4px rgba(27,79,114,0.05);
}}
.task-title {{ font-size: 0.88rem; font-weight: 700; color: #1a2a3a; }}
.task-meta {{ font-size: 0.73rem; color: #6b7a8d; margin-top: 3px; }}
.task-overdue {{ color: #e74c3c; font-weight: 700; }}
.task-due-soon {{ color: #f39c12; font-weight: 600; }}

/* ── Priority badges ── */
.badge-priority-low {{ background: #f0f4f8; color: #6c757d; padding: 2px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }}
.badge-priority-medium {{ background: #eaf4fb; color: #2980b9; padding: 2px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }}
.badge-priority-high {{ background: #fff3cd; color: #856404; padding: 2px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }}
.badge-priority-urgent {{ background: #f8d7da; color: #721c24; padding: 2px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; }}

/* ── Task status badges ── */
.badge-status-open {{ background: #eaf4fb; color: #2980b9; padding: 2px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }}
.badge-status-in_progress {{ background: #f3e9fd; color: #8e44ad; padding: 2px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }}
.badge-status-completed {{ background: #d4edda; color: #155724; padding: 2px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }}
.badge-status-blocked {{ background: #f8d7da; color: #721c24; padding: 2px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }}

/* ── Card badges (disciplinary) ── */
.card-grey {{ background: #e0e0e0; color: #424242; padding: 3px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 700; }}
.card-yellow {{ background: #fff3cd; color: #856404; padding: 3px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 700; border: 1px solid #f39c12; }}
.card-red {{ background: #f8d7da; color: #721c24; padding: 3px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 700; border: 1px solid #e74c3c; }}

/* ── Standing status badges ── */
.standing-good {{ background: #d4edda; color: #155724; padding: 3px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }}
.standing-grey {{ background: #e0e0e0; color: #424242; padding: 3px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }}
.standing-yellow {{ background: #fff3cd; color: #856404; padding: 3px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }}
.standing-review {{ background: #f8d7da; color: #721c24; padding: 3px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }}
.standing-removed {{ background: #721c24; color: #fff; padding: 3px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }}

/* ── Member card (team overview) ── */
.member-card {{
  background: #fff;
  border: 1px solid #e0e7ef;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  text-align: center;
  box-shadow: 0 2px 8px rgba(27,79,114,0.06);
}}
.member-avatar {{
  width: 44px; height: 44px; border-radius: 50%;
  background: linear-gradient(135deg, {MEDPORT_BLUE}, {MEDPORT_GREEN});
  color: #fff; font-size: 1rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 0.4rem auto;
}}
.member-name {{ font-size: 0.9rem; font-weight: 700; color: {MEDPORT_BLUE}; }}
.member-stat {{ font-size: 0.74rem; color: #6b7a8d; }}

/* ── Prospect card helpers (from original) ── */
.queue-badge {{
  background: #fff3cd; color: #856404;
  border: 1px solid #ffc107;
  padding: 3px 10px; border-radius: 20px;
  font-size: 0.8rem; font-weight: 700; display: inline-block;
}}
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

/* ── Chat UI ── */
.chat-msg-user {{
  background: {MEDPORT_LIGHT_BLUE}; border-radius: 12px 12px 4px 12px;
  padding: 0.65rem 0.9rem; margin: 0.3rem 0; font-size: 0.88rem;
  max-width: 85%; margin-left: auto;
}}
.chat-msg-assistant {{
  background: {MEDPORT_LIGHT_GREEN}; border-radius: 12px 12px 12px 4px;
  padding: 0.65rem 0.9rem; margin: 0.3rem 0; font-size: 0.88rem;
  max-width: 90%;
}}

/* ── Saved search pill ── */
.saved-search-pill {{
  background: {MEDPORT_LIGHT_BLUE}; color: {MEDPORT_BLUE};
  border: 1px solid #b8d4e8; border-radius: 20px;
  padding: 3px 12px; font-size: 0.78rem; font-weight: 600;
  display: inline-block; cursor: pointer; margin: 2px;
}}
</style>
"""


def inject_css():
    """Call this on every page after st.set_page_config()."""
    st.markdown(get_css(), unsafe_allow_html=True)
