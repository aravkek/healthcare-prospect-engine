"""
MedPort Cards — disciplinary card tracker.
Only admins can issue cards. All team members can view.
Grey x2 -> Yellow auto, Yellow x3 -> Red auto.
2 reds = Under Review, 3 reds = Removed.
"""

import os
import sys
from datetime import datetime, timezone

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import (
    inject_css, MEDPORT_BLUE, MEDPORT_GREEN, MEDPORT_TEAL, TEAM_MEMBERS,
    CARD_GREY, CARD_YELLOW, CARD_RED,
)
from lib.auth import check_auth, is_admin
from lib.db import get_cards, issue_card, get_card_summary, log_activity, get_team_members

st.set_page_config(
    page_title="Cards — MedPort",
    page_icon="🟨",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">Cards</span>',
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

    if st.button("Refresh data", use_container_width=True):
        get_cards.clear()
        get_card_summary.clear() if hasattr(get_card_summary, "clear") else None
        st.rerun()

# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown("# Disciplinary Cards")
st.markdown(
    f'<div style="color:#6b7a8d;font-size:0.88rem;margin-top:-0.6rem;margin-bottom:1.2rem;">'
    f'Accountability system for the MedPort founding team'
    f'</div>',
    unsafe_allow_html=True,
)

# ─── Card system rules ───────────────────────────────────────────────────────

with st.expander("Card System Rules", expanded=False):
    st.markdown("""
**Card Types:**
- **Grey card** — informal warning. Acknowledged minor issue, repeated tardiness, missed update.
- **Yellow card** — formal warning. Significant breach of team norms, missed deadline with no notice, conduct issue.
- **Red card** — serious warning. Repeated or severe breach. Requires immediate team discussion.

**Auto-Escalation Rules:**
- 2 active grey cards on the same member → a **Yellow card is automatically issued**
- 3 active yellow cards on the same member → a **Red card is automatically issued**

**Standing Thresholds:**
- 1 grey card → Grey Warning
- 2+ yellow cards → Yellow Warning
- 2 active red cards → **Under Review** (team meeting required)
- 3+ active red cards → **Removed** (membership revocation process)

Only Arav (admin) can issue cards. All team members can view their own and others' standing.
    """)

st.markdown("")

# ─── Team standing grid ──────────────────────────────────────────────────────

st.markdown(f"### Team Standing")

card_summary = get_card_summary()
_dynamic_members = get_team_members()

# Make sure all team members appear (even if no cards)
all_members = [m["name"] for m in _dynamic_members] if _dynamic_members else [m for m in TEAM_MEMBERS if m != "Unassigned"]
member_cols = st.columns(len(all_members))

STATUS_DISPLAY = {
    "good": ("Good Standing", "standing-good"),
    "grey_warning": ("Grey Warning", "standing-grey"),
    "yellow_warning": ("Yellow Warning", "standing-yellow"),
    "review": ("Under Review", "standing-review"),
    "removed": ("Removed", "standing-removed"),
}

for i, member in enumerate(all_members):
    # Get avatar color from dynamic member list
    member_avatar_color = MEDPORT_TEAL
    for dm in _dynamic_members:
        if dm["name"] == member:
            member_avatar_color = dm.get("avatar_color", MEDPORT_TEAL)
            break

    with member_cols[i]:
        # Find this member's summary by name (matching)
        member_data = None
        for em, data in card_summary.items():
            if data.get("name") == member:
                member_data = data
                break

        grey_n = member_data["grey"] if member_data else 0
        yellow_n = member_data["yellow"] if member_data else 0
        red_n = member_data["red"] if member_data else 0
        standing = member_data["status"] if member_data else "good"

        status_label, status_css = STATUS_DISPLAY.get(standing, ("Good Standing", "standing-good"))
        initials = "".join(w[0].upper() for w in member.split()[:2])

        st.markdown(
            f"""
            <div class="member-card">
              <div class="member-avatar" style="background:linear-gradient(135deg,{member_avatar_color},{MEDPORT_BLUE});">{initials}</div>
              <div class="member-name">{member}</div>
              <div style="margin: 0.5rem 0;">
                <span class="card-grey">Grey: {grey_n}</span>&nbsp;
                <span class="card-yellow">Yellow: {yellow_n}</span>&nbsp;
                <span class="card-red">Red: {red_n}</span>
              </div>
              <div><span class="{status_css}">{status_label}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ─── Issue Card form (admin only) ────────────────────────────────────────────

if admin:
    st.markdown(f"### Issue a Card")

    with st.container():
        ic_col1, ic_col2 = st.columns([2, 3])
        with ic_col1:
            ic_member = st.selectbox(
                "Team member *",
                [m["name"] for m in _dynamic_members] if _dynamic_members else [m for m in TEAM_MEMBERS if m != "Unassigned"],
                key="ic_member",
            )
            ic_type = st.selectbox(
                "Card type *",
                ["grey", "yellow", "red"],
                format_func=lambda t: {"grey": "Grey (informal warning)", "yellow": "Yellow (formal warning)", "red": "Red (serious breach)"}.get(t, t),
                key="ic_type",
            )
        with ic_col2:
            ic_reason = st.text_area(
                "Reason *",
                height=100,
                key="ic_reason",
                placeholder="Describe specifically what happened and why this card is being issued...",
            )

        if st.button("Issue Card", type="primary", key="do_issue_card"):
            if ic_reason.strip():
                # Look up member email from TEAM_EMAILS or use placeholder
                from lib.styles import TEAM_EMAILS
                import os as _os
                try:
                    team_email_map = {}
                    raw = st.secrets.get("TEAM_MEMBER_EMAILS", "")
                    if raw:
                        for pair in raw.split(","):
                            if ":" in pair:
                                k, v = pair.split(":", 1)
                                team_email_map[k.strip()] = v.strip()
                    team_email_map.update(TEAM_EMAILS)
                except Exception:
                    team_email_map = TEAM_EMAILS

                member_email_val = team_email_map.get(ic_member, f"{ic_member.lower().replace(' ', '.')}@medport.ca")

                card_dict = {
                    "member_email": member_email_val,
                    "member_name": ic_member,
                    "card_type": ic_type,
                    "reason": ic_reason.strip(),
                    "issued_by_email": email,
                    "issued_by_name": name,
                    "is_active": True,
                }
                card_id, escalation_msg = issue_card(card_dict)

                if card_id:
                    log_activity(
                        actor_email=email, actor_name=name,
                        action_type="card_issued", entity_type="card",
                        entity_id=card_id, entity_name=ic_member,
                        details={"card_type": ic_type, "reason": ic_reason.strip()},
                    )
                    st.success(f"{ic_type.capitalize()} card issued to {ic_member}.")
                    if escalation_msg:
                        st.warning(f"Auto-escalation: {escalation_msg}")
                    get_cards.clear()
                    st.rerun()
            else:
                st.warning("Please provide a reason for this card.")
else:
    st.info("Only admins can issue cards. Contact Arav if you believe a card should be issued.")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ─── Card History ────────────────────────────────────────────────────────────

st.markdown(f"### Card History")

all_cards = get_cards()

for member in all_members:
    member_cards = [c for c in all_cards if c.get("member_name") == member]
    if not member_cards:
        continue

    active_count = sum(1 for c in member_cards if c.get("is_active"))
    total_count = len(member_cards)

    with st.expander(f"{member} — {active_count} active card{'s' if active_count != 1 else ''} ({total_count} total)", expanded=False):
        for card in member_cards:
            card_type = card.get("card_type", "grey")
            reason = card.get("reason", "")
            issued_by = card.get("issued_by_name", "")
            created_at = card.get("created_at", "")
            is_active = card.get("is_active", True)
            auto_escalated = bool(card.get("auto_escalated_from"))

            try:
                ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                date_str = ts.strftime("%b %d, %Y at %I:%M %p")
            except Exception:
                date_str = created_at[:10] if created_at else ""

            type_color = {"grey": CARD_GREY, "yellow": CARD_YELLOW, "red": CARD_RED}.get(card_type, CARD_GREY)
            inactive_style = "opacity:0.5;" if not is_active else ""
            auto_badge = '<span style="font-size:0.7rem;background:#e8f4fd;color:#2980b9;padding:1px 7px;border-radius:10px;">Auto-escalated</span>' if auto_escalated else ""

            st.markdown(
                f"""
                <div style="border-left:3px solid {type_color};padding:0.5rem 0.7rem;margin:0.4rem 0;
                  background:#fafafa;border-radius:0 6px 6px 0;{inactive_style}">
                  <div style="display:flex;align-items:center;gap:0.5rem;">
                    <span class="card-{card_type}">{card_type.upper()}</span>
                    {auto_badge}
                    <span style="font-size:0.72rem;color:#8a9ab0;margin-left:auto;">{date_str}</span>
                  </div>
                  <div style="font-size:0.85rem;color:#1a2a3a;margin-top:0.3rem;">{reason}</div>
                  <div style="font-size:0.72rem;color:#6b7a8d;margin-top:0.2rem;">Issued by {issued_by}</div>
                  {"<div style='font-size:0.7rem;color:#8a9ab0;font-style:italic;'>Inactive</div>" if not is_active else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )
