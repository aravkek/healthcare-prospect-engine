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
        if members:
            return members
        # Table exists but empty — fall back to hardcoded list
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
    except Exception:
        # Table doesn't exist yet — fall back gracefully
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
