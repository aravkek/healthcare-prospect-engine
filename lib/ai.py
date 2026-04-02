"""
MedPort shared AI helper — Claude first, Groq fallback.
Import call_ai() from both pages/5 and pages/7.
"""

import os
import streamlit as st

MODEL = "claude-sonnet-4-6"


def _secret(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def call_ai(system: str, messages: list[dict], max_tokens: int = 2048) -> tuple[str, str]:
    """
    Claude first, Groq llama-3.3-70b fallback.
    Returns (response_text, provider_name).
    Raises RuntimeError on total failure.
    """
    anthropic_key = _secret("ANTHROPIC_API_KEY")
    groq_key = _secret("GROQ_API_KEY")
    fallback_reason = ""

    # Try Anthropic / Claude
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
            fallback_reason = str(e)
    else:
        fallback_reason = "ANTHROPIC_API_KEY not set"

    # Groq fallback
    if groq_key:
        try:
            import requests as _req
            groq_messages = [{"role": "system", "content": system}] + messages
            resp = _req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                },
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
                f"Both AI providers failed. Claude: {fallback_reason}. Groq: {ge}"
            )

    raise RuntimeError(
        "No AI API key configured. Add ANTHROPIC_API_KEY (or GROQ_API_KEY as fallback) to Streamlit secrets."
    )


def has_ai_configured() -> bool:
    """Returns True if at least one AI provider key is available."""
    return bool(_secret("ANTHROPIC_API_KEY") or _secret("GROQ_API_KEY"))


def ai_provider_badge() -> str:
    """Returns the name of the active AI provider for display."""
    if _secret("ANTHROPIC_API_KEY"):
        return "Claude Sonnet"
    if _secret("GROQ_API_KEY"):
        return "Groq (fallback)"
    return "No AI key"


# ─── MedPort product context (used in all prompts) ────────────────────────────

_MEDPORT_CONTEXT = """
MedPort is a Canadian healthcare intelligence startup building AI-powered patient intake tools.
Core product: Patients scan a QR code or get a text link before their appointment. They fill out all intake forms on their phone. When they arrive, the clinic has pre-filled, structured data ready — no paper, no front-desk manual entry, no duplicate forms.
Key value props:
- Reduces front-desk administrative burden by 40-60%
- Eliminates paper forms entirely
- Integrates with most major Canadian EMRs (OSCAR, Jane App, Accuro, Telus Health, PS Suite, etc.)
- PIPEDA-compliant, data stays in Canada
- Works for any clinic type: GP, walk-in, specialist, dental, physiotherapy, university health centres
- Setup takes under a day, no IT infrastructure required
- Pricing: ~$200-300/month per clinic location
Target buyers: Clinic owners, medical directors, practice managers, operations leads
Primary pain point we solve: "Patients show up and we spend 10+ minutes redoing paperwork they already filled out elsewhere"
""".strip()


def research_institution(prospect: dict) -> str:
    """
    Generate a detailed institutional research brief for a prospect.
    Returns the research text.
    """
    name = prospect.get("name", "Unknown")
    inst_type = prospect.get("inst_type", "healthcare institution")
    city = prospect.get("city", "")
    country = prospect.get("country", "CA")
    emr = prospect.get("emr_system", "unknown")
    patient_vol = prospect.get("patient_volume", "unknown")
    ai_tools = prospect.get("existing_ai_tools", "")
    phone_evidence = prospect.get("phone_intake_evidence", "")
    website = prospect.get("website", "")
    existing_notes = prospect.get("research_notes", "")

    system = f"""You are a B2B sales intelligence analyst for a healthcare startup.
{_MEDPORT_CONTEXT}
Your job: produce concise, actionable intelligence briefings that help a sales rep walk into a conversation fully prepared."""

    user_msg = f"""Research this prospect and write a structured intelligence brief.

Institution: {name}
Type: {inst_type}
Location: {city}, {country}
EMR System: {emr}
Patient Volume: {patient_vol}
Existing AI tools: {ai_tools or "None detected"}
Phone intake evidence: {phone_evidence or "None"}
Website: {website or "Not available"}
Existing research notes: {existing_notes or "None"}

Write a structured brief with these exact sections:

**INSTITUTION OVERVIEW**
2-3 sentences: what this institution is, who they serve, their scale and specialty. Be specific.

**ADMINISTRATIVE PAIN POINTS**
What specific intake/administrative problems does a {inst_type} like this likely face? Reference their size, volume, and EMR. Be concrete — not generic.

**TECHNOLOGY POSTURE**
Based on their EMR ({emr}), any AI tools, and what we know — how tech-forward are they? What does their current intake process probably look like?

**WHY MEDPORT FITS**
2-3 specific reasons MedPort solves a real problem for THIS institution. Connect MedPort's value props to their specific situation.

**RISK FACTORS**
1-2 honest reasons this prospect might be hard to convert (competitor, budget, process, inertia).

**RECOMMENDED APPROACH**
One paragraph: the specific angle, tone, and hook that will resonate most with this institution's decision maker.

Be specific and direct. No generic filler. If you don't have data, say what you'd expect based on institution type."""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=1500)
    return text


def research_decision_maker(prospect: dict) -> str:
    """
    Generate a decision maker research brief.
    Returns the research text.
    """
    dm_name = prospect.get("decision_maker_name", "")
    dm_title = prospect.get("decision_maker_title", "")
    dm_linkedin = prospect.get("decision_maker_linkedin", "")
    inst_name = prospect.get("name", "")
    inst_type = prospect.get("inst_type", "clinic")
    city = prospect.get("city", "")

    if not dm_name:
        # Try to infer who the decision maker probably is
        user_msg = f"""For a {inst_type} called "{inst_name}" in {city}, Canada:

Who is most likely the decision maker for adopting a new patient intake software tool?
What would their title typically be?
What do they care about professionally?
What objections would they typically have to a new vendor?
What is the best way to get their attention in a cold email?

Write a short profile (4-6 bullet points) of the typical decision maker at this type of institution."""
    else:
        user_msg = f"""Research this decision maker and write an intelligence profile.

Name: {dm_name}
Title: {dm_title or "Unknown"}
Institution: {inst_name} ({inst_type}) in {city}, Canada
LinkedIn: {dm_linkedin or "Not available"}

Write a structured profile:

**WHO THEY ARE**
What we know or can reasonably infer about their background, tenure, and responsibilities.

**WHAT THEY CARE ABOUT**
Based on their title and institution type — what are their top professional priorities? What keeps them up at night?

**HOW TO REACH THEM**
- Best email tone (formal vs. peer-to-peer)
- What subject line would make them open
- What first sentence would make them keep reading
- What they'll object to immediately

**PERSONALIZATION HOOKS**
2-3 specific things to reference in the outreach that will show you did your homework (based on institution type, their role, and Canadian healthcare context)."""

    system = f"""You are a B2B sales intelligence analyst for a healthcare startup.
{_MEDPORT_CONTEXT}
Help the sales team personalize their outreach to individual decision makers."""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=1200)
    return text


def analyze_fit(prospect: dict, research_brief: str = "", dm_research: str = "") -> str:
    """
    Generate a structured fit and success probability assessment.
    Returns structured analysis text.
    """
    name = prospect.get("name", "")
    inst_type = prospect.get("inst_type", "")
    city = prospect.get("city", "")
    emr = prospect.get("emr_system", "")
    inno = prospect.get("innovation_score", 0)
    access = prospect.get("accessibility_score", 0)
    fit = prospect.get("fit_score", 0)
    startup_rx = prospect.get("startup_receptiveness", 0)
    composite = int(inno or 0) + int(access or 0) + int(fit or 0) + int(startup_rx or 0)
    rank = prospect.get("priority_rank", 3)
    risk = prospect.get("competitor_risk", "none")

    system = f"""You are a sales strategist at a healthcare startup.
{_MEDPORT_CONTEXT}
Your job: give honest, calibrated assessments of whether a prospect is worth pursuing and how to win them."""

    user_msg = f"""Assess this prospect's fit and our probability of converting them.

Institution: {name} ({inst_type}, {city})
EMR: {emr}
Our scores: Innovation={inno}/10, Accessibility={access}/10, Product Fit={fit}/10, Startup Receptiveness={startup_rx}/10 → Composite: {composite}/40
Priority Tier: {rank} (1=A, 2=B, 3=C)
Competitor Risk: {risk}

Institution Research:
{research_brief or "Not yet researched"}

Decision Maker Research:
{dm_research or "Not yet researched"}

Provide a structured assessment:

**FIT SCORE: X/10**
One sentence explaining this score based on SPECIFIC evidence, not generic statements.

**SUCCESS PROBABILITY: X%**
Realistic estimate of getting a demo booked. Factor in: institution type, receptiveness score, competitor risk, and what we know about the DM.

**TOP 3 REASONS TO PURSUE**
Specific, evidence-based reasons this is worth our time.

**TOP 2 OBJECTIONS WE'LL FACE**
The most likely specific pushbacks from this prospect.

**WINNING STRATEGY**
The specific approach most likely to convert: timeline, tone, number of touches, key message.

**VERDICT**
One of: PURSUE AGGRESSIVELY / PURSUE NORMALLY / LOW PRIORITY / SKIP
With a one-sentence justification."""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=1200)
    return text


def draft_outreach_email(
    prospect: dict,
    research_brief: str = "",
    dm_research: str = "",
    fit_analysis: str = "",
    sender_name: str = "Ahan",
    sender_title: str = "CMO & Co-Founder",
    variant: int = 1,
) -> tuple[str, str]:
    """
    Draft a cold outreach email. Returns (subject, body).
    variant=1: direct value prop, variant=2: problem-first, variant=3: social proof hook
    """
    dm_name = prospect.get("decision_maker_name", "")
    dm_title = prospect.get("decision_maker_title", "")
    inst_name = prospect.get("name", "")
    inst_type = prospect.get("inst_type", "clinic")
    city = prospect.get("city", "")
    emr = prospect.get("emr_system", "")
    outreach_angle = prospect.get("outreach_angle", "")

    greeting = f"Hi {dm_name.split()[0]}," if dm_name else "Hi,"

    variant_instructions = {
        1: "Lead with the specific value prop (time saved, admin burden reduced). Make it concrete — mention their EMR if known.",
        2: "Lead with the problem: describe a specific pain point this type of clinic faces with patient intake. Make them feel understood before mentioning MedPort.",
        3: "Lead with a specific detail you know about their institution that shows you did your research. Then connect it to why MedPort matters for them specifically.",
    }.get(variant, "")

    system = """You write cold outreach emails for B2B healthcare SaaS sales.
Rules:
- Max 5 sentences in the body (not counting subject and CTA)
- Never use: "I hope this finds you well", "touching base", "synergy", "solution", "reaching out"
- Be specific — reference their actual EMR, their city, their institution type
- Sound like a smart peer, not a vendor
- CTA: always a 15-minute call, no pressure framing
- Subject line: under 55 characters, specific, no clickbait"""

    user_msg = f"""Write a cold outreach email for this prospect.

INSTITUTION: {inst_name} ({inst_type}), {city}, Canada
DECISION MAKER: {dm_name or "Unknown"} ({dm_title or "Decision maker"})
EMR SYSTEM: {emr or "Unknown"}
SENDER: {sender_name}, {sender_title} at MedPort

RESEARCH BRIEF:
{research_brief or "No research available — use general knowledge about this type of institution"}

DM RESEARCH:
{dm_research or "No DM research — write to a generic decision maker for this institution type"}

FIT ANALYSIS:
{fit_analysis or "Not analyzed yet"}

EXISTING OUTREACH ANGLE NOTE:
{outreach_angle or "None"}

VARIANT INSTRUCTION: {variant_instructions}

{_MEDPORT_CONTEXT}

Output format — exactly this, nothing else:
SUBJECT: [subject line here]
---
{greeting}

[email body — 4-5 sentences max]

[CTA sentence]

{sender_name}
MedPort | medport.ca"""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=600)

    # Parse subject and body
    lines = text.strip().split("\n")
    subject = ""
    body_lines = []
    past_divider = False
    for line in lines:
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.strip() == "---":
            past_divider = True
        elif past_divider:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    if not subject:
        subject = f"Quick question about {inst_name}'s intake process"
    if not body:
        body = text  # fallback: return raw text

    return subject, body


def draft_followup_email(
    prospect: dict,
    original_subject: str,
    days_since: int,
    outcome: str = "no_response",
    sender_name: str = "Ahan",
) -> tuple[str, str]:
    """Draft a follow-up email. Returns (subject, body)."""
    dm_name = prospect.get("decision_maker_name", "")
    inst_name = prospect.get("name", "")
    greeting = f"Hi {dm_name.split()[0]}," if dm_name else "Hi,"

    outcome_context = {
        "no_response": f"They haven't responded after {days_since} days.",
        "opened": "They opened the email but didn't respond.",
        "interested": "They expressed mild interest but didn't commit to a call.",
        "asked_for_info": "They asked for more information.",
        "bounced": "The email bounced — need to find a new contact.",
    }.get(outcome, f"Status: {outcome}")

    system = """You write follow-up emails for B2B healthcare SaaS sales. Be brief, add value, don't beg."""

    user_msg = f"""Write a follow-up email.

Original subject: {original_subject}
Institution: {inst_name}
Decision maker: {dm_name or "Unknown"}
Situation: {outcome_context}
Sender: {sender_name} at MedPort

Rules:
- Max 3 sentences
- Add a new hook or piece of value (not just "following up")
- Don't apologize for following up
- Keep subject line short — use RE: {original_subject} only if it makes sense

Output format:
SUBJECT: [subject]
---
{greeting}

[body — 2-3 sentences]

{sender_name}"""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=400)

    lines = text.strip().split("\n")
    subject = f"RE: {original_subject}"
    body_lines = []
    past_divider = False
    for line in lines:
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.strip() == "---":
            past_divider = True
        elif past_divider:
            body_lines.append(line)

    body = "\n".join(body_lines).strip() or text
    return subject, body
