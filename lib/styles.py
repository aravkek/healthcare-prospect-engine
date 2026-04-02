"""
MedPort shared styles — brand colors, CSS, and theme constants.
Import inject_css() at the top of every page after set_page_config().
"""

import streamlit as st

# ─── Brand colors ───────────────────────────────────────────────────────────
MEDPORT_TEAL = "#00B89F"
MEDPORT_BLUE = "#3B7EFF"
MEDPORT_DARK = "#0F172A"
MEDPORT_DARK_CARD = "#1E293B"
MEDPORT_WHITE = "#FFFFFF"
MEDPORT_BG = "#f0fdfb"
MEDPORT_LIGHT_TEAL = "#e6faf8"
MEDPORT_LIGHT_BLUE = "#eff6ff"

# Backward compat — old references won't break
MEDPORT_GREEN = MEDPORT_TEAL
MEDPORT_LIGHT_GREEN = MEDPORT_LIGHT_TEAL

# ─── Card system colors ──────────────────────────────────────────────────────
CARD_GREY = "#94a3b8"
CARD_YELLOW = "#f59e0b"
CARD_RED = "#ef4444"

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
    "not_contacted": "#64748b",
    "email_sent": "#3B7EFF",
    "pending_response": "#f59e0b",
    "demo_booked": "#8b5cf6",
    "converted": "#00B89F",
    "declined": "#ef4444",
}

PIPELINE_STAGES = ["not_contacted", "email_sent", "pending_response", "demo_booked", "converted"]

# ─── Team constants ──────────────────────────────────────────────────────────
TEAM_MEMBERS = ["Unassigned", "Arav", "CFO", "Team Member 3", "Team Member 4", "Team Member 5"]

TEAM_EMAILS = {
    "Arav": "aravkekane@gmail.com",
    # Others loaded from TEAM_MEMBER_EMAILS secret at runtime
}

PRIORITY_COLORS = {
    "low": "#64748b",
    "medium": "#3B7EFF",
    "high": "#f59e0b",
    "urgent": "#ef4444",
}

TASK_STATUS_COLORS = {
    "open": "#3B7EFF",
    "in_progress": "#8b5cf6",
    "completed": "#00B89F",
    "blocked": "#ef4444",
}


def page_header(title: str, subtitle: str = "") -> str:
    """Returns HTML for a consistent page header — dark, heavy weight, no gradient text."""
    subtitle_html = (
        f'<div class="page-subtitle">{subtitle}</div>'
        if subtitle else ""
    )
    return f"""
<div style="margin-bottom:1.5rem;">
  <div class="page-title">{title}</div>
  {subtitle_html}
</div>
"""


def get_css() -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');

/* ── Type scale ──────────────────────────────────────
   xs   : 0.75rem  → labels, badges, tiny metadata
   sm   : 0.8125rem → secondary text, timestamps
   base : 0.9375rem → body, descriptions
   md   : 1rem      → card titles, sidebar items
   lg   : 1.125rem  → section subheadings
   xl   : 1.5rem    → page section titles (h3)
   2xl  : 1.875rem  → page headers
──────────────────────────────────────────────────── */

/* ── Base ── */
html, body {{ font-size: 16px; }}
html, body, [class*="css"] {{ font-family: 'DM Sans', system-ui, sans-serif; }}
p, li, span, div {{ line-height: 1.55; }}
h1, h2, h3 {{ font-family: 'Plus Jakarta Sans', 'DM Sans', sans-serif; font-weight: 700; color: {MEDPORT_DARK}; line-height: 1.2; }}
.main .block-container {{ padding-top: 1.75rem; padding-bottom: 2.5rem; max-width: 1200px; }}
.main {{ background: #f8fafc; }}

/* Streamlit default text — make it readable */
.stMarkdown p {{ font-size: 0.9375rem; color: #334155; }}
.stMarkdown h1 {{ font-size: 1.875rem; margin-bottom: 0.5rem; }}
.stMarkdown h2 {{ font-size: 1.5rem; margin-bottom: 0.4rem; }}
.stMarkdown h3 {{ font-size: 1.125rem; margin-bottom: 0.3rem; }}
label[data-testid="stWidgetLabel"] > div > p {{ font-size: 0.875rem !important; font-weight: 500; color: #475569; }}
.stTextInput input, .stTextArea textarea, .stSelectbox div {{ font-size: 0.9375rem !important; }}
.stTabs [data-baseweb="tab"] {{ font-size: 0.875rem; font-weight: 600; }}
.stAlert p {{ font-size: 0.875rem; }}

/* ── Sidebar — dark theme ── */
section[data-testid="stSidebar"] {{
  background: #0F172A;
  color: white;
  border-right: 1px solid rgba(255,255,255,0.06);
}}
section[data-testid="stSidebar"] * {{ color: white; }}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span,
section[data-testid="stSidebar"] label {{
  color: #cbd5e1;
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
  color: white;
}}
section[data-testid="stSidebar"] hr {{
  border-color: #334155;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
  color: #94a3b8;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
  color: {MEDPORT_TEAL};
  background: rgba(0,184,159,0.08);
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {{
  color: {MEDPORT_TEAL};
  background: rgba(0,184,159,0.1);
  font-weight: 600;
}}
section[data-testid="stSidebar"] button {{
  color: white;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
}}
section[data-testid="stSidebar"] button:hover {{
  background: rgba(0,184,159,0.15);
  border-color: {MEDPORT_TEAL};
}}
section[data-testid="stSidebar"] .stToggle label {{
  color: #94a3b8;
}}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {{
  background: #1e293b;
  border-color: #334155;
  color: white;
}}
section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div {{
  background: #1e293b;
  border-color: #334155;
  color: white;
}}
section[data-testid="stSidebar"] .stSlider label {{
  color: #94a3b8;
}}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{
  color: #94a3b8;
  border-radius: 8px;
  transition: all 0.2s;
  padding: 4px 8px;
}}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {{
  color: {MEDPORT_TEAL};
  background: rgba(0,184,159,0.1);
}}

/* ── Page headers — clean, no gradient ── */
.page-title {{
  font-size: 1.875rem;
  font-weight: 700;
  color: #0F172A;
  font-family: 'Plus Jakarta Sans', sans-serif;
  letter-spacing: -0.02em;
  margin-bottom: 0.35rem;
  line-height: 1.2;
}}
.page-subtitle {{
  font-size: 0.9375rem;
  color: #64748b;
  font-weight: 400;
}}

/* ── Hide Streamlit chrome ── */
footer {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stToolbar"] {{ visibility: hidden !important; }}
/* Sidebar toggle must always be visible */
[data-testid="stSidebarCollapsedControl"] {{ display: flex !important; visibility: visible !important; opacity: 1 !important; }}

/* ── Badge base class ── */
.mp-badge {{
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 9px;
  display: inline-block;
}}

/* ── Stat cards — Wealthsimple style ── */
.stat-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.5rem 1.75rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 0 0 1px rgba(0,0,0,0.02);
  transition: box-shadow 0.2s ease;
}}
.stat-card:hover {{
  box-shadow: 0 4px 12px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.02);
}}
.stat-card .stat-value {{
  font-size: 2.5rem;
  font-weight: 700;
  line-height: 1.1;
  color: #0F172A;
  font-family: 'Plus Jakarta Sans', sans-serif;
  letter-spacing: -0.02em;
}}
.stat-card .stat-label {{
  font-size: 0.75rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 0.5rem;
  font-weight: 600;
}}

/* ── Funnel ── */
.funnel-row {{ display: flex; gap: 0; flex-wrap: nowrap; margin-bottom: 1rem; overflow-x: auto; border-radius: 10px; overflow: hidden; }}
.funnel-step {{
  flex: 1; min-width: 100px; padding: 0.75rem 0.5rem;
  text-align: center; font-size: 0.8125rem; font-weight: 600; color: #fff;
  position: relative;
}}
.funnel-step .funnel-count {{ font-size: 1.625rem; font-weight: 700; display: block; line-height: 1; font-family: 'Plus Jakarta Sans', sans-serif; }}
.funnel-step .funnel-label {{ font-size: 0.75rem; opacity: 0.9; margin-top: 4px; display: block; }}
.funnel-step:not(:last-child)::after {{
  content: '›'; position: absolute; right: -6px; top: 50%; transform: translateY(-50%);
  font-size: 1.2rem; color: rgba(255,255,255,0.5); z-index: 10;
}}

/* ── Score bars — single teal, no gradient ── */
.score-bar-container {{ margin: 4px 0; }}
.score-bar-label {{ font-size: 0.75rem; color: #64748b; display: inline-block; width: 90px; font-weight: 500; }}
.score-bar-outer {{ display: inline-block; width: 90px; height: 8px; background: #e2e8f0; border-radius: 4px; vertical-align: middle; }}
.score-bar-inner {{ height: 8px; border-radius: 4px; background: {MEDPORT_TEAL}; }}
.score-bar-val {{ font-size: 0.75rem; font-weight: 700; margin-left: 6px; display: inline-block; color: {MEDPORT_DARK}; }}

/* ── Goal progress bars ── */
.goal-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin-bottom: 0.75rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}}
.goal-title {{ font-size: 1rem; font-weight: 700; color: {MEDPORT_DARK}; font-family: 'Plus Jakarta Sans', sans-serif; }}
.goal-meta {{ font-size: 0.8125rem; color: #64748b; margin-top: 4px; }}
.goal-progress-outer {{
  width: 100%; height: 8px; background: #e2e8f0; border-radius: 4px;
  margin: 0.6rem 0 0.4rem 0; overflow: hidden;
}}
.goal-progress-inner {{
  height: 8px; border-radius: 4px;
  background: {MEDPORT_TEAL};
  transition: width 0.5s ease;
}}
.goal-pct {{ font-size: 0.8125rem; font-weight: 700; color: {MEDPORT_TEAL}; }}

/* ── Activity feed ── */
.activity-item {{
  display: flex; align-items: flex-start; gap: 0.75rem;
  padding: 0.75rem 1rem; border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left: 3px solid transparent;
  margin-bottom: 0.4rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  transition: border-left-color 0.15s ease;
}}
.activity-item:hover {{
  border-left-color: {MEDPORT_TEAL};
}}
.activity-avatar {{
  width: 32px; height: 32px; border-radius: 50%;
  background: {MEDPORT_DARK};
  color: #fff;
  font-size: 0.75rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}}
.activity-avatar.green {{ background: #059669; }}
.activity-avatar.orange {{ background: {CARD_YELLOW}; }}
.activity-avatar.red {{ background: {CARD_RED}; }}
.activity-dot {{
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; margin-top: 5px;
}}
.activity-text {{ font-size: 0.875rem; color: #1e293b; line-height: 1.45; }}
.activity-time {{ font-size: 0.75rem; color: #94a3b8; margin-top: 3px; }}

/* ── Task cards ── */
.task-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left: 3px solid {MEDPORT_TEAL};
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin-bottom: 0.5rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  transition: box-shadow 0.2s;
}}
.task-card:hover {{
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}}
.task-title {{ font-size: 0.9375rem; font-weight: 700; color: {MEDPORT_DARK}; }}
.task-meta {{ font-size: 0.8125rem; color: #64748b; margin-top: 5px; }}
.task-overdue {{ color: {CARD_RED}; font-weight: 700; }}
.task-due-soon {{ color: {CARD_YELLOW}; font-weight: 600; }}

/* ── Priority badges — pill, muted bg, colored text ── */
.badge-priority-low {{ background: #f1f5f9; color: #64748b; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
.badge-priority-medium {{ background: #eff6ff; color: {MEDPORT_BLUE}; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
.badge-priority-high {{ background: #fffbeb; color: #92400e; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
.badge-priority-urgent {{ background: #fef2f2; color: #991b1b; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }}

/* ── Task status badges ── */
.badge-status-open {{ background: #eff6ff; color: {MEDPORT_BLUE}; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
.badge-status-in_progress {{ background: #f5f3ff; color: #6d28d9; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
.badge-status-completed {{ background: #f0fdf9; color: #065f46; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
.badge-status-blocked {{ background: #fef2f2; color: #991b1b; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}

/* ── Card badges (disciplinary) ── */
.card-grey {{ background: #f1f5f9; color: #475569; padding: 3px 10px; border-radius: 6px; font-size: 0.8125rem; font-weight: 600; }}
.card-yellow {{ background: #fffbeb; color: #92400e; padding: 3px 10px; border-radius: 6px; font-size: 0.8125rem; font-weight: 600; border: 1px solid {CARD_YELLOW}; }}
.card-red {{ background: #fef2f2; color: #991b1b; padding: 3px 10px; border-radius: 6px; font-size: 0.8125rem; font-weight: 600; border: 1px solid {CARD_RED}; }}

/* ── Standing status badges ── */
.standing-good {{ background: #f0fdf9; color: #065f46; padding: 3px 11px; border-radius: 999px; font-size: 0.8125rem; font-weight: 600; }}
.standing-grey {{ background: #f1f5f9; color: #475569; padding: 3px 11px; border-radius: 999px; font-size: 0.8125rem; font-weight: 600; }}
.standing-yellow {{ background: #fffbeb; color: #92400e; padding: 3px 11px; border-radius: 999px; font-size: 0.8125rem; font-weight: 600; }}
.standing-review {{ background: #fef2f2; color: #991b1b; padding: 3px 11px; border-radius: 999px; font-size: 0.8125rem; font-weight: 600; }}
.standing-removed {{ background: #991b1b; color: #fff; padding: 3px 11px; border-radius: 999px; font-size: 0.8125rem; font-weight: 600; }}

/* ── Member card — vertical, centered (for narrow columns) ── */
.member-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.25rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.5rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease;
}}
.member-card:hover {{
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}}
.member-avatar {{
  width: 48px; height: 48px; border-radius: 50%;
  font-size: 1rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}}
.member-name {{ font-size: 0.9375rem; font-weight: 700; color: #0F172A; font-family: 'Plus Jakarta Sans', sans-serif; }}
.member-role {{ font-size: 0.8125rem; color: #64748b; font-weight: 500; }}
.member-stat {{ font-size: 0.75rem; color: #94a3b8; margin-top: 3px; }}

/* ── Primary buttons — clean dark ── */
.stButton > button[kind="primary"] {{
  background: #0F172A;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 0.5rem 1.5rem;
  font-weight: 600;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
  transition: all 0.15s ease;
}}
.stButton > button[kind="primary"]:hover {{
  background: #1e293b;
  box-shadow: 0 4px 12px rgba(15,23,42,0.2);
}}

/* ── Prospect card helpers ── */
.queue-badge {{
  background: #fffbeb; color: #92400e;
  border: 1px solid {CARD_YELLOW};
  padding: 2px 9px; border-radius: 6px;
  font-size: 0.8125rem; font-weight: 600; display: inline-block;
}}
.inst-header {{ font-size: 1.0625rem; font-weight: 700; color: {MEDPORT_DARK}; font-family: 'Plus Jakarta Sans', sans-serif; }}
.inst-meta {{ font-size: 0.8125rem; color: #64748b; margin-top: 0.2rem; }}
.score-green  {{ background:#f0fdf9; color:#065f46; padding:2px 9px; border-radius:6px; font-weight:600; font-size:0.8125rem; }}
.score-yellow {{ background:#fffbeb; color:#92400e; padding:2px 9px; border-radius:6px; font-weight:600; font-size:0.8125rem; }}
.score-red    {{ background:#fef2f2; color:#991b1b; padding:2px 9px; border-radius:6px; font-weight:600; font-size:0.8125rem; }}
.risk-none   {{ background:#f0fdf9; color:#065f46; padding:2px 8px; border-radius:6px; font-size:0.75rem; font-weight:600; }}
.risk-low    {{ background:#eff6ff; color:#1e40af; padding:2px 8px; border-radius:6px; font-size:0.75rem; font-weight:600; }}
.risk-medium {{ background:#fffbeb; color:#92400e; padding:2px 8px; border-radius:6px; font-size:0.75rem; font-weight:600; }}
.risk-high   {{ background:#fef2f2; color:#991b1b; padding:2px 8px; border-radius:6px; font-size:0.75rem; font-weight:600; }}
.type-badge {{
  background: rgba(0,184,159,0.1); color: {MEDPORT_TEAL};
  padding: 2px 9px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
}}
.tier-a {{ background: linear-gradient(135deg,{MEDPORT_TEAL},{MEDPORT_BLUE}); color:#fff; padding:3px 10px; border-radius:6px; font-size:0.8125rem; font-weight:700; }}
.tier-b {{ background: {MEDPORT_BLUE}; color:#fff; padding:3px 10px; border-radius:6px; font-size:0.8125rem; font-weight:700; }}
.tier-c {{ background: #94a3b8; color:#fff; padding:3px 10px; border-radius:6px; font-size:0.8125rem; font-weight:700; }}
.status-badge {{ display:inline-block; padding:3px 9px; border-radius:6px; font-size:0.75rem; font-weight:600; color:#fff; }}
.outreach-box {{
  background: #f8fafc;
  border-radius: 6px; padding: 0.75rem 1rem;
  font-size: 0.9375rem; color: {MEDPORT_DARK}; margin-top: 0.5rem;
  border: 1px solid #e2e8f0; border-left: 3px solid {MEDPORT_TEAL};
}}
.info-pill {{
  background: #f8fafc; color: #475569;
  border-radius: 6px; padding: 3px 10px; font-size: 0.8125rem;
  display: inline-block; margin: 2px 3px 2px 0;
  border: 1px solid #e2e8f0;
}}
.info-pill b {{ color: {MEDPORT_TEAL}; }}
.alert-box {{
  background: #fffbeb; border-left: 3px solid {CARD_YELLOW};
  border-radius: 8px; padding: 0.875rem 1.1rem;
  font-size: 0.9375rem; color: #78350f;
}}
hr.subtle {{ border: none; border-top: 1px solid #e2e8f0; margin: 0.5rem 0; }}

/* ── Chat UI — clean bubbles ── */
.chat-msg-user {{
  background: {MEDPORT_TEAL}; color: #fff;
  border-radius: 14px 14px 4px 14px;
  padding: 0.75rem 1.1rem; margin: 0.35rem 0; font-size: 0.9375rem;
  max-width: 82%; margin-left: auto;
}}
.chat-msg-assistant {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px 14px 14px 4px;
  padding: 0.75rem 1.1rem; margin: 0.35rem 0; font-size: 0.9375rem;
  max-width: 88%; color: {MEDPORT_DARK};
}}

/* ── Prospect table ── */
.mp-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  color: {MEDPORT_DARK};
}}
.mp-table th {{
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 0.6rem 0.85rem;
  text-align: left;
  font-weight: 700;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #64748b;
}}
.mp-table td {{
  padding: 0.6rem 0.85rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}}
.mp-table tr:hover td {{
  background: #f8fafc;
}}

/* ── Saved search pill ── */
.saved-search-pill {{
  background: #f8fafc; color: #475569;
  border: 1px solid #e2e8f0; border-radius: 6px;
  padding: 4px 11px; font-size: 0.8125rem; font-weight: 600;
  display: inline-block; cursor: pointer; margin: 2px;
}}

/* ── Intelligence page ── */
.intel-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.1rem 1.3rem;
  margin-bottom: 0.75rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
.intel-card-header {{
  font-size: 1rem;
  font-weight: 700;
  color: {MEDPORT_DARK};
  font-family: 'Plus Jakarta Sans', sans-serif;
}}
.intel-card-sub {{
  font-size: 0.8125rem;
  color: #64748b;
  margin-top: 3px;
}}
.threat-high {{ background: #fef2f2; color: #991b1b; padding: 2px 9px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; }}
.threat-medium {{ background: #fffbeb; color: #92400e; padding: 2px 9px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
.threat-low {{ background: #f0fdf9; color: #065f46; padding: 2px 9px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}

/* ── Settings member card ── */
.settings-member-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem 1.2rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s;
}}
.settings-member-card:hover {{
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}}

/* ── Filter status bar ── */
.filter-bar {{
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.55rem 1rem;
  font-size: 0.875rem;
  color: #475569;
  margin-bottom: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}}
.filter-tag {{
  background: rgba(0,184,159,0.08);
  color: {MEDPORT_TEAL};
  border: 1px solid rgba(0,184,159,0.2);
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 0.8125rem;
  font-weight: 600;
  display: inline-block;
}}
</style>
"""


def inject_css():
    """Call this on every page after st.set_page_config()."""
    st.markdown(get_css(), unsafe_allow_html=True)
