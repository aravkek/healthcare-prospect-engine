"""
MedPort auth helpers.
Every page calls check_auth() at the top to get (name, email).
LOCAL_DEV=true env var bypasses auth for local testing.
"""

import os
import streamlit as st


def _secret(key: str, default: str = "") -> str:
    """Read from env first, then st.secrets, else default."""
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def get_user() -> tuple[str, str]:
    """
    Returns (name, email) from st.experimental_user or env fallback.
    Never raises — always returns something.
    """
    # Local dev override
    if os.environ.get("LOCAL_DEV", "false").lower() == "true":
        name = os.environ.get("DEV_USER_NAME", "Arav (dev)")
        email = os.environ.get("DEV_USER_EMAIL", "aravkekane@gmail.com")
        return name, email

    try:
        user = st.experimental_user
        name = getattr(user, "name", "") or ""
        email = getattr(user, "email", "") or ""
        if not name:
            name = email.split("@")[0].capitalize() if email else "Team Member"
        return name, email
    except AttributeError:
        return "Team Member", ""


def is_admin(email: str) -> bool:
    """
    Returns True if this email has admin privileges (can issue cards, assign tasks).
    Arav is always admin. Additional admins can be added via ADMIN_EMAILS secret.
    """
    hardcoded = {"aravkekane@gmail.com", "arav@medport.ca"}
    extra_raw = _secret("ADMIN_EMAILS", "")
    extras = {e.strip().lower() for e in extra_raw.split(",") if e.strip()}
    return (email or "").lower() in (hardcoded | extras)


def check_auth() -> tuple[str, str]:
    """
    Run at the top of every page. Returns (name, email).
    - If LOCAL_DEV=true: bypass auth entirely.
    - If auth is configured in st.secrets: enforce Google OAuth.
    - If auth is not configured: allow through with a guest identity.
    """
    local_dev = os.environ.get("LOCAL_DEV", "false").lower() == "true"

    # Check if auth is configured
    try:
        auth_configured = bool(st.secrets.get("auth", {}))
    except Exception:
        auth_configured = False

    if local_dev or not auth_configured:
        name, email = get_user()
        return name, email

    # Auth is configured — enforce login
    try:
        is_logged_in = st.experimental_user.is_logged_in
    except AttributeError:
        is_logged_in = False

    if not is_logged_in:
        st.set_page_config(
            page_title="MedPort — Sign In",
            page_icon="🏥",
            layout="centered",
        ) if False else None  # page_config already set by the page
        _show_login_screen()
        st.stop()

    # Validate allowed emails
    allowed_raw = _secret("ALLOWED_EMAILS", "")
    if allowed_raw:
        allowed = {e.strip().lower() for e in allowed_raw.split(",") if e.strip()}
        try:
            user_email = (st.experimental_user.email or "").lower()
        except AttributeError:
            user_email = ""

        if user_email not in allowed:
            st.error(f"Access denied. {user_email} is not on the MedPort team list.")
            st.info("Contact Arav to request access.")
            if st.button("Sign out"):
                st.logout()
            st.stop()

    return get_user()


def _show_login_screen():
    from lib.styles import MEDPORT_BLUE, MEDPORT_GREEN, inject_css
    inject_css()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""
            <div style="text-align:center; padding: 3rem 0 2rem 0;">
              <div style="font-size:2.5rem; font-weight:900;
                background: linear-gradient(135deg, {MEDPORT_BLUE}, {MEDPORT_GREEN});
                -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                background-clip:text;">
                MedPort
              </div>
              <div style="font-size:0.95rem; color:#6b7a8d; margin-top:0.3rem;">
                Team Intelligence Hub
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("Sign in with your MedPort Google account to access the team dashboard.")
        st.markdown("")

        if st.button("Sign in with Google", type="primary", use_container_width=True):
            st.login()
