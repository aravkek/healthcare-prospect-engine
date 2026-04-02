"""
MedPort auth helpers.
Every page calls check_auth() at the top to get (name, email).
LOCAL_DEV=true env var bypasses auth for local testing.

Auth detection: uses st.experimental_user.is_logged_in directly.
Streamlit Cloud OAuth is configured via their UI, NOT via secrets.toml,
so checking secrets for [auth] keys always fails on Cloud.
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


def _is_local_dev() -> bool:
    return os.environ.get("LOCAL_DEV", "false").lower() == "true"


def _auth_is_active() -> bool:
    """
    Returns True if Streamlit's auth system is active (user object has is_logged_in).
    Works whether auth is configured via secrets.toml OR Streamlit Cloud UI.
    """
    try:
        _ = st.experimental_user.is_logged_in
        return True
    except AttributeError:
        return False


def get_user() -> tuple[str, str]:
    """Returns (name, email). Never raises."""
    if _is_local_dev():
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
    email_lower = (email or "").lower().strip()
    hardcoded = {"aravkekane@gmail.com", "arav@medport.ca", "arav@medport.health"}
    extra_raw = _secret("ADMIN_EMAILS", "")
    extras = {e.strip().lower() for e in extra_raw.split(",") if e.strip()}
    all_admins = hardcoded | extras
    # Exact match OR any arav@* medport address
    if email_lower in all_admins:
        return True
    # Fallback: first name is arav + medport domain
    if email_lower.startswith("arav@") and "medport" in email_lower:
        return True
    return False


def render_logout_button():
    """
    Renders a Sign Out button. Call inside a sidebar block on every page.
    Shows whenever auth is active (is_logged_in=True) OR user has an email.
    """
    if _is_local_dev():
        return
    try:
        user = st.experimental_user
        logged_in = getattr(user, "is_logged_in", None)
        email = getattr(user, "email", "") or ""
        # Show button if explicitly logged in, or if we have any email at all
        if logged_in or email:
            if email:
                st.markdown(
                    f"<div style='font-size:0.75rem;color:#64748b;padding:2px 0 4px 0;"
                    f"word-break:break-all;'>{email}</div>",
                    unsafe_allow_html=True,
                )
            if st.button("Sign out", key="global_signout", use_container_width=True):
                st.logout()
    except Exception:
        pass


def check_auth() -> tuple[str, str]:
    """
    Call at the top of every page. Returns (name, email).
    Shows Google login screen if auth is active but user is not logged in.
    Passes through silently if auth is not configured at all.
    """
    if _is_local_dev():
        return get_user()

    # If Streamlit auth isn't active at all, just pass through
    if not _auth_is_active():
        return get_user()

    # Auth is active — enforce login
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
    from lib.styles import MEDPORT_TEAL, MEDPORT_BLUE, inject_css
    inject_css()

    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown(
            f"""
            <div style="text-align:center;padding:2.5rem 2rem 2rem 2rem;
              background:#ffffff;border:1px solid #e2e8f0;border-radius:1.25rem;
              box-shadow:0 8px 32px rgba(0,184,159,0.10);">
              <div style="font-size:2.2rem;font-weight:700;font-family:'Plus Jakarta Sans',sans-serif;
                color:#0F172A;letter-spacing:-0.02em;margin-bottom:0.3rem;">
                MedPort
              </div>
              <div style="font-size:0.9rem;color:#64748b;margin-bottom:2rem;font-weight:500;">
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
