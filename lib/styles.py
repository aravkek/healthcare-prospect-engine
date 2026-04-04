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

# ─── Department colors ───────────────────────────────────────────────────────
DEPT_COLORS = {
    "leadership": "#00B89F",   # teal
    "marketing":  "#3B82F6",   # blue
    "finance":    "#10B981",   # emerald
    "tech":       "#8B5CF6",   # purple
    "operations": "#F59E0B",   # amber
    "unassigned": "#94a3b8",   # slate
}

DEPT_LABELS = {
    "leadership": "Leadership",
    "marketing":  "Marketing",
    "finance":    "Finance",
    "tech":       "Tech",
    "operations": "Operations",
    "unassigned": "Unassigned",
}

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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

/* ─────────────────────────────────────────────────────────────────
   MEDPORT DESIGN SYSTEM v2 — inspired by 21st.dev, Linear, Vercel
   Type scale:
   xs   0.75rem   labels, badges, timestamps
   sm   0.8125rem secondary text
   base 0.9375rem body copy
   md   1rem      card titles
   lg   1.125rem  section headings
   xl   1.5rem    page section titles
   2xl  1.875rem  page headers
───────────────────────────────────────────────────────────────── */

/* ── CSS custom properties ── */
:root {{
  --mp-teal:       {MEDPORT_TEAL};
  --mp-blue:       #3B7EFF;
  --mp-dark:       #0F172A;
  --mp-dark-2:     #1E293B;
  --mp-border:     rgba(0,0,0,0.08);
  --mp-border-2:   #e2e8f0;
  --mp-bg:         #f4f6f9;
  --mp-white:      #ffffff;
  --mp-shadow-sm:  0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
  --mp-shadow-md:  0 4px 16px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.05);
  --mp-shadow-lg:  0 12px 32px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06);
  --mp-radius-sm:  8px;
  --mp-radius-md:  14px;
  --mp-radius-lg:  20px;
  --mp-grad:       linear-gradient(135deg, {MEDPORT_TEAL} 0%, #3B7EFF 100%);
  --mp-grad-soft:  linear-gradient(135deg, rgba(0,184,159,0.12) 0%, rgba(59,126,255,0.12) 100%);
  --transition:    all 0.18s cubic-bezier(0.4,0,0.2,1);
}}

/* ── Base reset ── */
html, body {{ font-size: 16px; -webkit-font-smoothing: antialiased; }}
html, body, [class*="css"] {{ font-family: 'Inter', 'Plus Jakarta Sans', system-ui, sans-serif; }}
p, li, span, div {{ line-height: 1.6; }}
h1, h2, h3, h4 {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; color: var(--mp-dark); line-height: 1.2; letter-spacing: -0.02em; }}
.main .block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1240px; }}
.main {{ background: var(--mp-bg); }}

/* ── Streamlit typography ── */
.stMarkdown p {{ font-size: 0.9375rem; color: #334155; line-height: 1.65; }}
.stMarkdown h1 {{ font-size: 1.875rem; margin-bottom: 0.5rem; letter-spacing: -0.025em; }}
.stMarkdown h2 {{ font-size: 1.5rem; margin-bottom: 0.4rem; letter-spacing: -0.02em; }}
.stMarkdown h3 {{ font-size: 1.125rem; margin-bottom: 0.3rem; letter-spacing: -0.015em; }}
label[data-testid="stWidgetLabel"] > div > p {{ font-size: 0.8125rem !important; font-weight: 600; color: #475569; letter-spacing: 0.01em; }}

/* ── Inputs — clean modern ── */
.stTextInput input, .stTextArea textarea {{
  background: #ffffff !important;
  border: 1.5px solid #e2e8f0 !important;
  border-radius: var(--mp-radius-sm) !important;
  font-size: 0.9375rem !important;
  font-family: 'Inter', sans-serif !important;
  color: var(--mp-dark) !important;
  padding: 0.5rem 0.8rem !important;
  transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
  border-color: var(--mp-teal) !important;
  box-shadow: 0 0 0 3px rgba(0,184,159,0.12) !important;
  outline: none !important;
}}
.stSelectbox div[data-baseweb="select"] > div {{
  background: #ffffff !important;
  border: 1.5px solid #e2e8f0 !important;
  border-radius: var(--mp-radius-sm) !important;
  font-size: 0.9375rem !important;
  transition: border-color 0.15s ease !important;
}}
.stSelectbox div[data-baseweb="select"]:focus-within > div {{
  border-color: var(--mp-teal) !important;
  box-shadow: 0 0 0 3px rgba(0,184,159,0.12) !important;
}}

/* ── Tabs — clean underline style ── */
.stTabs [data-baseweb="tab-list"] {{
  background: transparent !important;
  border-bottom: 2px solid #e2e8f0;
  gap: 0;
  padding: 0;
}}
.stTabs [data-baseweb="tab"] {{
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  color: #64748b !important;
  padding: 0.6rem 1.1rem !important;
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  margin-bottom: -2px !important;
  transition: color 0.15s ease, border-color 0.15s ease !important;
}}
.stTabs [aria-selected="true"][data-baseweb="tab"] {{
  color: var(--mp-teal) !important;
  border-bottom-color: var(--mp-teal) !important;
  background: transparent !important;
}}
.stTabs [data-baseweb="tab"]:hover {{
  color: var(--mp-dark) !important;
}}
.stTabs [data-baseweb="tab-panel"] {{
  padding-top: 1.25rem !important;
}}

.stAlert p {{ font-size: 0.875rem; }}

/* ── Sidebar — refined dark ── */
section[data-testid="stSidebar"] {{
  background: #0B1120;
  color: white;
  border-right: 1px solid rgba(255,255,255,0.05);
}}
section[data-testid="stSidebar"] * {{ color: white; }}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span,
section[data-testid="stSidebar"] label {{
  color: #94a3b8;
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
  color: #f1f5f9;
  letter-spacing: -0.02em;
}}
section[data-testid="stSidebar"] hr {{
  border: none;
  border-top: 1px solid rgba(255,255,255,0.07);
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
  color: #64748b;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 0.875rem;
  font-weight: 500;
  transition: var(--transition);
  display: flex;
  align-items: center;
  gap: 8px;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
  color: #e2e8f0;
  background: rgba(255,255,255,0.06);
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {{
  color: {MEDPORT_TEAL};
  background: rgba(0,184,159,0.12);
  font-weight: 600;
  border-left: 2px solid {MEDPORT_TEAL};
}}
section[data-testid="stSidebar"] button {{
  color: #cbd5e1 !important;
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 10px !important;
  font-size: 0.875rem !important;
  transition: var(--transition) !important;
}}
section[data-testid="stSidebar"] button:hover {{
  background: rgba(0,184,159,0.15) !important;
  border-color: rgba(0,184,159,0.4) !important;
  color: {MEDPORT_TEAL} !important;
}}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {{
  background: rgba(255,255,255,0.05) !important;
  border-color: rgba(255,255,255,0.1) !important;
  color: #e2e8f0 !important;
  border-radius: 10px !important;
}}
section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div {{
  background: rgba(255,255,255,0.05) !important;
  border-color: rgba(255,255,255,0.1) !important;
  border-radius: 10px !important;
}}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{
  color: #64748b;
  border-radius: 10px;
  transition: var(--transition);
  padding: 6px 10px;
  font-size: 0.875rem;
}}
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {{
  color: #e2e8f0;
  background: rgba(255,255,255,0.06);
}}

/* ── Page headers ── */
.page-title {{
  font-size: 2rem;
  font-weight: 800;
  color: #0F172A;
  font-family: 'Plus Jakarta Sans', sans-serif;
  letter-spacing: -0.03em;
  margin-bottom: 0.35rem;
  line-height: 1.15;
  background: linear-gradient(135deg, #0F172A 40%, #334155 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.page-subtitle {{
  font-size: 0.9375rem;
  color: #64748b;
  font-weight: 400;
  line-height: 1.6;
}}

/* ── Hide ALL Streamlit chrome — manage app, footer, toolbar, badges ── */
footer {{ visibility: hidden !important; display: none !important; }}
footer * {{ visibility: hidden !important; display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stToolbarActions"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
[data-testid="manage-app-button"] {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
.viewerBadge_container__1QSob {{ display: none !important; }}
.styles_viewerBadge__1yB5_ {{ display: none !important; }}
/* Streamlit Cloud "Manage app" bottom-right pill */
[class*="toolbar"] {{ display: none !important; }}
div[class*="reportview"] div[class*="StatusWidget"] {{ display: none !important; }}

/* Keep sidebar collapse button always visible */
[data-testid="stSidebarCollapsedControl"] {{ display: flex !important; visibility: visible !important; opacity: 1 !important; }}
/* Remove Streamlit top padding gap */
[data-testid="stAppViewContainer"] > section:first-child {{ padding-top: 0 !important; }}

/* ── Badge base class ── */
.mp-badge {{
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 9px;
  display: inline-block;
}}

/* ── Stat cards — 21st.dev style with gradient accent ── */
.stat-card {{
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: var(--mp-radius-lg);
  padding: 1.5rem 1.75rem;
  box-shadow: var(--mp-shadow-md);
  transition: var(--transition);
  position: relative;
  overflow: hidden;
}}
.stat-card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--mp-grad);
  border-radius: var(--mp-radius-lg) var(--mp-radius-lg) 0 0;
}}
.stat-card::after {{
  content: '';
  position: absolute;
  bottom: 0; right: 0;
  width: 80px; height: 80px;
  background: var(--mp-grad-soft);
  border-radius: 50%;
  transform: translate(30%, 30%);
  pointer-events: none;
}}
.stat-card:hover {{
  transform: translateY(-2px);
  box-shadow: var(--mp-shadow-lg);
  border-color: rgba(0,184,159,0.2);
}}
.stat-card .stat-value {{
  font-size: 2.625rem;
  font-weight: 800;
  line-height: 1.05;
  color: #0F172A;
  font-family: 'Plus Jakarta Sans', sans-serif;
  letter-spacing: -0.04em;
}}
.stat-card .stat-label {{
  font-size: 0.75rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 0.6rem;
  font-weight: 700;
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
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: var(--mp-radius-md);
  padding: 1.125rem 1.375rem;
  margin-bottom: 0.75rem;
  box-shadow: var(--mp-shadow-sm);
  transition: var(--transition);
}}
.goal-card:hover {{
  box-shadow: var(--mp-shadow-md);
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
  display: flex; align-items: flex-start; gap: 0.875rem;
  padding: 0.875rem 1.125rem; border-radius: var(--mp-radius-md);
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.06);
  border-left: 3px solid transparent;
  margin-bottom: 0.4rem;
  box-shadow: var(--mp-shadow-sm);
  transition: var(--transition);
}}
.activity-item:hover {{
  border-left-color: {MEDPORT_TEAL};
  box-shadow: var(--mp-shadow-md);
  transform: translateX(2px);
}}
.activity-avatar {{
  width: 34px; height: 34px; border-radius: 50%;
  background: {MEDPORT_DARK};
  color: #fff;
  font-size: 0.75rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
  letter-spacing: -0.02em;
}}
.activity-avatar.green {{ background: linear-gradient(135deg, #059669, #10b981); }}
.activity-avatar.orange {{ background: linear-gradient(135deg, {CARD_YELLOW}, #f97316); }}
.activity-avatar.red {{ background: linear-gradient(135deg, {CARD_RED}, #dc2626); }}
.activity-dot {{
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; margin-top: 5px;
}}
.activity-text {{ font-size: 0.875rem; color: #1e293b; line-height: 1.5; }}
.activity-time {{ font-size: 0.75rem; color: #94a3b8; margin-top: 3px; }}

/* ── Task cards ── */
.task-card {{
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.07);
  border-left: 3px solid {MEDPORT_TEAL};
  border-radius: var(--mp-radius-md);
  padding: 1rem 1.25rem;
  margin-bottom: 0.5rem;
  box-shadow: var(--mp-shadow-sm);
  transition: var(--transition);
}}
.task-card:hover {{
  box-shadow: var(--mp-shadow-md);
  transform: translateX(2px);
  border-left-color: #3B7EFF;
}}
.task-title {{ font-size: 0.9375rem; font-weight: 700; color: {MEDPORT_DARK}; letter-spacing: -0.01em; }}
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

/* ── Member card ── */
.member-card {{
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: var(--mp-radius-lg);
  padding: 1.5rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.5rem;
  box-shadow: var(--mp-shadow-sm);
  transition: var(--transition);
  position: relative;
  overflow: hidden;
}}
.member-card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--mp-grad);
  opacity: 0;
  transition: opacity 0.18s ease;
}}
.member-card:hover {{
  box-shadow: var(--mp-shadow-md);
  transform: translateY(-2px);
}}
.member-card:hover::before {{
  opacity: 1;
}}
.member-avatar {{
  width: 52px; height: 52px; border-radius: 50%;
  font-size: 1.05rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  letter-spacing: -0.02em;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}}
.member-name {{ font-size: 0.9375rem; font-weight: 700; color: #0F172A; font-family: 'Plus Jakarta Sans', sans-serif; letter-spacing: -0.01em; }}
.member-role {{ font-size: 0.8125rem; color: #64748b; font-weight: 500; }}
.member-stat {{ font-size: 0.75rem; color: #94a3b8; margin-top: 3px; }}

/* ── Buttons ── */
.stButton > button[kind="primary"] {{
  background: linear-gradient(135deg, {MEDPORT_TEAL} 0%, #3B7EFF 100%);
  color: white !important;
  border: none !important;
  border-radius: 10px !important;
  padding: 0.5rem 1.5rem !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
  letter-spacing: -0.01em !important;
  font-family: 'Inter', sans-serif !important;
  transition: var(--transition) !important;
  box-shadow: 0 2px 8px rgba(0,184,159,0.3) !important;
}}
.stButton > button[kind="primary"]:hover {{
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 20px rgba(0,184,159,0.4) !important;
  filter: brightness(1.05) !important;
}}
.stButton > button[kind="primary"]:active {{
  transform: translateY(0px) !important;
}}
.stButton > button[kind="secondary"] {{
  background: #ffffff !important;
  color: #475569 !important;
  border: 1.5px solid #e2e8f0 !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  transition: var(--transition) !important;
}}
.stButton > button[kind="secondary"]:hover {{
  border-color: #94a3b8 !important;
  background: #f8fafc !important;
  color: #0F172A !important;
}}

/* ── Prospect card helpers ── */
.queue-badge {{
  background: #fffbeb; color: #92400e;
  border: 1px solid {CARD_YELLOW};
  padding: 2px 9px; border-radius: 6px;
  font-size: 0.8125rem; font-weight: 600; display: inline-block;
}}
.inst-header {{ font-size: 1.0625rem; font-weight: 800; color: {MEDPORT_DARK}; font-family: 'Plus Jakarta Sans', sans-serif; letter-spacing: -0.02em; }}
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
/* outreach-box defined below in enhanced section */
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
  background: var(--mp-grad);
  color: #fff;
  border-radius: 16px 16px 4px 16px;
  padding: 0.75rem 1.1rem; margin: 0.35rem 0; font-size: 0.9375rem;
  max-width: 82%; margin-left: auto;
  box-shadow: 0 4px 12px rgba(0,184,159,0.25);
}}
.chat-msg-assistant {{
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: 16px 16px 16px 4px;
  padding: 0.75rem 1.1rem; margin: 0.35rem 0; font-size: 0.9375rem;
  max-width: 88%; color: {MEDPORT_DARK};
  box-shadow: var(--mp-shadow-sm);
}}

/* ── Prospect table ── */
.mp-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  color: {MEDPORT_DARK};
  background: #ffffff;
  border-radius: var(--mp-radius-md);
  overflow: hidden;
  box-shadow: var(--mp-shadow-sm);
  border: 1px solid rgba(0,0,0,0.06);
}}
.mp-table th {{
  background: #f8fafc;
  border-bottom: 1px solid #e8ecf0;
  padding: 0.7rem 0.95rem;
  text-align: left;
  font-weight: 700;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  white-space: nowrap;
}}
.mp-table td {{
  padding: 0.65rem 0.95rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
  transition: background 0.12s ease;
}}
.mp-table tr:hover td {{
  background: #f8fafc;
}}
.mp-table tr:last-child td {{ border-bottom: none; }}

/* ── Department badges ── */
.dept-badge {{
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}}
.dept-leadership {{ background: rgba(0,184,159,0.12); color: #00B89F; }}
.dept-marketing   {{ background: rgba(59,130,246,0.12); color: #2563EB; }}
.dept-finance     {{ background: rgba(16,185,129,0.12); color: #059669; }}
.dept-tech        {{ background: rgba(139,92,246,0.12); color: #7C3AED; }}
.dept-operations  {{ background: rgba(245,158,11,0.12); color: #D97706; }}
.dept-unassigned  {{ background: #f1f5f9; color: #64748b; }}

/* ── Access denied card ── */
.access-denied-card {{
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-left: 4px solid #ef4444;
  border-radius: 16px;
  padding: 2.5rem 2rem;
  text-align: center;
  max-width: 540px;
  margin: 3rem auto;
}}
.access-denied-title {{
  font-size: 1.375rem;
  font-weight: 700;
  color: #991b1b;
  font-family: 'Plus Jakarta Sans', sans-serif;
  margin-bottom: 0.5rem;
}}
.access-denied-body {{
  font-size: 0.9375rem;
  color: #7f1d1d;
  line-height: 1.6;
}}

/* ── Announcement banner ── */
.announcement-info    {{ background:#eff6ff; border-left:4px solid #3B82F6; border-radius:10px; padding:0.875rem 1.1rem; margin-bottom:0.75rem; }}
.announcement-warning {{ background:#fffbeb; border-left:4px solid #F59E0B; border-radius:10px; padding:0.875rem 1.1rem; margin-bottom:0.75rem; }}
.announcement-urgent  {{ background:#fef2f2; border-left:4px solid #EF4444; border-radius:10px; padding:0.875rem 1.1rem; margin-bottom:0.75rem; }}
.announcement-title   {{ font-size:0.9375rem; font-weight:700; color:#0F172A; font-family:'Plus Jakarta Sans',sans-serif; }}
.announcement-body    {{ font-size:0.875rem; color:#334155; margin-top:4px; line-height:1.5; }}

/* ── Standup card ── */
.standup-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin-bottom: 0.5rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}}
.standup-author {{ font-size:0.875rem; font-weight:700; color:#0F172A; font-family:'Plus Jakarta Sans',sans-serif; }}
.standup-date   {{ font-size:0.75rem; color:#94a3b8; margin-left:0.5rem; }}
.standup-section {{ font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:#64748b; margin-top:0.6rem; margin-bottom:2px; }}
.standup-text   {{ font-size:0.875rem; color:#334155; line-height:1.5; }}

/* ── Wiki card ── */
.wiki-card {{
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  transition: box-shadow 0.2s, border-color 0.2s;
}}
.wiki-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-color: #cbd5e1; }}
.wiki-title {{ font-size:0.9375rem; font-weight:700; color:#0F172A; font-family:'Plus Jakarta Sans',sans-serif; }}
.wiki-meta  {{ font-size:0.8125rem; color:#64748b; margin-top:3px; }}

/* ── Notification badge ── */
.notif-badge {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  background: #EF4444; color: #fff;
  font-size: 0.7rem; font-weight: 700;
  margin-left: 6px; vertical-align: middle;
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
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: var(--mp-radius-md);
  padding: 1.1rem 1.3rem;
  margin-bottom: 0.75rem;
  box-shadow: var(--mp-shadow-sm);
  transition: var(--transition);
}}
.intel-card:hover {{ box-shadow: var(--mp-shadow-md); }}
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
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: var(--mp-radius-md);
  padding: 1rem 1.2rem;
  box-shadow: var(--mp-shadow-sm);
  transition: var(--transition);
}}
.settings-member-card:hover {{
  box-shadow: var(--mp-shadow-md);
  transform: translateY(-1px);
}}

/* ── Filter status bar ── */
.filter-bar {{
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: var(--mp-radius-md);
  padding: 0.6rem 1.1rem;
  font-size: 0.875rem;
  color: #475569;
  margin-bottom: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  box-shadow: var(--mp-shadow-sm);
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

/* ── Gradient hero banner ── */
.mp-hero {{
  background: linear-gradient(135deg, #0B1120 0%, #0F172A 50%, #1a2a3a 100%);
  border-radius: var(--mp-radius-lg);
  padding: 2rem 2.25rem;
  margin-bottom: 1.75rem;
  position: relative;
  overflow: hidden;
  box-shadow: var(--mp-shadow-lg);
}}
.mp-hero::before {{
  content: '';
  position: absolute;
  top: -60px; right: -60px;
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(0,184,159,0.25) 0%, transparent 70%);
  pointer-events: none;
}}
.mp-hero::after {{
  content: '';
  position: absolute;
  bottom: -40px; left: 30%;
  width: 150px; height: 150px;
  background: radial-gradient(circle, rgba(59,126,255,0.2) 0%, transparent 70%);
  pointer-events: none;
}}
.mp-hero-title {{
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.75rem;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.03em;
  line-height: 1.15;
  margin-bottom: 0.4rem;
}}
.mp-hero-sub {{
  font-size: 0.9375rem;
  color: #94a3b8;
  font-weight: 400;
  line-height: 1.6;
}}

/* ── Glass card ── */
.mp-glass {{
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.8);
  border-radius: var(--mp-radius-md);
  box-shadow: var(--mp-shadow-md);
}}

/* ── Gradient text utility ── */
.mp-grad-text {{
  background: var(--mp-grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 800;
}}

/* ── Glow accent line ── */
.mp-glow-line {{
  height: 3px;
  background: var(--mp-grad);
  border-radius: 999px;
  margin: 0.75rem 0;
  box-shadow: 0 0 12px rgba(0,184,159,0.4);
}}

/* ── Metric delta badge ── */
.mp-delta-up {{
  background: #f0fdf9; color: #059669;
  border-radius: 999px; padding: 2px 9px;
  font-size: 0.75rem; font-weight: 700;
  display: inline-flex; align-items: center; gap: 3px;
}}
.mp-delta-down {{
  background: #fef2f2; color: #dc2626;
  border-radius: 999px; padding: 2px 9px;
  font-size: 0.75rem; font-weight: 700;
  display: inline-flex; align-items: center; gap: 3px;
}}

/* ── Kanban column ── */
.kanban-col {{
  background: #f8fafc;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: var(--mp-radius-md);
  padding: 1rem 0.875rem;
  min-height: 200px;
}}
.kanban-header {{
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 6px;
}}

/* ── Section divider with label ── */
.mp-section-label {{
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #94a3b8;
  margin: 1.5rem 0 0.75rem 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}}
.mp-section-label::after {{
  content: '';
  flex: 1;
  height: 1px;
  background: #e2e8f0;
}}

/* ── Outreach box — enhanced ── */
.outreach-box {{
  background: #f8fafc;
  border-radius: var(--mp-radius-md); padding: 1rem 1.25rem;
  font-size: 0.9375rem; color: {MEDPORT_DARK}; margin-top: 0.5rem;
  border: 1px solid rgba(0,0,0,0.06); border-left: 3px solid {MEDPORT_TEAL};
  box-shadow: var(--mp-shadow-sm);
  line-height: 1.65;
}}

/* ── Scrollbar — subtle ── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 999px; }}
::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}

/* ── Mobile responsiveness ── */
@media (max-width: 768px) {{
  /* Tighten main padding on small screens */
  .main .block-container {{
    padding-top: 1rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    max-width: 100% !important;
  }}

  /* Stack columns vertically */
  [data-testid="stHorizontalBlock"] {{
    flex-wrap: wrap !important;
  }}
  [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] {{
    min-width: 100% !important;
    width: 100% !important;
  }}

  /* Stat cards — smaller on mobile */
  .stat-card {{
    padding: 1rem 1.1rem !important;
    border-radius: 14px !important;
  }}
  .stat-card .stat-value {{
    font-size: 1.875rem !important;
  }}

  /* Member cards — 2-column grid on mobile */
  .member-card {{
    padding: 1rem 0.75rem !important;
  }}
  .member-avatar {{
    width: 42px !important;
    height: 42px !important;
    font-size: 0.875rem !important;
  }}

  /* Page title — smaller */
  .page-title {{
    font-size: 1.5rem !important;
  }}

  /* Tabs — smaller text, scrollable */
  .stTabs [data-baseweb="tab-list"] {{
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
  }}
  .stTabs [data-baseweb="tab"] {{
    font-size: 0.8rem !important;
    padding: 0.5rem 0.7rem !important;
    white-space: nowrap !important;
  }}

  /* Buttons — always full width on mobile */
  .stButton > button {{
    width: 100% !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1rem !important;
  }}

  /* Hide sidebar collapse button area padding */
  section[data-testid="stSidebar"] {{
    min-width: 260px !important;
  }}

  /* Inputs — full width */
  .stTextInput, .stSelectbox, .stTextArea {{
    width: 100% !important;
  }}

  /* Prospect cards — reduce padding */
  .inst-header {{ font-size: 0.9375rem !important; }}
  .inst-meta {{ font-size: 0.75rem !important; }}

  /* Funnel — scrollable on mobile */
  .funnel-row {{ overflow-x: auto !important; }}

  /* Task cards */
  .task-card {{
    padding: 0.75rem 1rem !important;
    border-radius: 10px !important;
  }}

  /* Chat bubbles — wider on mobile */
  .chat-msg-user, .chat-msg-assistant {{
    max-width: 95% !important;
  }}

  /* Hide decorative ::after orbs on mobile (performance) */
  .stat-card::after {{ display: none !important; }}
  .member-card::before {{ display: none !important; }}
}}

/* ── Streamlit expander ── */
[data-testid="stExpander"] {{
  border: 1px solid rgba(0,0,0,0.07) !important;
  border-radius: var(--mp-radius-md) !important;
  background: #ffffff !important;
  box-shadow: var(--mp-shadow-sm) !important;
  overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
  font-weight: 600 !important;
  color: {MEDPORT_DARK} !important;
  padding: 0.75rem 1rem !important;
}}

/* ── Metric widget ── */
[data-testid="stMetric"] {{
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: var(--mp-radius-md);
  padding: 1rem 1.25rem;
  box-shadow: var(--mp-shadow-sm);
}}
[data-testid="stMetricLabel"] {{ font-size: 0.75rem !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b !important; }}
[data-testid="stMetricValue"] {{ font-size: 2rem !important; font-weight: 800 !important; font-family: 'Plus Jakarta Sans', sans-serif !important; letter-spacing: -0.04em !important; color: {MEDPORT_DARK} !important; }}
[data-testid="stMetricDelta"] {{ font-size: 0.8rem !important; font-weight: 600 !important; }}
</style>
"""


def inject_css():
    """Call this on every page after st.set_page_config()."""
    st.markdown(get_css(), unsafe_allow_html=True)
