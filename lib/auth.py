"""
MedPort auth.

Two modes (tried in order):
  1. Streamlit OAuth  — if [auth] secrets are configured (st.login / st.logout)
  2. Password gate    — if TEAM_PASSWORD secret is set (simple shared password)

If neither is configured the app passes through (local dev / no-auth deploy).
"""

import os
import streamlit as st

# Email → display name overrides (so "aravkekane@gmail.com" shows as "Arav" not "Aravkekane")
_NAME_EMAIL_MAP = {
    "aravkekane@gmail.com": "Arav",
    "arav@medport.ca": "Arav",
    "arav@medport.health": "Arav",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

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


def _oauth_is_active() -> bool:
    """True only when Streamlit's [auth] secrets are configured."""
    try:
        _ = st.experimental_user.is_logged_in
        return True
    except AttributeError:
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

def get_user() -> tuple[str, str]:
    """Returns (name, email). Never raises."""
    if _is_local_dev():
        return (
            os.environ.get("DEV_USER_NAME", "Arav (dev)"),
            os.environ.get("DEV_USER_EMAIL", "aravkekane@gmail.com"),
        )
    # Password-auth session
    if st.session_state.get("_mp_authenticated"):
        return (
            st.session_state.get("_mp_name", "Team Member"),
            st.session_state.get("_mp_email", ""),
        )
    # OAuth session
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
    hardcoded = {"aravkekane@gmail.com", "arav@medport.ca", "arav@medport.health"}
    extra_raw = _secret("ADMIN_EMAILS", "")
    extras = {e.strip().lower() for e in extra_raw.split(",") if e.strip()}
    all_admins = hardcoded | extras
    email_lower = (email or "").lower().strip()
    if email_lower in all_admins:
        return True
    if email_lower.startswith("arav@") and "medport" in email_lower:
        return True
    return False


def render_logout_button():
    """Call inside a `with st.sidebar:` block on every page."""
    if _is_local_dev():
        return

    # OAuth logout
    try:
        if st.experimental_user.is_logged_in:
            if st.button("Sign out", key="global_signout", use_container_width=True):
                st.logout()
            return
    except AttributeError:
        pass

    # Password auth logout
    if st.session_state.get("_mp_authenticated"):
        if st.button("Sign out", key="global_signout", use_container_width=True):
            for k in ("_mp_authenticated", "_mp_name", "_mp_email"):
                st.session_state.pop(k, None)
            st.rerun()


def check_auth() -> tuple[str, str]:
    """
    Call at the top of every page. Returns (name, email).
    Blocks access until the user authenticates.
    """
    if _is_local_dev():
        return get_user()

    # ── Mode 1: Streamlit OAuth ───────────────────────────────────────────────
    if _oauth_is_active():
        try:
            logged_in = st.experimental_user.is_logged_in
        except AttributeError:
            logged_in = False

        if not logged_in:
            _show_oauth_login()
            st.stop()

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

    # ── Mode 2: Password gate ─────────────────────────────────────────────────
    team_password = _secret("TEAM_PASSWORD", "")
    if team_password:
        if not st.session_state.get("_mp_authenticated"):
            _show_password_login(team_password)
            st.stop()
        return get_user()

    # ── No auth configured — pass through ────────────────────────────────────
    return get_user()


# ─── Login screens ────────────────────────────────────────────────────────────

def _show_oauth_login():
    from lib.styles import MEDPORT_TEAL, MEDPORT_BLUE, MEDPORT_DARK, inject_css
    inject_css()
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown(
            f"""
            <div style="text-align:center;padding:2.5rem 2rem 2rem;background:#fff;
              border:1px solid #e2e8f0;border-radius:1.25rem;
              box-shadow:0 8px 32px rgba(0,0,0,0.08);">
              <div style="font-size:2rem;font-weight:700;
                font-family:'Plus Jakarta Sans',sans-serif;
                color:{MEDPORT_DARK};letter-spacing:-0.02em;margin-bottom:0.3rem;">
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
        if st.button("Sign in with Google", type="primary",
                     use_container_width=True, key="login_btn"):
            st.login()


def _show_password_login(team_password: str):
    from lib.styles import MEDPORT_DARK, inject_css
    inject_css()
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown(
            f"""
            <div style="text-align:center;padding:2.5rem 2rem 1.5rem;background:#fff;
              border:1px solid #e2e8f0;border-radius:1.25rem;
              box-shadow:0 8px 32px rgba(0,0,0,0.08);margin-bottom:1rem;">
              <div style="font-size:2rem;font-weight:700;
                font-family:'Plus Jakarta Sans',sans-serif;
                color:{MEDPORT_DARK};letter-spacing:-0.02em;margin-bottom:0.25rem;">
                MedPort
              </div>
              <div style="font-size:0.875rem;color:#64748b;font-weight:500;">
                Team Intelligence Hub
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        email_input = st.text_input("Email", placeholder="you@medport.ca",
                                    key="_mp_email_input")
        pwd_input = st.text_input("Team password", type="password",
                                  key="_mp_pwd_input")

        if st.button("Sign in", type="primary", use_container_width=True,
                     key="_mp_signin"):
            if not email_input.strip():
                st.error("Enter your email.")
            elif pwd_input != team_password:
                st.error("Wrong password. Ask Arav for the team password.")
            else:
                # Check allowed emails if configured
                allowed_raw = _secret("ALLOWED_EMAILS", "")
                email_lower = email_input.strip().lower()
                if allowed_raw:
                    allowed = {e.strip().lower() for e in allowed_raw.split(",") if e.strip()}
                    if email_lower not in allowed:
                        st.error("That email isn't on the MedPort team list. Contact Arav.")
                        return
                # Derive display name from email
                name_part = email_lower.split("@")[0]
                # Check hardcoded name map first
                name = _NAME_EMAIL_MAP.get(email_lower, "")
                if not name:
                    # e.g. "arav.kekane" → "Arav Kekane"
                    name = name_part.replace(".", " ").replace("_", " ").title()
                st.session_state["_mp_authenticated"] = True
                st.session_state["_mp_name"] = name
                st.session_state["_mp_email"] = email_lower
                st.rerun()
