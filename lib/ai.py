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

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=2000)
    return text


def research_decision_maker(prospect: dict, institution_research: str = "") -> str:
    """
    Generate a hyper-specific decision maker profile.
    If institution_research is provided, the DM profile is contextualized to it.
    """
    prospect_ctx = _build_prospect_context(prospect)
    dm_name = prospect.get("decision_maker_name", "")
    dm_title = prospect.get("decision_maker_title", "")
    inst_name = prospect.get("name", "")
    inst_type = prospect.get("inst_type", "clinic")
    city = prospect.get("city", "")
    emr = prospect.get("emr_system", "")

    system = f"""You are a B2B sales intelligence analyst specializing in Canadian healthcare.
{_MEDPORT_CONTEXT}

Your job: build a decision maker profile that helps our team write a cold email so personalized
it feels impossible to ignore. Every insight must be actionable — not theoretical."""

    if not dm_name or dm_name.lower() in ("unknown", "not identified"):
        user_msg = f"""We don't have a named decision maker yet for this institution.

{prospect_ctx}

INSTITUTION RESEARCH BRIEF:
{institution_research or "Not yet available"}

Build a profile of the TYPICAL decision maker for a {inst_type} like {inst_name} in {city}, Canada:

**MOST LIKELY DECISION MAKER**
What is their most common title at a {inst_type}? (e.g., Practice Manager, Medical Director, Executive Director, Clinic Owner, etc.)
Why is this person the one who buys — not the doctors?

**WHAT DRIVES THEM PROFESSIONALLY**
What are they measured on? What keeps them up at night?
What does "a good year" look like for someone in this role at a {inst_type} using {emr or "their EMR"}?

**HOW THEY EVALUATE NEW VENDORS**
How does a {inst_type} administrator typically discover and evaluate new tools?
What proof points matter most to them? (Peer references, ROI numbers, ease of setup, compliance, etc.)

**COLD EMAIL PSYCHOLOGY**
- What subject line makes them click?
- What first sentence makes them keep reading?
- What first paragraph makes them reply?
- What would make them delete this in 3 seconds?

**3 PERSONALIZATION HOOKS FOR {inst_name.upper()}**
Based on everything we know about this specific institution — 3 things we can reference in
our outreach to show we know their world, not just clinics in general."""

    else:
        user_msg = f"""Build a detailed intelligence profile for this specific decision maker.

{prospect_ctx}

INSTITUTION RESEARCH BRIEF:
{institution_research or "Not yet available — use the prospect data above to infer context"}

**WHO {dm_name.upper()} IS**
Based on their title ({dm_title}) at {inst_name} ({inst_type}, {city}):
- What is their likely background and career path?
- How long do people in this role typically stay?
- What does their day-to-day actually look like?
- What decisions are they empowered to make vs. what requires a physician or board sign-off?

**WHAT {dm_name.split()[0].upper()} CARES ABOUT**
As a {dm_title} at a {inst_type}:
- Top 3 professional priorities (be specific to role and institution type)
- What success looks like for them in the next 12 months
- What they're probably frustrated about right now

**HOW TO REACH {dm_name.split()[0].upper()}**
- Email tone: formal/peer-to-peer/clinical? Why?
- Subject line that works for this specific person's role and institution
- First sentence that makes a {dm_title} keep reading
- The objection they will raise in the first 10 seconds — and how to pre-empt it

**PERSONALIZATION HOOKS — USE THESE IN EMAILS**
5 specific details to reference about {inst_name} / {dm_name} that show deep research.
Make these concrete and usable as natural email sentences.

**SUGGESTED EMAIL OPENER**
Write the ideal opening 2 sentences of a cold email to {dm_name.split()[0]} specifically.
It should feel like it was written by someone who spent 30 minutes on their website and LinkedIn."""

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=1500)
    return text


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

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=1400)
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
        1: f"""VARIANT 1 — DIRECT VALUE PROP:
Lead with a specific, quantified benefit tied directly to their situation.
Reference their EMR ({emr or "their current system"}) and our integration with it by name.
If we know their patient volume ({patient_vol or "unknown"}), reference what 40% time savings means concretely.
Example of BAD opening: "We help clinics reduce administrative burden."
Example of GOOD opening: "OSCAR-based family clinics in Ontario are cutting check-in time from 14 minutes to under 2 — without changing anything in their workflow."
Make the math real for a clinic their size.""",

        2: f"""VARIANT 2 — PROBLEM-FIRST:
Open by describing the exact scene at {inst_name} on a busy Monday morning — before mentioning us.
What is the front desk doing? What are patients doing? What's the friction?
Make the {dm_title or "practice manager"} feel understood before you offer anything.
Then position MedPort as the obvious answer to the problem you just described.
Example of BAD opening: "I know you're busy, so I'll be brief."
Example of GOOD opening: "Every Monday at a walk-in like yours, the first 40 patients fill out the same form they filled out at their GP last week — and your front desk re-enters it anyway."
Reference the phone intake evidence if available: {phone_evidence or "not available"}.""",

        3: f"""VARIANT 3 — RESEARCH HOOK:
Open with one specific thing we know about {inst_name} that shows we did our homework.
This should be something about their institution, their EMR, their city/region, or their type of practice.
NOT a compliment — a relevant observation that creates context for why you're emailing.
Then connect that observation directly to the problem MedPort solves.
Example of BAD opening: "I came across your clinic online and was impressed."
Example of GOOD opening: "Jane App clinics in {city or "your city"} are increasingly competing on patient experience — and most are still handing out paper clipboards at the front desk."
Use the personalization hooks from the DM research. Reference the outreach angle if available: {outreach_angle or "not recorded"}.""",
    }.get(variant, "")

    system = f"""You write cold outreach emails for a Canadian healthcare startup's sales team.
{_MEDPORT_CONTEXT}

STRICT EMAIL RULES — violating any of these makes the email unusable:
1. Body: exactly 4-5 sentences. No more.
2. NEVER use: "I hope this finds you well", "touching base", "just checking in", "reaching out", "synergy", "innovative solution", "game-changer", "streamline"
3. Every sentence must contain a specific fact about {inst_name}, {emr or "their EMR"}, {city or "their city"}, or the decision maker's role. No generic filler sentences.
4. CTA: one specific 15-minute ask. "Would you have 15 minutes next week to see how it'd work with your {emr or "setup"}?" is good. "Let me know if you're interested" is bad.
5. Subject line: under 55 characters, specific to this institution, no clickbait, no questions
6. Tone: peer-to-peer, confident, not salesy. You are a fellow Canadian founder who understands their world.
7. Signature: {sender_name} / {sender_title} / MedPort"""

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

    text, _ = call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=700)

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
