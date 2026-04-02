"""
MedPort AI Research — Operations Manager chatbot, Email Factory, Quick Research, Prospect Deep Dive.
Model: claude-sonnet-4-6
API key from st.secrets["ANTHROPIC_API_KEY"] or ANTHROPIC_API_KEY env var.
"""

import os
import sys
import time
import json
import re
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import (
    inject_css, MEDPORT_BLUE, MEDPORT_TEAL, MEDPORT_DARK,
    MEDPORT_LIGHT_TEAL, STATUS_LABELS,
)
from lib.auth import check_auth, is_admin, render_logout_button
from lib.db import load_prospects, get_tasks, create_task
from lib.ai import call_ai, has_ai_configured, ai_provider_badge, MODEL

st.set_page_config(
    page_title="AI Research — MedPort",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)

# ─── System prompts ──────────────────────────────────────────────────────────

OPS_SYSTEM_PROMPT = f"""You are MedPort's AI Operations Manager — a senior strategic advisor embedded in the team's command center. You have full context on MedPort's business, the prospect database, team tasks, and pipeline.

MedPort builds AI voice agents for clinic phone intake (appointment booking, triage, intake). 5-person founding team. Targeting YC W27. Key upcoming demos: Flemingdon Health Centre (April 8), McMaster Wellness Centre.

Known competitors to help avoid: Care Cru (dental), Novoflow (primary care), Medi (walk-ins), Decoda Health (CHCs), Waive Medical (specialty).

Your capabilities:
- Analyze the prospect pipeline and give specific recommendations
- Draft cold emails tailored to specific institutions
- Suggest which prospects to prioritize this week
- Identify deal-killing risks in specific prospects
- Generate research on any clinic or institution
- Create tasks for team members (respond with a structured task JSON the app can parse)
- Write outreach sequences (email 1, follow-up 1, follow-up 2)
- Identify patterns across the pipeline

When creating tasks, format them as:
<TASK>{{"title": "...", "assigned_to": ["{name}"], "priority": "high", "due_date": "YYYY-MM-DD", "description": "..."}}</TASK>

Always be direct, specific, and tactical. No corporate speak. Talk like a sharp startup advisor."""

RESEARCH_SYSTEM_PROMPT = """You are MedPort's internal AI assistant. MedPort builds AI voice agents that handle incoming patient calls for clinics — handling appointment booking, intake, and triage. The team is a 5-person founding team targeting YC W27.

You help with:
- Outreach research and prospect analysis
- Email drafting for cold outreach
- Strategy and pipeline questions
- Answering questions about the prospect database
- Suggesting new prospect targets similar to existing ones

When drafting emails, be concise, warm, and focus on the specific pain points of clinic phone intake (missed calls, after-hours calls, front desk overload, appointment no-shows). Emphasize that MedPort handles the whole call — not just transcription or scheduling.

Always be direct and useful. If asked about the prospect database, analyze the data provided and give specific, actionable answers."""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _df_summary(df) -> str:
    if df.empty:
        return "No prospect data available."
    lines = [f"Total prospects: {len(df)}"]
    if "status" in df.columns:
        lines.append("Status breakdown:")
        for status, count in df["status"].value_counts().items():
            lines.append(f"  - {STATUS_LABELS.get(status, status)}: {count}")
    if "country" in df.columns:
        ca = len(df[df["country"] == "CA"])
        us = len(df[df["country"] == "US"])
        lines.append(f"Markets: {ca} Canada, {us} US")
    if "priority_rank" in df.columns:
        tier_a = len(df[df["priority_rank"] == 1])
        tier_b = len(df[df["priority_rank"] == 2])
        lines.append(f"Tiers: {tier_a} Tier A, {tier_b} Tier B")
    return "\n".join(lines)


def _prospect_context(df, prospect_name: str) -> str:
    if df.empty:
        return "No data available."
    match = df[df["name"].str.lower() == prospect_name.lower()]
    if match.empty:
        match = df[df["name"].str.lower().str.contains(prospect_name.lower(), na=False)]
    if match.empty:
        return f"No prospect found matching '{prospect_name}'."
    row = match.iloc[0]
    lines = []
    for col in row.index:
        val = row[col]
        if val and str(val) not in ("nan", "0", ""):
            lines.append(f"{col}: {val}")
    return "\n".join(lines)


def _extract_tasks(text: str) -> list[dict]:
    """Extract <TASK>{...}</TASK> blocks from Claude response."""
    pattern = r"<TASK>(.*?)</TASK>"
    matches = re.findall(pattern, text, re.DOTALL)
    tasks = []
    for m in matches:
        try:
            tasks.append(json.loads(m.strip()))
        except Exception:
            pass
    return tasks


def _stream_text(text: str, placeholder, delay: float = 0.012):
    """Simulate streaming by revealing text word by word."""
    words = text.split(" ")
    displayed = ""
    for i, word in enumerate(words):
        displayed += word + " "
        if i % 5 == 0:  # update every 5 words for speed
            placeholder.markdown(
                f'<div class="chat-msg-assistant">{displayed}</div>',
                unsafe_allow_html=True,
            )
            time.sleep(delay)
    placeholder.markdown(
        f'<div class="chat-msg-assistant">{text}</div>',
        unsafe_allow_html=True,
    )


# ─── Load data ───────────────────────────────────────────────────────────────

df = load_prospects()
tasks = get_tasks()

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">AI Research</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='font-size:0.8rem;color:#94a3b8;'>{name}</div>", unsafe_allow_html=True)
    st.markdown("---")

    render_logout_button()

    st.markdown("---")
    provider = ai_provider_badge()
    if "Claude" in provider:
        st.markdown(
            f'<span style="background:{MEDPORT_TEAL};color:#fff;border-radius:6px;padding:2px 10px;font-size:0.75rem;font-weight:700;">Claude Sonnet</span>',
            unsafe_allow_html=True,
        )
    elif "Groq" in provider:
        st.markdown(
            '<span style="background:#f59e0b;color:#fff;border-radius:6px;padding:2px 10px;font-size:0.75rem;font-weight:700;">Groq Fallback Active</span>',
            unsafe_allow_html=True,
        )
        st.caption("Add ANTHROPIC_API_KEY for Claude Sonnet.")
    else:
        st.markdown(
            '<span style="background:#fef2f2;color:#991b1b;border-radius:6px;padding:2px 10px;font-size:0.75rem;font-weight:700;">No AI Key</span>',
            unsafe_allow_html=True,
        )
        st.caption("Add ANTHROPIC_API_KEY (or GROQ_API_KEY as fallback) to Streamlit secrets.")

# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown(
    f'<div style="font-size:1.9rem;font-weight:800;color:{MEDPORT_DARK};font-family:Syne,sans-serif;margin-bottom:0.2rem;">AI Research Assistant</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div style="color:#64748b;font-size:0.88rem;margin-bottom:1.3rem;">Powered by Claude {MODEL} &nbsp;·&nbsp; Operations manager, email factory, research, and prospect deep dives</div>',
    unsafe_allow_html=True,
)

# ─── Tabs ────────────────────────────────────────────────────────────────────

tab_ops, tab_email, tab_quick, tab_deepdive = st.tabs([
    "Operations Manager",
    "Email Factory",
    "Quick Research",
    "Prospect Deep Dive",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1: Operations Manager (upgraded chatbot)
# ═════════════════════════════════════════════════════════════════════════════

with tab_ops:
    # ── Context panel ──────────────────────────────────────────────────────
    total_prospects = len(df) if not df.empty else 0
    demos_booked = int(len(df[df["status"] == "demo_booked"])) if not df.empty else 0
    converted = int(len(df[df["status"] == "converted"])) if not df.empty else 0
    open_tasks_count = sum(1 for t in tasks if t.get("status") in ("open", "in_progress"))
    not_contacted = int(len(df[df["status"] == "not_contacted"])) if not df.empty else 0

    with st.expander("What I know about MedPort right now", expanded=False):
        ctx_cols = st.columns(5)
        for col, val, label in [
            (ctx_cols[0], total_prospects, "Total Prospects"),
            (ctx_cols[1], demos_booked, "Demos Booked"),
            (ctx_cols[2], converted, "Converted"),
            (ctx_cols[3], open_tasks_count, "Open Tasks"),
            (ctx_cols[4], not_contacted, "Not Contacted"),
        ]:
            with col:
                st.markdown(
                    f'<div class="stat-card"><div class="stat-value">{val}</div><div class="stat-label">{label}</div></div>',
                    unsafe_allow_html=True,
                )
        st.markdown("")
        st.caption("Upcoming demos: Flemingdon Health Centre (April 8), McMaster Wellness Centre")

    st.markdown("")

    # ── Two-column layout: quick actions + chat ────────────────────────────
    col_actions, col_chat = st.columns([1, 3])

    with col_actions:
        st.markdown(
            f'<div style="font-size:0.8rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.6rem;text-transform:uppercase;letter-spacing:0.06em;">Quick Actions</div>',
            unsafe_allow_html=True,
        )

        quick_actions = [
            "What should we focus on this week?",
            "Who on the team has the most open tasks?",
            "Analyze our biggest pipeline risks",
            "Which prospects haven't been contacted in 2+ weeks?",
            "What's our win rate for CHCs?",
            "Write a follow-up email for a prospect that didn't respond",
        ]

        # Prospect dropdown for outreach draft
        if not df.empty:
            prospect_names = sorted(df["name"].dropna().unique().tolist())
            sel_prospect_for_outreach = st.selectbox(
                "Draft outreach for",
                ["— select —"] + prospect_names,
                key="ops_prospect_select",
            )
            if st.button("Draft outreach", key="ops_draft_outreach", use_container_width=True):
                if sel_prospect_for_outreach != "— select —":
                    st.session_state["ops_prefill"] = f"Draft a cold outreach email for {sel_prospect_for_outreach}. Use all available data about them."
                    st.rerun()

        st.markdown("")
        for i, action in enumerate(quick_actions):
            if st.button(action, key=f"ops_quick_{i}", use_container_width=True):
                st.session_state["ops_prefill"] = action
                st.rerun()

        if "chat_history_ops" in st.session_state and st.session_state.chat_history_ops:
            st.markdown("")
            if st.button("Clear conversation", key="ops_clear", use_container_width=True):
                st.session_state.chat_history_ops = []
                st.rerun()

    with col_chat:
        # Init chat history
        if "chat_history_ops" not in st.session_state:
            st.session_state.chat_history_ops = []

        # Handle pre-fills from quick actions
        if "ops_prefill" in st.session_state:
            prefill_val = st.session_state.pop("ops_prefill")
            st.session_state.chat_history_ops.append({"role": "user", "content": prefill_val})

        # Show welcome if empty
        if not st.session_state.chat_history_ops:
            st.markdown(
                f"""
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem;">
                  <div style="font-size:0.9rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.3rem;">Operations Manager ready.</div>
                  <div style="font-size:0.82rem;color:#64748b;">Ask me anything about the pipeline, request email drafts, get strategic recommendations, or use Quick Actions to the left.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Render chat history
        for msg in st.session_state.chat_history_ops:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                st.markdown(
                    f'<div class="chat-msg-user">{content}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-msg-assistant">{content}</div>',
                    unsafe_allow_html=True,
                )
                # Show task creation buttons for any <TASK> tags
                extracted_tasks = _extract_tasks(content)
                for ti, task_data in enumerate(extracted_tasks):
                    task_key = f"create_task_{hash(content[:50])}_{ti}"
                    if st.button(
                        f"Create task: {task_data.get('title', 'Untitled')}",
                        key=task_key,
                        type="primary",
                    ):
                        result = create_task({
                            "title": task_data.get("title", ""),
                            "description": task_data.get("description", ""),
                            "assigned_to": task_data.get("assigned_to", [name]),
                            "priority": task_data.get("priority", "medium"),
                            "due_date": task_data.get("due_date", ""),
                            "status": "open",
                            "created_by_email": email,
                            "created_by_name": name,
                        })
                        if result:
                            st.success(f"Task created: {task_data.get('title','')}")
                        else:
                            st.warning("Could not create task — check Supabase connection.")

        # Generate response if last message is from user
        if st.session_state.chat_history_ops and st.session_state.chat_history_ops[-1]["role"] == "user":
            if not has_ai_configured():
                st.error("No AI key configured. Add ANTHROPIC_API_KEY to Streamlit secrets.")
            else:
                placeholder = st.empty()
                try:
                    db_summary = _df_summary(df)
                    context = (
                        f"Current prospect database:\n{db_summary}\n\n"
                        f"Open tasks: {open_tasks_count}\n"
                        f"Today's date: {datetime.now().strftime('%B %d, %Y')}\n"
                        f"Logged-in user: {name} ({email})"
                    )
                    messages = []
                    for i, msg in enumerate(st.session_state.chat_history_ops):
                        content = msg["content"]
                        if i == 0 and msg["role"] == "user":
                            content = f"{context}\n\nUser: {content}"
                        messages.append({"role": msg["role"], "content": content})

                    placeholder.markdown(
                        '<div class="chat-msg-assistant" style="color:#94a3b8;">Thinking...</div>',
                        unsafe_allow_html=True,
                    )
                    reply, prov = call_ai(OPS_SYSTEM_PROMPT, messages, max_tokens=2048)
                    # Simulate streaming
                    _stream_text(reply, placeholder)
                    st.session_state.chat_history_ops.append({"role": "assistant", "content": reply})
                    if prov != "Claude":
                        st.caption(f"Answered by {prov}")
                    st.rerun()
                except Exception as e:
                    placeholder.empty()
                    st.error(f"AI request failed: {e}")

        # Chat input
        st.markdown("")
        user_input = st.chat_input("Ask the Operations Manager anything...", key="ops_chat_input")
        if user_input:
            st.session_state.chat_history_ops.append({"role": "user", "content": user_input})
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2: Email Factory
# ═════════════════════════════════════════════════════════════════════════════

with tab_email:
    st.markdown(
        f'<div style="font-size:1rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.3rem;">Email Factory</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.82rem;color:#64748b;margin-bottom:1rem;">Generate tailored outreach emails using all prospect data. Keeps a history of last 5 generated emails.</div>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("No prospects loaded.")
    else:
        prospect_names = sorted(df["name"].dropna().unique().tolist())

        ef_col1, ef_col2 = st.columns([3, 2])

        with ef_col1:
            ef_prospect = st.selectbox(
                "Select prospect",
                prospect_names,
                key="ef_prospect",
            )
            ef_email_type = st.radio(
                "Email type",
                ["Cold outreach", "Follow-up #1", "Follow-up #2", "Demo confirmation", "Post-demo"],
                horizontal=True,
                key="ef_email_type",
            )
            ef_context = st.text_area(
                "Additional context to include (optional)",
                placeholder="e.g. She mentioned they're opening a new satellite clinic in Scarborough next quarter...",
                height=80,
                key="ef_extra_context",
            )

            if st.button("Generate Email", type="primary", key="do_generate_email"):
                if not has_ai_configured():
                    st.error("No AI key configured.")
                else:
                    with st.spinner(f"Generating {ef_email_type} for {ef_prospect}..."):
                        ctx = _prospect_context(df, ef_prospect)
                        type_guidance = {
                            "Cold outreach": "Write a cold outreach email. Be concise (under 150 words), warm but professional. Hook on their specific pain point. Clear CTA: 15-min discovery call.",
                            "Follow-up #1": "Write a follow-up email for a prospect who didn't respond to the first email. Reference the original email was sent. Add one new piece of value. Keep it short (under 100 words).",
                            "Follow-up #2": "Write a second follow-up (third email total). Acknowledge they may be busy. Offer an easy low-commitment CTA (a quick question they can answer in one line). Under 80 words.",
                            "Demo confirmation": "Write a demo confirmation email. Include what to expect from the demo, a quick agenda (15-20 min), and any prep they might want to do. Friendly and brief.",
                            "Post-demo": "Write a post-demo follow-up email. Thank them for their time, recap the key pain point they mentioned, next steps, and a clear ask for a decision timeline.",
                        }
                        guidance = type_guidance.get(ef_email_type, "Write a professional outreach email.")
                        extra = f"\n\nAdditional context: {ef_context.strip()}" if ef_context.strip() else ""

                        prompt = f"""{guidance}

PROSPECT DATA:
{ctx}{extra}

Format:
Subject: [subject line]

[email body]

Sign off as: {name}, MedPort

Important: reference specific details from their data (institution type, outreach angle, decision maker name if available). Do NOT use generic templates."""

                        try:
                            email_text, prov = call_ai(RESEARCH_SYSTEM_PROMPT, [{"role": "user", "content": prompt}], max_tokens=800)
                            # Store in email history
                            if "email_history" not in st.session_state:
                                st.session_state.email_history = []
                            st.session_state.email_history.insert(0, {
                                "prospect": ef_prospect,
                                "type": ef_email_type,
                                "email": email_text,
                                "provider": prov,
                                "timestamp": datetime.now().strftime("%b %d %H:%M"),
                            })
                            st.session_state.email_history = st.session_state.email_history[:5]
                            st.session_state["latest_email"] = email_text
                        except Exception as e:
                            st.error(f"Email generation failed: {e}")

        with ef_col2:
            st.markdown(
                f'<div style="font-size:0.82rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.5rem;">Recent Emails (last 5)</div>',
                unsafe_allow_html=True,
            )
            if "email_history" in st.session_state and st.session_state.email_history:
                for i, hist in enumerate(st.session_state.email_history):
                    with st.expander(f"{hist['prospect']} — {hist['type']} ({hist['timestamp']})", expanded=(i == 0)):
                        st.code(hist["email"], language=None)
                        if hist.get("provider") and hist["provider"] != "Claude":
                            st.caption(f"Generated by {hist['provider']}")
            else:
                st.caption("No emails generated yet.")

        # Show latest generated email prominently
        if "latest_email" in st.session_state:
            st.markdown("---")
            st.markdown(
                f'<div style="font-size:0.88rem;font-weight:700;color:{MEDPORT_DARK};margin-bottom:0.5rem;">Generated Email</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid {MEDPORT_TEAL};border-radius:8px;padding:1rem 1.1rem;font-size:0.87rem;white-space:pre-wrap;font-family:monospace;color:{MEDPORT_DARK};">{st.session_state["latest_email"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown("")
            copy_col, dl_col = st.columns(2)
            with copy_col:
                st.code(st.session_state["latest_email"], language=None)
            with dl_col:
                st.download_button(
                    "Download (.txt)",
                    data=st.session_state["latest_email"],
                    file_name=f"email_{ef_prospect.lower().replace(' ','_')[:30]}_{ef_email_type.replace(' ','_')}.txt",
                    mime="text/plain",
                    key="dl_email",
                )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3: Quick Research
# ═════════════════════════════════════════════════════════════════════════════

with tab_quick:
    st.markdown("### Quick Research Brief")
    st.markdown(
        f'<div style="color:#64748b;font-size:0.82rem;margin-bottom:1rem;">'
        f'Enter a clinic or institution name to generate a research brief with outreach angle, decision makers, and risk assessment.'
        f'</div>',
        unsafe_allow_html=True,
    )

    qr_name = st.text_input("Clinic or institution name", placeholder="e.g. Flemingdon Health Centre", key="qr_name")
    qr_city = st.text_input("City (optional)", placeholder="e.g. Toronto, ON", key="qr_city")

    if st.button("Generate Research Brief", type="primary", key="do_quick_research"):
        if qr_name.strip():
            location_str = f" in {qr_city.strip()}" if qr_city.strip() else ""
            prompt = f"""Generate a concise outreach intelligence brief for {qr_name.strip()}{location_str}.

Structure your response as:
1. **Overview** — What is this institution? Type, size, population served (2-3 sentences).
2. **Phone Intake Assessment** — Based on institution type, estimate call volume and likely pain points with manual phone intake.
3. **Decision Maker Titles** — Who likely owns the technology/operations decision at this org? List 3 likely titles.
4. **Innovation Score Rationale** — On a scale of 1-10, how likely is this institution to adopt new AI technology? Explain briefly.
5. **Outreach Angle** — One sharp, specific cold outreach angle (2-3 sentences max). Reference specific context about this institution type.
6. **Key Risks** — Top 2 reasons this deal might not close (e.g. budget constraints, incumbent EMR, regulatory concerns).
7. **Recommended Next Step** — One specific action for the outreach team.

Be direct and specific. Avoid generic filler."""

            with st.spinner(f"Researching {qr_name.strip()}..."):
                try:
                    brief, prov = call_ai(RESEARCH_SYSTEM_PROMPT, [{"role": "user", "content": prompt}], max_tokens=1200)
                    st.markdown("---")
                    st.markdown(f"#### Research Brief: {qr_name.strip()}")
                    if prov != "Claude":
                        st.caption(f"Generated by {prov}")
                    st.markdown(brief)
                    st.markdown("---")
                    st.download_button(
                        "Download Brief (.txt)",
                        data=brief,
                        file_name=f"brief_{qr_name.strip().lower().replace(' ', '_')}.txt",
                        mime="text/plain",
                        key="download_brief",
                    )
                except Exception as e:
                    st.error(f"Research failed: {e}")
        else:
            st.warning("Please enter an institution name.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4: Prospect Deep Dive
# ═════════════════════════════════════════════════════════════════════════════

with tab_deepdive:
    st.markdown("### Prospect Deep Dive")
    st.markdown(
        f'<div style="color:#64748b;font-size:0.82rem;margin-bottom:1rem;">'
        f'Select a prospect from your database to generate a comprehensive 500-word research and outreach brief.'
        f'</div>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("No prospects in the database yet.")
    else:
        prospect_names = sorted(df["name"].dropna().unique().tolist())
        selected_prospect = st.selectbox(
            "Select prospect",
            prospect_names,
            key="dd_prospect",
        )

        if selected_prospect:
            ctx = _prospect_context(df, selected_prospect)
            with st.expander("Current database data for this prospect", expanded=False):
                st.text(ctx)

        if st.button("Generate Deep Dive Brief", type="primary", key="do_deep_dive"):
            if selected_prospect:
                ctx = _prospect_context(df, selected_prospect)
                prompt = f"""Generate a comprehensive deep-dive research brief for this prospect.

PROSPECT DATA FROM OUR DATABASE:
{ctx}

Write a ~500 word brief covering:
1. **Institution Profile** — What we know about this institution, size, community served, any unique characteristics.
2. **Why MedPort Fits** — Specific connection between their phone intake challenges and MedPort's AI voice agent. Reference their patient volume, EMR system, and any phone intake evidence we have.
3. **Decision Maker Intelligence** — Who to target, how to find them, what they care about. Reference the contact info we have.
4. **Outreach Strategy** — Our specific outreach angle, recommended channel (email vs LinkedIn vs phone), timing recommendations.
5. **Competitive Risks** — Any competitor tools they may already use, budget constraints, or barriers.
6. **Ask** — What's the exact call-to-action for our first outreach? A demo? A discovery call? A specific question?

Be specific, actionable, and written for a sales team member who will use this immediately."""

                with st.spinner(f"Generating deep dive for {selected_prospect}..."):
                    try:
                        brief, prov = call_ai(RESEARCH_SYSTEM_PROMPT, [{"role": "user", "content": prompt}], max_tokens=2000)
                        st.markdown("---")
                        st.markdown(f"#### Deep Dive: {selected_prospect}")
                        if prov != "Claude":
                            st.caption(f"Generated by {prov}")
                        st.markdown(brief)
                        st.markdown("---")
                        st.download_button(
                            "Download Deep Dive (.txt)",
                            data=brief,
                            file_name=f"deepdive_{selected_prospect.lower().replace(' ', '_')[:40]}.txt",
                            mime="text/plain",
                            key="download_deepdive",
                        )
                    except Exception as e:
                        st.error(f"Deep dive failed: {e}")
