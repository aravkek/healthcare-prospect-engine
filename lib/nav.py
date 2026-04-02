"""
lib/nav.py
Role-based navigation for the MedPort Team OS Streamlit app.

Co-founders and their departments:
  Arav   — leadership (admin, sees everything)
  Advait — finance
  Ahan   — marketing
  Aarya  — tech
  Nathen — operations
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Page registry — single source of truth for every page in the app
# (path, label, icon)
# ---------------------------------------------------------------------------
_ALL_PAGES: list[tuple[str, str, str]] = [
    ("medport_dashboard.py",       "Home",             "🏠"),
    ("pages/1_Team_Hub.py",        "Team Hub",         "👥"),
    ("pages/2_Outreach_CRM.py",    "Outreach CRM",     "📊"),
    ("pages/3_Tasks.py",           "Tasks",            "✅"),
    ("pages/4_Cards.py",           "Cards",            "🟨"),
    ("pages/5_AI_Research.py",     "AI Research",      "🤖"),
    ("pages/6_Settings.py",        "Settings",         "⚙️"),
    ("pages/7_Intelligence.py",    "Intelligence",     "🔍"),
    ("pages/8_Marketing_Hub.py",   "Marketing Hub",    "📣"),
    ("pages/9_Finance_Hub.py",     "Finance Hub",      "💰"),
    ("pages/10_Tech_Hub.py",       "Tech Hub",         "💻"),
    ("pages/11_Operations_Hub.py", "Operations Hub",   "🔧"),
    ("pages/12_Announcements.py",  "Announcements",    "📢"),
    ("pages/13_Standups.py",       "Standups",         "📋"),
    ("pages/14_Wiki.py",           "Wiki",             "📚"),
    ("pages/16_Prospect_Profile.py", "Prospect Profile", "🎯"),
]

# Lookup by label for quick access in badge/filter logic
_PAGE_BY_LABEL: dict[str, tuple[str, str, str]] = {p[1]: p for p in _ALL_PAGES}

# ---------------------------------------------------------------------------
# Department → allowed page labels
# ---------------------------------------------------------------------------
_DEPT_LABELS: dict[str, list[str]] = {
    "leadership": [p[1] for p in _ALL_PAGES],  # all pages
    "marketing": [
        "Home", "Team Hub", "Outreach CRM", "Tasks",
        "Marketing Hub", "AI Research", "Announcements", "Standups", "Settings",
    ],
    "finance": [
        "Home", "Team Hub", "Tasks",
        "Finance Hub", "Announcements", "Standups", "Settings",
    ],
    "tech": [
        "Home", "Team Hub", "Tasks",
        "Tech Hub", "AI Research", "Announcements", "Standups", "Settings",
    ],
    "operations": [
        "Home", "Team Hub", "Tasks", "Cards",
        "Operations Hub", "Announcements", "Standups", "Settings",
    ],
    "unassigned": [
        "Home", "Team Hub", "Tasks", "Announcements", "Standups", "Settings",
    ],
}

# ---------------------------------------------------------------------------
# DEPT_PAGE_LABELS: public mapping — department → list of (path, label, icon)
# ---------------------------------------------------------------------------
DEPT_PAGE_LABELS: dict[str, list[tuple[str, str, str]]] = {
    dept: [_PAGE_BY_LABEL[label] for label in labels if label in _PAGE_BY_LABEL]
    for dept, labels in _DEPT_LABELS.items()
}

# ---------------------------------------------------------------------------
# Department brand colors
# ---------------------------------------------------------------------------
_DEPT_COLORS: dict[str, str] = {
    "leadership": "#00B89F",
    "marketing":  "#3B82F6",
    "finance":    "#10B981",
    "tech":       "#8B5CF6",
    "operations": "#F59E0B",
    "unassigned": "#94a3b8",
}


def get_dept_color(dept: str) -> str:
    """Return the hex brand color for a department."""
    return _DEPT_COLORS.get(dept, _DEPT_COLORS["unassigned"])


def get_dept_pages(dept: str, is_admin_user: bool) -> list[tuple[str, str, str]]:
    """
    Return the list of (path, label, icon) tuples accessible to a user.
    Admin users always receive every page regardless of their department.
    """
    if is_admin_user:
        return list(_ALL_PAGES)
    return list(DEPT_PAGE_LABELS.get(dept, DEPT_PAGE_LABELS["unassigned"]))


# ---------------------------------------------------------------------------
# Sidebar rendering
# ---------------------------------------------------------------------------

def _derive_display_name(email: str) -> str:
    """Best-effort first name from an email address."""
    local = email.split("@")[0]
    # Handle dot-separated names: first.last@domain → First
    part = local.split(".")[0]
    return part.capitalize()


def render_sidebar_nav(
    email: str,
    dept: str,
    is_admin_user: bool,
    unread_notifications: int = 0,
    unread_announcements: int = 0,
) -> None:
    """
    Render the full sidebar navigation.

    Call this inside a `with st.sidebar:` block. The function outputs widgets
    directly without referencing st.sidebar internally, keeping it testable
    and composable.
    """
    # Deferred import to avoid circular dependency (lib.auth imports lib.nav indirectly)
    from lib.auth import render_logout_button

    dept_key = dept if dept in _DEPT_COLORS else "unassigned"
    color = get_dept_color(dept_key)
    display_name = _derive_display_name(email)

    # ------------------------------------------------------------------
    # Branding
    # ------------------------------------------------------------------
    st.markdown(
        f"""
        <div style="padding: 0.5rem 0 0.25rem 0;">
            <span style="font-size:1.45rem; font-weight:700; color:#00B89F; letter-spacing:-0.5px;">
                MedPort
            </span>
            <div style="font-size:0.72rem; color:#94a3b8; margin-top:1px; letter-spacing:0.3px;">
                Team Intelligence Hub
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # User identity
    # ------------------------------------------------------------------
    st.markdown(
        f"<div style='font-size:0.78rem; color:#94a3b8; margin-bottom:6px;'>"
        f"Signed in as <strong style='color:#cbd5e1;'>{display_name}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Department badge (+ optional Admin badge)
    badges_html = (
        f"<span style='"
        f"background:{color}22; color:{color}; border:1px solid {color}55; "
        f"border-radius:999px; padding:2px 10px; font-size:0.72rem; font-weight:600; "
        f"margin-right:6px; display:inline-block;'>"
        f"{dept_key.capitalize()}"
        f"</span>"
    )
    if is_admin_user:
        badges_html += (
            "<span style='"
            "background:linear-gradient(135deg,#1e293b,#334155); color:#e2e8f0; "
            "border:1px solid #475569; border-radius:999px; padding:2px 10px; "
            "font-size:0.72rem; font-weight:600; display:inline-block;'>"
            "Admin"
            "</span>"
        )

    st.markdown(
        f"<div style='margin-bottom:10px;'>{badges_html}</div>",
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Separator
    # ------------------------------------------------------------------
    st.markdown(
        "<hr style='border:none; border-top:1px solid #1e293b; margin:6px 0 10px 0;'/>",
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Sign-out
    # ------------------------------------------------------------------
    render_logout_button()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    st.markdown(
        "<div style='font-size:0.7rem; font-weight:700; color:#64748b; "
        "letter-spacing:0.08em; text-transform:uppercase; margin:12px 0 4px 0;'>"
        "Team</div>",
        unsafe_allow_html=True,
    )

    pages = get_dept_pages(dept_key, is_admin_user)

    for path, label, icon in pages:
        # Augment labels with unread counts where applicable
        display_label = label
        if label == "Announcements" and unread_announcements > 0:
            display_label = f"{label} ({unread_announcements})"
        elif label == "Notifications" and unread_notifications > 0:
            display_label = f"{label} ({unread_notifications})"

        st.page_link(path, label=display_label, icon=icon)


# ---------------------------------------------------------------------------
# Access control helpers
# ---------------------------------------------------------------------------

def check_page_access(
    email: str,
    dept: str,
    allowed_depts: list[str],
    is_admin_user: bool,
) -> bool:
    """
    Return True if the user may view the current page.

    Admins always have access. Otherwise, the user's department must appear
    in allowed_depts.
    """
    if is_admin_user:
        return True
    return dept in allowed_depts


def render_access_denied(dept: str, allowed_depts: list[str]) -> None:
    """
    Render a styled Access Denied error card.

    Show which departments are permitted and provide a link back to Team Hub.
    """
    color = get_dept_color(dept)
    allowed_labels = ", ".join(d.capitalize() for d in allowed_depts)

    st.markdown(
        f"""
        <div style="
            background:#1e1e2e;
            border:1px solid #ef444455;
            border-left:4px solid #ef4444;
            border-radius:10px;
            padding:1.5rem 1.75rem;
            margin:2rem auto;
            max-width:520px;
        ">
            <div style="font-size:1.15rem; font-weight:700; color:#ef4444; margin-bottom:8px;">
                Access Denied
            </div>
            <div style="font-size:0.9rem; color:#cbd5e1; line-height:1.6;">
                Your department
                <span style="
                    background:{color}22; color:{color}; border:1px solid {color}55;
                    border-radius:999px; padding:1px 9px; font-size:0.8rem;
                    font-weight:600; margin:0 2px;
                ">{dept.capitalize()}</span>
                does not have access to this page.
            </div>
            <div style="font-size:0.82rem; color:#64748b; margin-top:10px;">
                This page is available to:
                <strong style="color:#94a3b8;">{allowed_labels}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.page_link("pages/1_Team_Hub.py", label="Go to Team Hub", icon="👥")
