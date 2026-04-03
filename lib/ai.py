"""
MedPort shared AI helper — Claude first, Groq fallback.
All research and email functions produce hyper-personalized output anchored
to every known signal about the prospect.
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
    return bool(_secret("ANTHROPIC_API_KEY") or _secret("GROQ_API_KEY"))


def ai_provider_badge() -> str:
    if _secret("ANTHROPIC_API_KEY"):
        return "Claude Sonnet"
    if _secret("GROQ_API_KEY"):
        return "Groq (fallback)"
    return "No AI key"


# ─── MedPort product context ──────────────────────────────────────────────────
# Injected into every prompt so all AI output is anchored to what MedPort
# actually does, its integrations, and its positioning.

_MEDPORT_CONTEXT = """
ABOUT MEDPORT:
MedPort is a Canadian healthcare technology startup (Toronto-based, founded 2025) building
AI-powered patient intake and pre-registration tools for clinics across Canada.

CORE PRODUCT:
Patients get a text/email link before their appointment. They complete all intake forms on
their phone in under 3 minutes. When they arrive, the clinic already has structured, verified
patient data — no paper, no front-desk re-entry, no duplicate questions. The data flows
directly into the clinic's EMR.

EMR INTEGRATIONS (confirmed or in active development):
- OSCAR Pro / OSCAR EMR (most common in Ontario/BC family medicine)
- Jane App (physio, chiro, massage, mental health, multi-disciplinary)
- Accuro (specialty clinics, surgical, hospital-adjacent)
- Telus Health (PS Suite, Wolf, Med Access)
- Dentrix, Dolphin (dental)
- University health centre platforms (varies by institution)

QUANTIFIED VALUE PROPS (use these numbers in emails and research):
- Reduces front-desk administrative time by 40-60%
- Average check-in time drops from 12-15 minutes to under 2 minutes
- Eliminates paper forms and manual data transcription entirely
- Reduces no-shows by 18% due to pre-visit engagement touchpoint
- Setup and go-live in under one business day — no IT project required
- PIPEDA-compliant, all data stored on Canadian servers (no cross-border PHI transfer)

PRICING:
~$200-300/month per clinic location. No long-term contract required for pilot.
Free 30-day pilot available for qualified clinics.

IDEAL CUSTOMER PROFILE:
- Canadian clinic: GP, walk-in, specialist, dental, physio, university health centre, hospital outpatient
- 3+ practitioners or 50+ patient visits/day
- Currently using paper forms OR manually re-entering patient data from one system to another
- On a supported EMR (above list)
- Has a decision maker who values efficiency and is open to software tools

THE FOUNDERS:
- Arav Kekane — CEO (aravkekane@gmail.com)
- Ahan — CMO (leads outreach)
- Advait — CFO
- Aarya — CTO
- Nathen — COO
Young founding team, University of Toronto / Canadian ecosystem.
Positioning: peer founders who understand the Canadian healthcare system, not a US vendor parachuting in.
""".strip()


def _build_prospect_context(prospect: dict) -> str:
    """
    Build a dense, structured context block from every available signal
    about a prospect. Used as the factual spine of every prompt.
    """
    def _v(key, fallback="Unknown"):
        v = prospect.get(key)
        return str(v).strip() if v not in (None, "", "Unknown", "unknown") else fallback

    name = _v("name", "Unknown institution")
    inst_type = _v("inst_type", "healthcare institution")
    city = _v("city", "Unknown city")
    country = _v("country", "CA")
    website = _v("website", "Not available")
    phone = _v("phone", "Not listed")
    emr = _v("emr_system", "Unknown EMR")
    patient_vol = _v("patient_volume", "Unknown")
    ai_tools = _v("existing_ai_tools", "None detected")
    phone_evidence = _v("phone_intake_evidence", "None")
    outreach_angle = _v("outreach_angle", "None recorded")
    contact_notes = _v("contact_notes", "None")
    research_notes = _v("research_notes", "None")
    competitor_risk = _v("competitor_risk", "Unknown")

    dm_name = _v("decision_maker_name", "Not identified")
    dm_title = _v("decision_maker_title", "Not identified")
    dm_email = _v("decision_maker_email", "Not available")
    dm_phone = _v("decision_maker_phone", "Not available")
    dm_linkedin = _v("decision_maker_linkedin", "Not available")

    inno = prospect.get("innovation_score", 0) or 0
    access = prospect.get("accessibility_score", 0) or 0
    fit = prospect.get("fit_score", 0) or 0
    startup_rx = prospect.get("startup_receptiveness", 0) or 0
    composite = int(inno) + int(access) + int(fit) + int(startup_rx)
    rank = prospect.get("priority_rank", 3) or 3
    tier = {1: "A (highest priority)", 2: "B (medium priority)", 3: "C (lower priority)"}.get(int(rank), "C")

    score_bd = _v("score_breakdown", "")

    lines = [
        f"INSTITUTION: {name}",
        f"TYPE: {inst_type}",
        f"LOCATION: {city}, {country}",
        f"WEBSITE: {website}",
        f"PHONE: {phone}",
        f"EMR SYSTEM: {emr}",
        f"PATIENT VOLUME: {patient_vol}",
        f"EXISTING AI/TECH TOOLS: {ai_tools}",
        f"PHONE INTAKE EVIDENCE DETECTED: {phone_evidence}",
        f"",
        f"DECISION MAKER: {dm_name}",
        f"DM TITLE: {dm_title}",
        f"DM EMAIL: {dm_email}",
        f"DM PHONE: {dm_phone}",
        f"DM LINKEDIN: {dm_linkedin}",
        f"",
        f"SCORES (our internal assessment, 1-10 each):",
        f"  Innovation Score: {inno}/10",
        f"  Accessibility Score: {access}/10",
        f"  Product Fit Score: {fit}/10",
        f"  Startup Receptiveness: {startup_rx}/10",
        f"  Composite: {composite}/40",
        f"  Score Breakdown Details: {score_bd}",
        f"PRIORITY TIER: {tier}",
        f"COMPETITOR RISK: {competitor_risk}",
        f"",
        f"PRE-IDENTIFIED OUTREACH ANGLE: {outreach_angle}",
        f"CONTACT NOTES: {contact_notes}",
        f"OTHER RESEARCH NOTES: {research_notes}",
    ]
    return "\n".join(lines)


def research_institution(prospect: dict) -> str:
    """
    Generate a hyper-specific institutional intelligence brief.
    Every section must reference actual data points from this prospect.
    """
    prospect_ctx = _build_prospect_context(prospect)
    name = prospect.get("name", "this institution")
    inst_type = prospect.get("inst_type", "healthcare institution")
    emr = prospect.get("emr_system", "")
    city = prospect.get("city", "")

    system = f"""You are a senior B2B sales intelligence analyst at a Canadian healthcare startup.
{_MEDPORT_CONTEXT}

CRITICAL RULE: Every sentence you write must be specific to THIS institution.
Never write generic statements that could apply to any clinic.
If you catch yourself writing something that could appear in any brief, rewrite it with a specific fact, inference, or angle tied to this exact prospect.
You are preparing intelligence that will help our team walk in fully prepared — not a Wikipedia summary."""

    user_msg = f"""Write a deep intelligence brief for this prospect. Use every data point below.

{prospect_ctx}

Write each section below. Be brutally specific — reference their actual EMR by name,
their city and province, their patient volume numbers, any tech signals detected.
Draw inferences from what you know about {inst_type} institutions in {city}, Canada.

**INSTITUTION OVERVIEW**
3 sentences max. What is this institution specifically? Who do they serve? What makes them distinct from a generic {inst_type}?
If their website is available, infer what you can about their size, focus areas, and patient demographics.

**THEIR CURRENT INTAKE REALITY**
Based on their EMR ({emr or "unknown system"}), patient volume, and any phone intake signals —
paint a picture of what check-in day probably looks like right now at {name}.
What are patients doing? What is the front desk doing? Where is the friction?
Be specific about how {emr or "their EMR"} clinics typically handle this.

**WHY THIS INSTITUTION SPECIFICALLY NEEDS MEDPORT**
3 specific reasons — not generic reasons why any clinic needs us.
Connect MedPort's capabilities directly to their EMR, their volume, their type, and their location.
If they have phone intake evidence, reference it. If they use specific AI tools or lack them, factor that in.

**DECISION MAKER LANDSCAPE**
Who at {name} signs off on a tool like MedPort? What does their title tell us about their priorities?
What is a {(prospect.get("decision_maker_title") or inst_type + " administrator")} evaluated on?
What would make them say yes? What would make them say no in 5 seconds?

**COMPETITIVE & RISK FACTORS**
What could block this deal? Reference their competitor risk rating, any inertia signals, budget constraints typical of a {inst_type}, or incumbent tools.

**RECOMMENDED OUTREACH STRATEGY**
The single sharpest angle for the first email to {name}.
Specific subject line style. Specific hook. Specific value prop to lead with.
Reference what we already know about their outreach angle if one is recorded.

**5 SPECIFIC FACTS TO WEAVE INTO OUTREACH**
A numbered list of the 5 most powerful personalization details to reference in emails, calls, and demos.
These should be things that show we did our homework — not generic claims."""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=3000)
    return text


def research_decision_maker(prospect: dict, institution_research: str = "") -> dict:
    """
    Identify the decision maker at this institution and return a structured dict:
    {name, title, email, phone, linkedin, brief}

    The brief is short (4-6 sentences) — just what the team needs to write a good email.
    """
    import json as _json

    prospect_ctx = _build_prospect_context(prospect)
    dm_name = (prospect.get("decision_maker_name") or "").strip()
    dm_title = (prospect.get("decision_maker_title") or "").strip()
    dm_linkedin = (prospect.get("decision_maker_linkedin") or "").strip()
    inst_name = prospect.get("name", "")
    inst_type = prospect.get("inst_type", "clinic")
    city = prospect.get("city", "")
    province = prospect.get("province", "")

    system = f"""You are a sales intelligence researcher helping a healthcare startup identify and profile
the right person to contact at a target institution. Be specific and practical — no filler.
{_MEDPORT_CONTEXT}"""

    if not dm_name or dm_name.lower() in ("unknown", "not identified", "n/a"):
        user_msg = f"""Find the most likely decision maker at this institution for adopting a new patient intake tool.

INSTITUTION: {inst_name} ({inst_type}, {city}, {province})
{prospect_ctx}
INSTITUTION RESEARCH: {institution_research or "Not yet available"}

Your job:
1. Name the SPECIFIC person at {inst_name} who would sign off on adopting MedPort (or the closest real person you know of from your training data).
2. If you know their actual name and email from your training data, include it. If not, name the role/title and leave name/email blank.
3. Write a SHORT brief (4-6 sentences max) covering: who they are, what they care about, and the one angle that will land in a cold email.

Respond ONLY with this JSON (no other text, no markdown code fences):
{{
  "name": "Full Name if known, else empty string",
  "title": "Job Title",
  "email": "work email if known from training data, else empty string",
  "phone": "phone if known, else empty string",
  "linkedin": "LinkedIn URL if known, else empty string",
  "brief": "4-6 sentence profile: who they are, what they care about most, tone to use, one specific hook for {inst_name}"
}}"""

    else:
        first = dm_name.split()[0]
        user_msg = f"""Profile this specific decision maker for a cold outreach by MedPort.

PERSON: {dm_name}, {dm_title} at {inst_name} ({inst_type}, {city}, {province})
LinkedIn: {dm_linkedin or "unknown"}
{prospect_ctx}
INSTITUTION RESEARCH: {institution_research or "Not yet available"}

Tasks:
1. Fill in any missing contact info (email, phone, LinkedIn) if you know it from your training data.
2. Write a SHORT brief (4-6 sentences): who {first} is, what they prioritize, what email tone works for them, one specific hook to open with.

Respond ONLY with this JSON (no other text, no markdown code fences):
{{
  "name": "{dm_name}",
  "title": "{dm_title}",
  "email": "work email if known, else empty string",
  "phone": "phone if known, else empty string",
  "linkedin": "{dm_linkedin}",
  "brief": "4-6 sentence profile: background, what {first} cares about, ideal tone, one specific personalized hook"
}}"""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=600)

    # Parse JSON response; fall back to wrapping raw text as brief
    try:
        # Strip any accidental code fences
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = _json.loads(clean.strip())
        # Ensure all expected keys exist
        for key in ("name", "title", "email", "phone", "linkedin", "brief"):
            result.setdefault(key, "")
        return result
    except Exception:
        return {
            "name": dm_name,
            "title": dm_title,
            "email": "",
            "phone": "",
            "linkedin": dm_linkedin,
            "brief": text.strip(),
        }


def analyze_fit(prospect: dict, research_brief: str = "", dm_research: str = "") -> str:
    """
    Generate a structured fit and success probability assessment.
    """
    prospect_ctx = _build_prospect_context(prospect)
    name = prospect.get("name", "this institution")

    system = f"""You are a sales strategist at a Canadian healthcare startup.
{_MEDPORT_CONTEXT}

Give calibrated, honest assessments. Don't oversell the opportunity.
If this is a hard pass, say so. If this is a must-win, say so.
Every claim must be anchored to the specific data we have about this prospect."""

    user_msg = f"""Assess whether we should pursue {name} and how to win them.

{prospect_ctx}

INSTITUTION RESEARCH:
{research_brief or "Not yet researched — base your assessment on the prospect data above"}

DECISION MAKER RESEARCH:
{dm_research or "Not yet researched — infer from title and institution type"}

Provide the following:

**FIT SCORE: X/10**
Based on their scores, EMR, type, and research — how well does MedPort map to their situation?
Justify with one specific sentence referencing actual data points.

**SUCCESS PROBABILITY: X%**
Realistic probability of getting to a booked demo (not a closed deal).
Factor in: startup receptiveness score, competitor risk, decision maker accessibility, institution type, and any friction signals.

**WHY WE SHOULD PURSUE THIS — TOP 3 REASONS**
Specific, evidence-based. Reference their actual data.

**THE 2 OBJECTIONS WE WILL DEFINITELY FACE**
Not generic objections. The specific pushbacks a {prospect.get("decision_maker_title", "decision maker")} at a {prospect.get("inst_type", "clinic")} using {prospect.get("emr_system", "their EMR")} would raise.
And the one-sentence counter to each.

**OUR BEST SHOT AT WINNING THIS ACCOUNT**
The specific sequence: who to contact first, what to say, what proof point to lead with, what demo flow to use.
Be specific to this institution — not a generic playbook.

**VERDICT**
One of: PURSUE AGGRESSIVELY / PURSUE NORMALLY / LOW PRIORITY / SKIP
With a one-sentence justification tied to specific data."""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=2000)
    return text


def draft_outreach_email(
    prospect: dict,
    research_brief: str = "",
    dm_research: str = "",
    fit_analysis: str = "",
    sender_name: str = "Ahan",
    sender_title: str = "CMO & Co-Founder, MedPort",
    variant: int = 1,
) -> tuple[str, str]:
    """
    Draft a hyper-personalized cold outreach email.
    variant=1: direct value prop anchored to their EMR + volume
    variant=2: problem-first — describe their exact intake pain before mentioning us
    variant=3: research hook — open with something specific we know about them
    """
    prospect_ctx = _build_prospect_context(prospect)

    dm_name = prospect.get("decision_maker_name", "")
    dm_title = prospect.get("decision_maker_title", "")
    inst_name = prospect.get("name", "")
    inst_type = prospect.get("inst_type", "clinic")
    city = prospect.get("city", "")
    emr = prospect.get("emr_system", "")
    patient_vol = prospect.get("patient_volume", "")
    phone_evidence = prospect.get("phone_intake_evidence", "")
    ai_tools = prospect.get("existing_ai_tools", "")
    outreach_angle = prospect.get("outreach_angle", "")

    first_name = dm_name.split()[0] if dm_name and dm_name not in ("Unknown", "Not identified") else None
    greeting = f"Hi {first_name}," if first_name else "Hi there,"

    # Pull the sharpest facts from research to force specificity
    facts_block = ""
    if research_brief:
        facts_block += f"\nINSTITUTION RESEARCH (mine this for specific facts to reference):\n{research_brief}\n"
    if dm_research:
        facts_block += f"\nDECISION MAKER RESEARCH (use the personalization hooks):\n{dm_research}\n"
    if fit_analysis:
        facts_block += f"\nFIT ANALYSIS (use the winning strategy section):\n{fit_analysis}\n"

    variant_instructions = {
        1: f"""VARIANT 1 — PEER INSIGHT + VALUE:
Open with a genuine insight about the world {dm_title or "this person"} operates in — something that shows
you understand their context deeply. Then connect it to a specific, quantified outcome MedPort delivers.
Reference their EMR ({emr or "their system"}) by name and what integration actually means for their workflow.

NEVER start with: "I noticed", "I came across", "I hope this finds you", "I wanted to reach out"
INSTEAD open with: An observation about their world, a trend in their institution type, or a peer insight.

Example of BAD: "We help clinics reduce administrative burden with our AI solution."
Example of GOOD: "Family medicine clinics running OSCAR across Ontario are averaging 12 minutes of front-desk
intake work per patient — before the appointment even starts. For a 30-patient day, that's 6 hours of staff
time spent on paper."
Then explain: MedPort sends patients a link before their appointment — they arrive pre-registered, data flows
straight into {emr or "their EMR"}, front desk goes from gatekeeping forms to actually helping patients.
Make the numbers real for their scale ({patient_vol or "their volume"}).""",

        2: f"""VARIANT 2 — THEIR WORLD FIRST:
Open by painting a picture of a regular day at {inst_name} — from the perspective of someone who deeply
understands how {inst_type} institutions operate. Make {dm_title or "the reader"} feel seen before
you ever mention MedPort.
The first sentence should describe their reality, not our product.
The second sentence should name the friction. The third should offer the solution.

NEVER: comment on their website, point out what they're "still" doing, or imply they're behind.
INSTEAD: describe their world with empathy and precision, then offer a better version of it.

Example of BAD: "I noticed your website still uses paper intake forms."
Example of GOOD: "Running a {inst_type} means your team is managing patient arrivals,
re-entering data they've already collected, and handling the front desk rush — all before anyone
has actually seen a provider."
Reference phone intake evidence if available: {phone_evidence or "n/a"}
Use their specific institution dynamics from the research brief.""",

        3: f"""VARIANT 3 — PERSONALITY-MATCHED:
This email is written specifically for {dm_name or "this person"}'s personality, communication style,
and professional ideology as profiled in the DM research.
Use the language they respond to. Match their formality level. Lead with what they care about most.

If the DM research shows they're data-driven: lead with a number.
If they're relationship-first: lead with a shared challenge other institutions like theirs have solved.
If they're academically oriented: lead with a trend or study relevant to their institution type.
If they're operations-focused: lead with process efficiency and time savings.

Pull directly from the DM research personalization hooks.
The email should feel like it was written by someone who read their LinkedIn, their institution's annual
report, and talked to three of their peers — and is now writing as a collegial peer, not a vendor.

Outreach angle from our notes: {outreach_angle or "not recorded — infer from DM personality research"}""",
    }.get(variant, "")

    system = f"""You write cold outreach emails for a Canadian healthcare startup's sales team.
{_MEDPORT_CONTEXT}

STRICT EMAIL RULES — violating any of these makes the email unusable:
1. Body: exactly 4-5 sentences. No more.
2. BANNED phrases — never appear in the output:
   "I hope this finds you well" / "touching base" / "just checking in" / "reaching out" /
   "synergy" / "innovative solution" / "game-changer" / "streamline" /
   "I noticed your" / "I came across your" / "I wanted to reach out" / "I saw that you" /
   "still using" / "still doing" / "you're still" — these are condescending or cliché.
3. NEVER point out something the institution is doing wrong or "still" doing.
   INSTEAD: describe their world accurately and warmly, then offer a better version of it.
4. Every sentence must be grounded in a specific fact about this institution, their EMR, their
   city, their institution type, or the DM's role and personality. No generic filler.
5. CTA: one specific, low-friction ask — e.g., "Would you be open to a 15-minute call to see
   how it integrates with {emr or 'your setup'}?" Not "Let me know if you're interested."
6. Subject: under 55 chars, earns attention through specificity — no tricks, no questions.
7. Tone: collegial founder-to-peer. You deeply respect their work and understand their world.
   You're sharing something genuinely useful — not pitching, not selling.
8. Signature: {sender_name} / {sender_title} / MedPort"""

    user_msg = f"""Write a cold outreach email to this specific prospect.

{prospect_ctx}
{facts_block}

SENDER: {sender_name}, {sender_title}
GREETING TO USE: {greeting}

{variant_instructions}

OUTPUT FORMAT — exactly this, nothing else:
SUBJECT: [subject line — under 55 chars, no generic phrases]
---
{greeting}

[4-5 sentence body — every sentence must reference something specific to {inst_name} or {dm_title or "their role"}]

[CTA — one sentence, specific]

{sender_name}
{sender_title}
MedPort | medport.ca"""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=1200)

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
        subject = f"{inst_name} — patient intake"
    if not body:
        body = text

    return subject, body


def draft_followup_email(
    prospect: dict,
    original_subject: str,
    days_since: int,
    outcome: str = "no_response",
    sender_name: str = "Ahan",
    research_brief: str = "",
    dm_research: str = "",
) -> tuple[str, str]:
    """
    Draft a hyper-personalized follow-up email.
    Adds new value — never just "following up on my last email."
    """
    dm_name = prospect.get("decision_maker_name", "")
    inst_name = prospect.get("name", "")
    inst_type = prospect.get("inst_type", "clinic")
    emr = prospect.get("emr_system", "")
    city = prospect.get("city", "")
    dm_title = prospect.get("decision_maker_title", "")

    first_name = dm_name.split()[0] if dm_name and dm_name not in ("Unknown", "Not identified") else None
    greeting = f"Hi {first_name}," if first_name else "Hi,"

    outcome_context = {
        "no_response": f"Sent {days_since} days ago. No response. They may not have seen it, or it wasn't compelling enough.",
        "opened": f"They opened the email {days_since} days ago but didn't respond. They're aware of us — not yet convinced.",
        "interested": "They expressed some interest but haven't committed to a call. Need to reduce friction.",
        "asked_for_info": "They asked for more information. Need to send something specific that answers their question and moves toward a demo.",
        "bounced": "The email bounced. Need to try a different contact method or find another contact at this institution.",
    }.get(outcome, f"Outcome: {outcome}. {days_since} days since last contact.")

    # Pull a fresh hook from research if available
    research_hook = ""
    if research_brief:
        research_hook = f"\nINSTITUTION RESEARCH (find a new hook or angle to add value in this follow-up):\n{research_brief[:800]}\n"
    if dm_research:
        research_hook += f"\nDM RESEARCH (find a personalization detail specific to this person):\n{dm_research[:600]}\n"

    system = f"""You write follow-up emails for a Canadian healthcare startup.
{_MEDPORT_CONTEXT}

FOLLOW-UP RULES:
1. Max 3 sentences total. Shorter is better.
2. Every follow-up must add NEW VALUE — a new fact, a new angle, a new proof point. Never just say "following up."
3. Reference something specific about {inst_name} or {dm_title or "their role"} — not just a generic re-introduction.
4. No apologies for following up. No "I know you're busy."
5. End with a frictionless CTA — offer something specific (a 10-min call, a one-page overview, a quick demo video)."""

    user_msg = f"""Write a follow-up email for this prospect.

INSTITUTION: {inst_name} ({inst_type}), {city}
DECISION MAKER: {dm_name or "Unknown"} ({dm_title or "decision maker"})
EMR: {emr or "Unknown"}
ORIGINAL SUBJECT: {original_subject}
SITUATION: {outcome_context}
SENDER: {sender_name} at MedPort
GREETING: {greeting}
{research_hook}

Add a new angle or new value in this follow-up. Ideas:
- A specific stat about {inst_type} clinics using MedPort or similar tools
- A specific integration detail about {emr or "their EMR"} that's relevant to their workflow
- A short proof point: "A {inst_type} in [similar city] went live in one day — no IT involved"
- A new question that shows you understand their specific challenge

OUTPUT FORMAT:
SUBJECT: [Re: {original_subject} OR a new specific subject if re-engage is needed]
---
{greeting}

[2-3 sentence body — adds new value, references {inst_name} specifically]

[1 sentence CTA — very low friction]

{sender_name}"""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=450)

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
