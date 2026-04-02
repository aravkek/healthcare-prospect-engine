"""
MedPort AI Research — Claude-powered research assistant and team chatbot.
Model: claude-sonnet-4-6
API key from st.secrets["ANTHROPIC_API_KEY"] or ANTHROPIC_API_KEY env var.
"""

import os
import sys
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import inject_css, MEDPORT_BLUE, MEDPORT_GREEN, MEDPORT_LIGHT_BLUE, MEDPORT_LIGHT_GREEN
from lib.auth import check_auth, is_admin
from lib.db import load_prospects

st.set_page_config(
    page_title="AI Research — MedPort",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)

# ─── Constants ───────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are MedPort's internal AI assistant. MedPort builds AI voice agents that handle incoming patient calls for clinics — handling appointment booking, intake, and triage. The team is a 5-person founding team targeting YC W27.

You help with:
- Outreach research and prospect analysis
- Email drafting for cold outreach
- Strategy and pipeline questions
- Answering questions about the prospect database
- Suggesting new prospect targets similar to existing ones

When drafting emails, be concise, warm, and focus on the specific pain points of clinic phone intake (missed calls, after-hours calls, front desk overload, appointment no-shows). Emphasize that MedPort handles the whole call — not just transcription or scheduling.

Always be direct and useful. If asked about the prospect database, analyze the data provided and give specific, actionable answers."""


def _secret(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def _call_ai(system: str, messages: list[dict], max_tokens: int = 2048) -> tuple[str, str]:
    """
    Call Claude first, fall back to Groq llama-3.3-70b if Anthropic key missing or fails.
    Returns (response_text, provider_used).
    Raises on total failure.
    """
    anthropic_key = _secret("ANTHROPIC_API_KEY")
    groq_key = _secret("GROQ_API_KEY")

    # Try Anthropic first
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            resp = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            return resp.content[0].text, "Claude"
        except Exception as e:
            # Fall through to Groq
            _groq_fallback_reason = str(e)
    else:
        _groq_fallback_reason = "ANTHROPIC_API_KEY not set"

    # Groq fallback
    if groq_key:
        try:
            import requests as _req
            groq_messages = [{"role": "system", "content": system}] + messages
            resp = _req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": groq_messages,
                    "max_tokens": min(max_tokens, 8192),
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"], "Groq (fallback)"
        except Exception as ge:
            raise RuntimeError(
                f"Both AI providers failed. Claude: {_groq_fallback_reason}. Groq: {ge}"
            )

    raise RuntimeError(
        "No AI API key configured. Add ANTHROPIC_API_KEY (or GROQ_API_KEY as fallback) to Streamlit secrets."
    )


def _df_summary(df) -> str:
    """Compact text summary of prospect data for context injection."""
    if df.empty:
        return "No prospect data available."
    lines = [f"Total prospects: {len(df)}"]
    if "status" in df.columns:
        lines.append("Status breakdown:")
        for status, count in df["status"].value_counts().items():
            lines.append(f"  - {status.replace('_', ' ').title()}: {count}")
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
    """Return all known data about a specific prospect as formatted text."""
    if df.empty:
        return "No data available."
    match = df[df["name"].str.lower() == prospect_name.lower()]
    if match.empty:
        # Fuzzy match
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


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_BLUE};">AI Research</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='font-size:0.8rem;color:#6b7a8d;'>{name}</div>", unsafe_allow_html=True)
    st.markdown("---")

    try:
        auth_configured = bool(st.secrets.get("auth", {}))
    except Exception:
        auth_configured = False
    if auth_configured and os.environ.get("LOCAL_DEV", "false").lower() != "true":
        if st.button("Sign out"):
            st.logout()

    st.markdown("---")
    _has_anthropic = bool(_secret("ANTHROPIC_API_KEY"))
    _has_groq = bool(_secret("GROQ_API_KEY"))
    if _has_anthropic:
        st.markdown(
            f'<span style="background:{MEDPORT_GREEN};color:#fff;border-radius:20px;padding:2px 10px;font-size:0.75rem;font-weight:700;">Claude Sonnet ✓</span>',
            unsafe_allow_html=True,
        )
    elif _has_groq:
        st.markdown(
            '<span style="background:#f39c12;color:#fff;border-radius:20px;padding:2px 10px;font-size:0.75rem;font-weight:700;">Groq Fallback Active</span>',
            unsafe_allow_html=True,
        )
        st.caption("Add ANTHROPIC_API_KEY for Claude Sonnet.")
    else:
        st.markdown(
            '<span style="background:#f8d7da;color:#721c24;border-radius:20px;padding:2px 10px;font-size:0.75rem;font-weight:700;">No AI Key</span>',
            unsafe_allow_html=True,
        )
        st.caption("Add ANTHROPIC_API_KEY (or GROQ_API_KEY as fallback) to Streamlit secrets.")

# ─── Load data ───────────────────────────────────────────────────────────────

df = load_prospects()

# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown("# AI Research Assistant")
st.markdown(
    f'<div style="color:#6b7a8d;font-size:0.88rem;margin-top:-0.6rem;margin-bottom:1.2rem;">'
    f'Powered by Claude {MODEL} &nbsp;·&nbsp; Research, emails, strategy, and prospect deep dives'
    f'</div>',
    unsafe_allow_html=True,
)

# ─── Tabs ────────────────────────────────────────────────────────────────────

tab_chat, tab_quick, tab_deepdive = st.tabs(["Team Chatbot", "Quick Research", "Prospect Deep Dive"])

# ─── Tab 1: Team Chatbot ─────────────────────────────────────────────────────

with tab_chat:
    st.markdown("### Team Chatbot")
    st.markdown(
        f'<div style="color:#6b7a8d;font-size:0.82rem;margin-bottom:1rem;">'
        f'Ask anything: prospect questions, email drafts, strategy, pipeline analysis.'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Suggestion buttons
    suggestions = [
        "Which Tier A prospects haven't been contacted yet?",
        "Write a cold email for a community health centre in Toronto",
        "What's our current pipeline conversion rate?",
        "Suggest 5 clinic types similar to CHCs that we haven't targeted",
        "What are the most common EMR systems in our database?",
        "Draft a follow-up email for a prospect that hasn't responded in 2 weeks",
    ]

    if not st.session_state.chat_history:
        st.markdown("**Suggested questions:**")
        sug_cols = st.columns(3)
        for i, sug in enumerate(suggestions):
            with sug_cols[i % 3]:
                if st.button(sug, key=f"sug_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": sug})
                    st.rerun()

    # Render chat history
    for msg in st.session_state.chat_history:
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

    # Check if we need to generate a response
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        with st.spinner("Thinking..."):
            try:
                db_summary = _df_summary(df)
                context = (
                    f"Current prospect database context:\n{db_summary}\n\n"
                    f"Today's date: {datetime.now().strftime('%B %d, %Y')}\n"
                    f"Logged-in user: {name} ({email})"
                )
                messages = []
                for i, msg in enumerate(st.session_state.chat_history):
                    content = msg["content"]
                    if i == 0 and msg["role"] == "user":
                        content = f"{context}\n\nUser question: {content}"
                    messages.append({"role": msg["role"], "content": content})

                reply, provider = _call_ai(SYSTEM_PROMPT, messages, max_tokens=2048)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                if provider != "Claude":
                    st.caption(f"Answered by {provider}")
                st.rerun()
            except Exception as e:
                st.error(f"AI request failed: {e}")

    # Input
    st.markdown("")
    user_input = st.chat_input("Ask MedPort AI anything...", key="chat_input")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()

# ─── Tab 2: Quick Research ────────────────────────────────────────────────────

with tab_quick:
    st.markdown("### Quick Research Brief")
    st.markdown(
        f'<div style="color:#6b7a8d;font-size:0.82rem;margin-bottom:1rem;">'
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
                    brief, provider = _call_ai(SYSTEM_PROMPT, [{"role": "user", "content": prompt}], max_tokens=1200)
                    st.markdown("---")
                    st.markdown(f"#### Research Brief: {qr_name.strip()}")
                    if provider != "Claude":
                        st.caption(f"Generated by {provider}")
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

# ─── Tab 3: Prospect Deep Dive ────────────────────────────────────────────────

with tab_deepdive:
    st.markdown("### Prospect Deep Dive")
    st.markdown(
        f'<div style="color:#6b7a8d;font-size:0.82rem;margin-bottom:1rem;">'
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
            # Show current data summary
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
                        brief, provider = _call_ai(SYSTEM_PROMPT, [{"role": "user", "content": prompt}], max_tokens=2000)
                        st.markdown("---")
                        st.markdown(f"#### Deep Dive: {selected_prospect}")
                        if provider != "Claude":
                            st.caption(f"Generated by {provider}")
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
