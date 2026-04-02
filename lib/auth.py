"""
MedPort auth helpers.
Every page calls check_auth() at the top to get (name, email).
LOCAL_DEV=true env var bypasses auth for local testing.
"""

import os
import streamlit as st


def _secret(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def _auth_is_configured() -> bool:
    """
    Returns True if the [auth] section in Streamlit secrets is properly set up.
    Checks for redirect_uri or providers — not just the presence of the section.
    """
    try:
        auth = st.secrets.get("auth", {}) or {}
        return bool(auth.get("redirect_uri") or auth.get("providers") or auth.get("cookie_secret"))
    except Exception:
        return False


def get_user() -> tuple[str, str]:
    """Returns (name, email). Never raises."""
    if os.environ.get("LOCAL_DEV", "false").lower() == "true":
        return (
            os.environ.get("DEV_USER_NAME", "Arav (dev)"),
            os.environ.get("DEV_USER_EMAIL", "aravkekane@gmail.com"),
        )
    try:
        user = st.experimental_user
        email = getattr(user, "email", "") or ""
        name = getattr(user, "name", "") or ""
        if not name:
            name = email.split("@")[0].capitalize() if email else "Team Member"
        return name, email
    except Exception:
        return "Team Member", ""


def is_admin(email: str) -> bool:
    hardcoded = {"aravkekane@gmail.com", "arav@medport.ca"}
    extra_raw = _secret("ADMIN_EMAILS", "")
    extras = {e.strip().lower() for e in extra_raw.split(",") if e.strip()}
    return (email or "").lower() in (hardcoded | extras)


def render_logout_button():
    """
    Renders a Sign Out button in the current context (call inside a sidebar block).
    Always shown when auth is configured, regardless of page.
    """
    local_dev = os.environ.get("LOCAL_DEV", "false").lower() == "true"
    if _auth_is_configured() and not local_dev:
        if st.button("Sign out", key="global_signout", use_container_width=True):
            st.logout()


def check_auth() -> tuple[str, str]:
    """
    Call at the top of every page. Returns (name, email).
    Shows Google login screen if not authenticated.
    """
    local_dev = os.environ.get("LOCAL_DEV", "false").lower() == "true"
    auth_configured = _auth_is_configured()

    # No auth configured or local dev — pass through
    if local_dev or not auth_configured:
        return get_user()

    # Check login state
    try:
        is_logged_in = st.experimental_user.is_logged_in
    except AttributeError:
        is_logged_in = False

    if not is_logged_in:
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

        if user_email and user_email not in allowed:
            st.error(f"Access denied. **{user_email}** is not on the MedPort team list.")
            st.caption("Contact Arav to request access.")
            if st.button("Sign out"):
                st.logout()
            st.stop()

    return get_user()


def _show_login_screen():
    from lib.styles import MEDPORT_TEAL, MEDPORT_BLUE, MEDPORT_DARK, inject_css
    inject_css()

    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown(
            f"""
            <div style="text-align:center;padding:2.5rem 2rem 2rem 2rem;
              background:#ffffff;border:1px solid #e2e8f0;border-radius:1.25rem;
              box-shadow:0 8px 32px rgba(0,184,159,0.10);">
              <div style="font-size:2.2rem;font-weight:900;font-family:'Syne',sans-serif;
                background:linear-gradient(135deg,{MEDPORT_TEAL},{MEDPORT_BLUE});
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;margin-bottom:0.3rem;">
                MedPort
              </div>
              <div style="font-size:0.88rem;color:#64748b;margin-bottom:2rem;font-weight:500;">
                Team Intelligence Hub
              </div>
              <div style="font-size:0.9rem;color:#475569;margin-bottom:1.5rem;">
                Sign in with your MedPort Google account to continue.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")
        if st.button(
            "Sign in with Google",
            type="primary",
            use_container_width=True,
            key="login_btn",
        ):
            st.login()
