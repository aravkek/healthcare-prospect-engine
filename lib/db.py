"""
MedPort database layer — all Supabase operations.
All functions fail gracefully and log warnings rather than crashing pages.
"""

import os
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st


# ─── Client ─────────────────────────────────────────────────────────────────

def _secret(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


@st.cache_resource
def get_client():
    """Return cached Supabase client. Returns None if not configured."""
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        st.warning(f"Supabase client init failed: {e}")
        return None


# ─── Prospects ───────────────────────────────────────────────────────────────

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "medport_prospects.csv")


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    int_cols = ["innovation_score", "accessibility_score", "fit_score",
                "startup_receptiveness", "priority_rank", "outreach_count"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    str_cols = ["competitor_risk", "emr_system", "patient_volume", "existing_ai_tools",
                "phone_intake_evidence", "score_breakdown", "contact_notes",
                "research_notes", "outreach_angle"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna("")
        else:
            df[col] = ""

    if "country" in df.columns:
        df["country"] = df["country"].fillna("").str.upper()
    if "inst_type" in df.columns:
        df["inst_type"] = df["inst_type"].fillna("unknown")
    if "competitor_risk" in df.columns:
        df["competitor_risk"] = df["competitor_risk"].fillna("none")

    df["composite_score"] = (
        df.get("innovation_score", pd.Series(0, index=df.index)).fillna(0).astype(int)
        + df.get("accessibility_score", pd.Series(0, index=df.index)).fillna(0).astype(int)
        + df.get("fit_score", pd.Series(0, index=df.index)).fillna(0).astype(int)
        + df.get("startup_receptiveness", pd.Series(0, index=df.index)).fillna(0).astype(int)
    )

    if "status" not in df.columns:
        df["status"] = "not_contacted"
    else:
        status_map = {"contacted": "email_sent", "responded": "pending_response",
                      "meeting_booked": "demo_booked"}
        df["status"] = df["status"].fillna("not_contacted").replace(status_map)

    if "assigned_to" not in df.columns:
        df["assigned_to"] = "Unassigned"
    else:
        df["assigned_to"] = df["assigned_to"].fillna("Unassigned")

    if "id" not in df.columns:
        df["id"] = df.index.astype(str)

    return df


@st.cache_data(ttl=30)
def load_prospects() -> pd.DataFrame:
    """Returns normalized DataFrame from Supabase, falling back to CSV."""
    client = get_client()
    if client is None:
        if os.path.exists(CSV_PATH):
            return _normalize_df(pd.read_csv(CSV_PATH))
        return pd.DataFrame()

    try:
        result = (
            client.table("prospects")
            .select("*")
            .order("priority_rank")
            .order("composite_score", desc=True)
            .execute()
        )
        if not result.data:
            if os.path.exists(CSV_PATH):
                return _normalize_df(pd.read_csv(CSV_PATH))
            return pd.DataFrame()
        return _normalize_df(pd.DataFrame(result.data))
    except Exception as e:
        st.warning(f"Supabase load failed, falling back to CSV: {e}")
        if os.path.exists(CSV_PATH):
            return _normalize_df(pd.read_csv(CSV_PATH))
        return pd.DataFrame()


def update_prospect(prospect_id: str, updates: dict) -> bool:
    """Update CRM fields for a prospect. Returns True on success."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("prospects").update(updates).eq("id", prospect_id).execute()
        return True
    except Exception as e:
        st.error(f"Failed to update prospect: {e}")
        return False


# ─── Activity Log ────────────────────────────────────────────────────────────

def log_activity(
    actor_email: str,
    actor_name: str,
    action_type: str,
    entity_type: str,
    entity_id: str = "",
    entity_name: str = "",
    details: dict | None = None,
) -> bool:
    """Insert a row into activity_log. Silently fails if Supabase unavailable."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("activity_log").insert({
            "actor_email": actor_email,
            "actor_name": actor_name,
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": entity_id or "",
            "entity_name": entity_name or "",
            "details": details or {},
        }).execute()
        return True
    except Exception:
        return False


@st.cache_data(ttl=15)
def get_activity_feed(limit: int = 50) -> list[dict]:
    """Returns most recent activities, newest first."""
    client = get_client()
    if client is None:
        return []
    try:
        result = (
            client.table("activity_log")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


# ─── Tasks ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=20)
def get_tasks(assigned_to_email: str | None = None) -> list[dict]:
    """Returns list of task dicts. If assigned_to_email given, filter to that user."""
    client = get_client()
    if client is None:
        return []
    try:
        query = client.table("tasks").select("*").order("created_at", desc=True)
        result = query.execute()
        tasks = result.data or []
        if assigned_to_email:
            tasks = [t for t in tasks if assigned_to_email in (t.get("assigned_to") or [])]
        return tasks
    except Exception as e:
        st.warning(f"Could not load tasks: {e}")
        return []


def create_task(task_dict: dict) -> str | None:
    """Insert a new task. Returns the new task ID or None on failure."""
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("tasks").insert(task_dict).execute()
        if result.data:
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to create task: {e}")
        return None


def update_task(task_id: str, updates: dict) -> bool:
    """Update task fields. Returns True on success."""
    client = get_client()
    if client is None:
        return False
    try:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        client.table("tasks").update(updates).eq("id", task_id).execute()
        return True
    except Exception as e:
        st.error(f"Failed to update task: {e}")
        return False


# ─── Team Goals ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=20)
def get_goals() -> list[dict]:
    """Returns list of goal dicts."""
    client = get_client()
    if client is None:
        return []
    try:
        result = (
            client.table("team_goals")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def create_goal(goal_dict: dict) -> str | None:
    """Insert a new goal. Returns the new goal ID or None."""
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("team_goals").insert(goal_dict).execute()
        if result.data:
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to create goal: {e}")
        return None


def update_goal(goal_id: str, updates: dict) -> bool:
    """Update goal fields. Returns True on success."""
    client = get_client()
    if client is None:
        return False
    try:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        client.table("team_goals").update(updates).eq("id", goal_id).execute()
        return True
    except Exception as e:
        st.error(f"Failed to update goal: {e}")
        return False


# ─── Cards ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=20)
def get_cards(member_email: str | None = None) -> list[dict]:
    """Returns list of card dicts. Optionally filter by member_email."""
    client = get_client()
    if client is None:
        return []
    try:
        query = client.table("team_cards").select("*").order("created_at", desc=True)
        result = query.execute()
        cards = result.data or []
        if member_email:
            cards = [c for c in cards if c.get("member_email") == member_email]
        return cards
    except Exception:
        return []


def issue_card(card_dict: dict) -> tuple[str | None, str | None]:
    """
    Insert a card and handle auto-escalation.
    Returns (card_id, escalation_message).
    escalation_message is None if no escalation triggered.

    Rules:
    - 2+ active grey cards on same member → auto-issue yellow
    - 3+ active yellow cards on same member → auto-issue red
    - 2 active red cards → status becomes 'internal_review'
    - 3+ active red cards → status becomes 'removed'
    """
    client = get_client()
    if client is None:
        return None, None

    member_email = card_dict.get("member_email", "")
    member_name = card_dict.get("member_name", "")
    card_type = card_dict.get("card_type", "grey")

    try:
        result = client.table("team_cards").insert(card_dict).execute()
        if not result.data:
            return None, None
        card_id = result.data[0].get("id")
    except Exception as e:
        st.error(f"Failed to issue card: {e}")
        return None, None

    # Count active cards for this member (reload fresh)
    escalation_message = None
    try:
        active_result = (
            client.table("team_cards")
            .select("card_type, id")
            .eq("member_email", member_email)
            .eq("is_active", True)
            .execute()
        )
        active_cards = active_result.data or []
        grey_count = sum(1 for c in active_cards if c["card_type"] == "grey")
        yellow_count = sum(1 for c in active_cards if c["card_type"] == "yellow")
        red_count = sum(1 for c in active_cards if c["card_type"] == "red")

        # Auto-escalation: grey → yellow
        if card_type == "grey" and grey_count >= 2:
            escalation_card = {
                "member_email": member_email,
                "member_name": member_name,
                "card_type": "yellow",
                "reason": f"Auto-escalated: {grey_count} grey cards accumulated",
                "issued_by_email": card_dict.get("issued_by_email", "system"),
                "issued_by_name": "System (Auto-escalation)",
                "is_active": True,
                "auto_escalated_from": card_id,
            }
            client.table("team_cards").insert(escalation_card).execute()
            yellow_count += 1
            escalation_message = (
                f"Grey card escalation: {member_name} now has {grey_count} grey cards — "
                f"a Yellow card was automatically issued."
            )

        # Auto-escalation: yellow → red
        if (card_type in ("yellow",) or escalation_message) and yellow_count >= 3:
            escalation_card = {
                "member_email": member_email,
                "member_name": member_name,
                "card_type": "red",
                "reason": f"Auto-escalated: {yellow_count} yellow cards accumulated",
                "issued_by_email": card_dict.get("issued_by_email", "system"),
                "issued_by_name": "System (Auto-escalation)",
                "is_active": True,
                "auto_escalated_from": card_id,
            }
            client.table("team_cards").insert(escalation_card).execute()
            red_count += 1
            msg = f"{member_name} now has {yellow_count} yellow cards — a Red card was automatically issued."
            escalation_message = (escalation_message + " | " + msg) if escalation_message else msg

        # Red card status checks
        if red_count >= 3:
            msg = f"ALERT: {member_name} has {red_count} red cards — status is REMOVED. Review required."
            escalation_message = (escalation_message + " | " + msg) if escalation_message else msg
        elif red_count >= 2:
            msg = f"WARNING: {member_name} has {red_count} red cards — status is UNDER REVIEW."
            escalation_message = (escalation_message + " | " + msg) if escalation_message else msg

    except Exception:
        pass  # Escalation check failed silently — card was still issued

    # Invalidate cache
    get_cards.clear()
    return card_id, escalation_message


def get_card_summary() -> dict[str, dict]:
    """
    Returns {email: {name, grey, yellow, red, status}} for all members with cards.
    Status: 'good' | 'grey_warning' | 'yellow_warning' | 'review' | 'removed'
    """
    cards = get_cards()
    summary: dict[str, dict] = {}

    for card in cards:
        if not card.get("is_active"):
            continue
        email = card.get("member_email", "")
        name = card.get("member_name", "")
        if email not in summary:
            summary[email] = {"name": name, "grey": 0, "yellow": 0, "red": 0, "status": "good"}
        summary[email][card.get("card_type", "grey")] += 1

    # Compute status
    for email, data in summary.items():
        red = data["red"]
        yellow = data["yellow"]
        grey = data["grey"]
        if red >= 3:
            data["status"] = "removed"
        elif red >= 2:
            data["status"] = "review"
        elif yellow >= 2:
            data["status"] = "yellow_warning"
        elif grey >= 1:
            data["status"] = "grey_warning"
        else:
            data["status"] = "good"

    return summary


def delete_card(card_id: str) -> bool:
    """Hard-delete a card by ID. Admin only — enforced at page level. Returns True on success."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("team_cards").delete().eq("id", card_id).execute()
        get_cards.clear()
        return True
    except Exception as e:
        st.error(f"Failed to delete card: {e}")
        return False


# ─── Saved Searches ───────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def get_saved_searches(owner_email: str) -> list[dict]:
    """Returns personal saved searches + team-shared searches for this user."""
    client = get_client()
    if client is None:
        return []
    try:
        # Personal searches
        personal = (
            client.table("saved_searches")
            .select("*")
            .eq("owner_email", owner_email)
            .order("use_count", desc=True)
            .execute()
        )
        # Team-shared (from others)
        shared = (
            client.table("saved_searches")
            .select("*")
            .eq("is_team_shared", True)
            .neq("owner_email", owner_email)
            .order("use_count", desc=True)
            .execute()
        )
        # Combine, deduplicate by id
        results = {r["id"]: r for r in (personal.data or []) + (shared.data or [])}
        return list(results.values())
    except Exception:
        return []


def save_search(search_dict: dict) -> str | None:
    """Insert a saved search. Returns the new ID or None."""
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("saved_searches").insert(search_dict).execute()
        if result.data:
            get_saved_searches.clear()
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to save search: {e}")
        return None


def delete_saved_search(search_id: str) -> bool:
    """Delete a saved search. Returns True on success."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("saved_searches").delete().eq("id", search_id).execute()
        get_saved_searches.clear()
        return True
    except Exception:
        return False


def increment_search_use_count(search_id: str):
    """Bump use_count on a saved search."""
    client = get_client()
    if client is None:
        return
    try:
        # Fetch current count then increment (Supabase anon doesn't support rpc easily)
        result = client.table("saved_searches").select("use_count").eq("id", search_id).execute()
        if result.data:
            current = result.data[0].get("use_count", 0) or 0
            client.table("saved_searches").update({"use_count": current + 1}).eq("id", search_id).execute()
    except Exception:
        pass


# ─── Team Members ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def get_team_members() -> list[dict]:
    """
    Returns team members from Supabase team_members table, ordered by sort_order.
    Falls back to hardcoded TEAM_MEMBERS from styles.py if the table doesn't exist or is empty.
    Each member dict: {id, name, role, email, avatar_color, is_active, sort_order}
    """
    from lib.styles import TEAM_MEMBERS, MEDPORT_TEAL

    client = get_client()
    if client is None:
        # Fallback to hardcoded list
        return [
            {
                "id": str(i),
                "name": m,
                "role": "Team Member",
                "email": "",
                "avatar_color": MEDPORT_TEAL,
                "is_active": True,
                "sort_order": i,
            }
            for i, m in enumerate(TEAM_MEMBERS)
            if m != "Unassigned"
        ]

    try:
        result = (
            client.table("team_members")
            .select("*")
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        members = result.data or []
        # Return DB results only — even if empty. Never return fake integer IDs
        # when the table exists, as those break UUID-typed update calls.
        return members
    except Exception:
        # Table doesn't exist yet — fall back gracefully with fake IDs
        # (read-only display only; edits will fail until table is created)
        from lib.styles import TEAM_MEMBERS, MEDPORT_TEAL
        return [
            {
                "id": str(i),
                "name": m,
                "role": "Team Member",
                "email": "",
                "avatar_color": MEDPORT_TEAL,
                "is_active": True,
                "sort_order": i,
            }
            for i, m in enumerate(TEAM_MEMBERS)
            if m != "Unassigned"
        ]


def create_team_member(member_dict: dict) -> str | None:
    """Insert a new team member. Returns the new member ID or None on failure."""
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("team_members").insert(member_dict).execute()
        if result.data:
            get_team_members.clear()
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to create team member: {e}")
        return None


def update_team_member(member_id: str, updates: dict) -> bool:
    """Update team member fields. Returns True on success."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("team_members").update(updates).eq("id", member_id).execute()
        get_team_members.clear()
        return True
    except Exception as e:
        st.error(f"Failed to update team member: {e}")
        return False


def delete_team_member(member_id: str) -> bool:
    """Soft-delete a team member (set is_active=False). Returns True on success."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("team_members").update({"is_active": False}).eq("id", member_id).execute()
        get_team_members.clear()
        return True
    except Exception as e:
        st.error(f"Failed to remove team member: {e}")
        return False


def get_member_by_email(email: str) -> dict:
    """Returns team_members row for email, or {} if not found."""
    client = get_client()
    if client is None:
        return {}
    try:
        result = (
            client.table("team_members")
            .select("*")
            .eq("email", (email or "").lower().strip())
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return {}
    except Exception:
        return {}


@st.cache_data(ttl=20)
def get_tasks_by_department(department: str) -> list[dict]:
    """Returns tasks filtered by department."""
    client = get_client()
    if client is None:
        return []
    try:
        result = (
            client.table("tasks")
            .select("*")
            .eq("department", department)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


# ─── Announcements ────────────────────────────────────────────────────────────

@st.cache_data(ttl=15)
def get_announcements(active_only: bool = True) -> list[dict]:
    """Returns announcements, newest first."""
    client = get_client()
    if client is None:
        return []
    try:
        query = client.table("announcements").select("*").order("created_at", desc=True)
        if active_only:
            query = query.eq("is_active", True)
        result = query.execute()
        return result.data or []
    except Exception:
        return []


def create_announcement(ann_dict: dict) -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("announcements").insert(ann_dict).execute()
        if result.data:
            get_announcements.clear()
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to create announcement: {e}")
        return None


def update_announcement(ann_id: str, updates: dict) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.table("announcements").update(updates).eq("id", ann_id).execute()
        get_announcements.clear()
        return True
    except Exception as e:
        st.error(f"Failed to update announcement: {e}")
        return False


def get_unread_announcement_count(email: str) -> int:
    """Returns count of active announcements not yet read by this email."""
    client = get_client()
    if client is None:
        return 0
    try:
        all_active = get_announcements(active_only=True)
        if not all_active:
            return 0
        ann_ids = [a["id"] for a in all_active]
        read_result = (
            client.table("announcement_reads")
            .select("announcement_id")
            .eq("email", email.lower())
            .execute()
        )
        read_ids = {r["announcement_id"] for r in (read_result.data or [])}
        return sum(1 for aid in ann_ids if aid not in read_ids)
    except Exception:
        return 0


def mark_announcement_read(ann_id: str, email: str) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.table("announcement_reads").upsert({
            "announcement_id": ann_id,
            "email": email.lower(),
        }).execute()
        return True
    except Exception:
        return False


# ─── Standups ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=20)
def get_standups(limit: int = 50, author_email: str | None = None) -> list[dict]:
    """Returns standup logs, newest first. Optionally filtered by author."""
    client = get_client()
    if client is None:
        return []
    try:
        query = (
            client.table("standup_logs")
            .select("*")
            .order("submitted_at", desc=True)
            .limit(limit)
        )
        result = query.execute()
        logs = result.data or []
        if author_email:
            logs = [s for s in logs if s.get("author_email") == author_email.lower()]
        return logs
    except Exception:
        return []


def submit_standup(standup_dict: dict) -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("standup_logs").insert(standup_dict).execute()
        if result.data:
            get_standups.clear()
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to submit standup: {e}")
        return None


def get_today_standup(author_email: str) -> dict | None:
    """Returns today's standup for this author, or None."""
    from datetime import date
    client = get_client()
    if client is None:
        return None
    try:
        today = date.today().isoformat()
        result = (
            client.table("standup_logs")
            .select("*")
            .eq("author_email", author_email.lower())
            .eq("date", today)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


# ─── Wiki ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def get_wiki_pages(category: str | None = None) -> list[dict]:
    """Returns wiki pages, newest first. Optionally filtered by category."""
    client = get_client()
    if client is None:
        return []
    try:
        query = client.table("wiki_pages").select("*").order("updated_at", desc=True)
        result = query.execute()
        pages = result.data or []
        if category:
            pages = [p for p in pages if p.get("category") == category]
        return pages
    except Exception:
        return []


def create_wiki_page(page_dict: dict) -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("wiki_pages").insert(page_dict).execute()
        if result.data:
            get_wiki_pages.clear()
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to create wiki page: {e}")
        return None


def update_wiki_page(page_id: str, updates: dict) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        client.table("wiki_pages").update(updates).eq("id", page_id).execute()
        get_wiki_pages.clear()
        return True
    except Exception as e:
        st.error(f"Failed to update wiki page: {e}")
        return False


# ─── Notifications ────────────────────────────────────────────────────────────

@st.cache_data(ttl=10)
def get_notifications(recipient_email: str, unread_only: bool = False) -> list[dict]:
    """Returns notifications for a user, newest first."""
    client = get_client()
    if client is None:
        return []
    try:
        query = (
            client.table("notifications")
            .select("*")
            .eq("recipient_email", recipient_email.lower())
            .order("created_at", desc=True)
            .limit(50)
        )
        if unread_only:
            query = query.eq("is_read", False)
        result = query.execute()
        return result.data or []
    except Exception:
        return []


def create_notification(notif_dict: dict) -> bool:
    """Insert a notification. Silently fails — notifications are best-effort."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("notifications").insert(notif_dict).execute()
        return True
    except Exception:
        return False


def mark_notification_read(notif_id: str) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.table("notifications").update({"is_read": True}).eq("id", notif_id).execute()
        get_notifications.clear()
        return True
    except Exception:
        return False


def mark_all_notifications_read(recipient_email: str) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.table("notifications").update({"is_read": True}).eq(
            "recipient_email", recipient_email.lower()
        ).eq("is_read", False).execute()
        get_notifications.clear()
        return True
    except Exception:
        return False


def get_unread_notification_count(recipient_email: str) -> int:
    """Returns count of unread notifications. Cached."""
    notifs = get_notifications(recipient_email, unread_only=True)
    return len(notifs)


# ─── Task Comments ────────────────────────────────────────────────────────────

@st.cache_data(ttl=15)
def get_task_comments(task_id: str) -> list[dict]:
    client = get_client()
    if client is None:
        return []
    try:
        result = (
            client.table("task_comments")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at")
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def add_task_comment(comment_dict: dict) -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("task_comments").insert(comment_dict).execute()
        if result.data:
            get_task_comments.clear()
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to add comment: {e}")
        return None


# ─── One-on-Ones ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def get_one_on_ones(member_email: str | None = None) -> list[dict]:
    """Returns 1-on-1 records, newest first."""
    client = get_client()
    if client is None:
        return []
    try:
        query = client.table("one_on_ones").select("*").order("scheduled_date", desc=True)
        result = query.execute()
        records = result.data or []
        if member_email:
            records = [r for r in records if r.get("member_email") == member_email.lower()]
        return records
    except Exception:
        return []


def create_one_on_one(record_dict: dict) -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("one_on_ones").insert(record_dict).execute()
        if result.data:
            get_one_on_ones.clear()
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to create 1-on-1: {e}")
        return None


def update_one_on_one(record_id: str, updates: dict) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.table("one_on_ones").update(updates).eq("id", record_id).execute()
        get_one_on_ones.clear()
        return True
    except Exception as e:
        st.error(f"Failed to update 1-on-1: {e}")
        return False


# ─── Messages (Team Chat) ─────────────────────────────────────────────────────

def _dm_channel(email_a: str, email_b: str) -> str:
    """Stable channel ID for a DM between two emails (alphabetically sorted)."""
    return "dm:" + ":".join(sorted([email_a.lower(), email_b.lower()]))


@st.cache_data(ttl=5)
def get_messages(channel: str, limit: int = 100) -> list[dict]:
    """Returns messages for a channel, oldest first."""
    client = get_client()
    if client is None:
        return []
    try:
        result = (
            client.table("messages")
            .select("*")
            .eq("channel", channel)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def send_message(channel: str, sender_email: str, sender_name: str, content: str) -> bool:
    """Insert a new message. Returns True on success."""
    content = content.strip()[:2000]
    if not content:
        return False
    client = get_client()
    if client is None:
        return False
    try:
        client.table("messages").insert({
            "channel": channel,
            "sender_email": sender_email.lower(),
            "sender_name": sender_name,
            "content": content,
        }).execute()
        get_messages.clear()
        return True
    except Exception:
        return False


def get_dm_channel(email_a: str, email_b: str) -> str:
    return _dm_channel(email_a, email_b)


# ─── Sprints ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=20)
def get_sprints(status: str | None = None) -> list[dict]:
    """Returns sprints, newest first. Optionally filter by status."""
    client = get_client()
    if client is None:
        return []
    try:
        query = client.table("sprints").select("*").order("created_at", desc=True)
        result = query.execute()
        sprints = result.data or []
        if status:
            sprints = [s for s in sprints if s.get("status") == status]
        return sprints
    except Exception:
        return []


def get_active_sprint() -> dict | None:
    """Returns the most recent active sprint, or None."""
    sprints = get_sprints(status="active")
    return sprints[0] if sprints else None


def create_sprint(sprint_dict: dict) -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        result = client.table("sprints").insert(sprint_dict).execute()
        if result.data:
            get_sprints.clear()
            return result.data[0].get("id")
        return None
    except Exception as e:
        st.error(f"Failed to create sprint: {e}")
        return None


def update_sprint(sprint_id: str, updates: dict) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.table("sprints").update(updates).eq("id", sprint_id).execute()
        get_sprints.clear()
        return True
    except Exception as e:
        st.error(f"Failed to update sprint: {e}")
        return False


@st.cache_data(ttl=15)
def get_sprint_tasks(sprint_id: str) -> list[dict]:
    """Returns all tasks assigned to a sprint."""
    client = get_client()
    if client is None:
        return []
    try:
        result = (
            client.table("tasks")
            .select("*")
            .eq("sprint_id", sprint_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def get_my_sprint_tasks(sprint_id: str, email: str) -> list[dict]:
    """Returns sprint tasks assigned to a specific email."""
    tasks = get_sprint_tasks(sprint_id)
    return [t for t in tasks if email.lower() in [a.lower() for a in (t.get("assigned_to") or [])]]


# ─── Prospect enrichment ──────────────────────────────────────────────────────

def save_prospect_research(
    prospect_id: str,
    research_brief: str | None = None,
    dm_research: str | None = None,
    fit_analysis: str | None = None,
) -> bool:
    """Save AI-generated research fields to a prospect. Only updates non-None fields."""
    client = get_client()
    if client is None:
        return False
    updates: dict = {"research_updated_at": datetime.now(timezone.utc).isoformat()}
    if research_brief is not None:
        updates["research_brief"] = research_brief
    if dm_research is not None:
        updates["dm_research"] = dm_research
    if fit_analysis is not None:
        updates["fit_analysis"] = fit_analysis
    try:
        client.table("prospects").update(updates).eq("id", prospect_id).execute()
        load_prospects.clear()
        return True
    except Exception as e:
        st.error(f"Failed to save research: {e}")
        return False


def add_email_draft(prospect_id: str, subject: str, body: str, variant: int = 1) -> bool:
    """Append an email draft to a prospect's email_drafts JSONB array."""
    client = get_client()
    if client is None:
        return False
    try:
        # Fetch existing drafts
        result = client.table("prospects").select("email_drafts").eq("id", prospect_id).execute()
        existing = (result.data or [{}])[0].get("email_drafts") or []
        new_draft = {
            "id": str(datetime.now(timezone.utc).timestamp()),
            "subject": subject,
            "body": body,
            "variant": variant,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        existing.append(new_draft)
        client.table("prospects").update({"email_drafts": existing}).eq("id", prospect_id).execute()
        load_prospects.clear()
        return True
    except Exception as e:
        st.error(f"Failed to save email draft: {e}")
        return False


def log_outreach_event(
    prospect_id: str,
    event_type: str,
    subject: str = "",
    notes: str = "",
    outcome: str = "",
    logged_by: str = "",
) -> bool:
    """Append an outreach event to a prospect's outreach_timeline JSONB array."""
    client = get_client()
    if client is None:
        return False
    try:
        result = client.table("prospects").select("outreach_timeline").eq("id", prospect_id).execute()
        existing = (result.data or [{}])[0].get("outreach_timeline") or []
        event = {
            "date": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "subject": subject,
            "notes": notes,
            "outcome": outcome,
            "logged_by": logged_by,
        }
        existing.append(event)
        updates = {
            "outreach_timeline": existing,
            "last_contacted_at": datetime.now(timezone.utc).isoformat(),
        }
        client.table("prospects").update(updates).eq("id", prospect_id).execute()
        load_prospects.clear()
        return True
    except Exception as e:
        st.error(f"Failed to log outreach event: {e}")
        return False


def get_prospect_by_id(prospect_id: str) -> dict:
    """Fetch a single prospect by ID, all fields."""
    client = get_client()
    if client is None:
        return {}
    try:
        result = client.table("prospects").select("*").eq("id", str(prospect_id)).limit(1).execute()
        return result.data[0] if result.data else {}
    except Exception:
        return {}
