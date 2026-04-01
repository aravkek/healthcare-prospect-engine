#!/usr/bin/env python3
"""
MedPort Customer Discovery Engine
====================================
Stage 1: Pull healthcare institutions from public directories
          (Ontario CHCs, Ontario university health centres, US FQHCs, specialty clinics)
Stage 2: Deep-research each institution using Groq LLM (llama-3.3-70b-versatile)
          to score innovation openness, decision-maker accessibility, competitor risk, fit
          Falls back to keyword scoring when no Groq key is available.
Stage 3: Output a prioritized CSV with outreach angles for each

Usage:
    pip install requests beautifulsoup4 pandas
    python customer_discovery.py

    Optional flags:
    --stage1-only     Just pull the list, skip research (fast)
    --limit N         Only research the first N institutions (default: all)
    --country ca|us   Only pull from Canada or US (default: both)
    --resume          Skip institutions already in output CSV
    --groq-key TEXT   Groq API key (overrides GROQ_API_KEY env var)

    Uses Groq free tier (llama-3.3-70b) for AI research.
    Get a free key at https://console.groq.com and set GROQ_API_KEY env var.
"""

import os
import sys
import time
import csv
import json
import argparse
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from typing import Optional

# ─────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────

@dataclass
class Institution:
    name: str
    inst_type: str          # CHC | university | FQHC | walk-in | dental | specialty
    city: str
    province_state: str
    country: str            # CA | US
    website: str = ""
    phone: str = ""
    email: str = ""
    decision_maker_name: str = ""
    decision_maker_title: str = ""
    decision_maker_linkedin: str = ""
    # Scoring (filled by Stage 2)
    innovation_score: int = 0       # 1-10: does their public presence signal openness to tech?
    accessibility_score: int = 0    # 1-10: can a student founder get in front of the right person?
    fit_score: int = 0              # 1-10: do their stated problems match what MedPort solves?
    competitor_risk: str = ""       # none | low | medium | high
    priority_rank: int = 0          # lower = higher priority
    research_notes: str = ""        # what was found during research
    outreach_angle: str = ""        # the specific hook to use in cold outreach to this institution
    source: str = ""                # where this institution came from


# ─────────────────────────────────────────────
# Stage 1 — Pull institutions from directories
# ─────────────────────────────────────────────

ONTARIO_UNIVERSITY_HEALTH_CENTRES = [
    Institution("University of Toronto Health & Wellness", "university", "Toronto", "ON", "CA",
                "https://studentlife.utoronto.ca/service/health-wellness/", decision_maker_title="Director, Health & Wellness"),
    Institution("McMaster University Student Wellness Centre", "university", "Hamilton", "ON", "CA",
                "https://wellness.mcmaster.ca/", decision_maker_name="Cynthia Gibney (intro exists)", decision_maker_title="Director"),
    Institution("University of Waterloo Campus Wellness", "university", "Waterloo", "ON", "CA",
                "https://uwaterloo.ca/campus-wellness/", decision_maker_title="Executive Director, Campus Wellness"),
    Institution("Western University Student Health Services", "university", "London", "ON", "CA",
                "https://www.uwo.ca/health/", decision_maker_title="Director, Student Health Services"),
    Institution("Queen's University Student Wellness Services", "university", "Kingston", "ON", "CA",
                "https://www.queensu.ca/studentwellness/", decision_maker_title="Director, Student Wellness"),
    Institution("University of Ottawa Health Services", "university", "Ottawa", "ON", "CA",
                "https://www.uottawa.ca/campus-life/health-wellness/", decision_maker_title="Director, Health Services"),
    Institution("York University Health Education & Promotion", "university", "Toronto", "ON", "CA",
                "https://www.yorku.ca/well-u/health/", decision_maker_title="Manager, Health Education"),
    Institution("Toronto Metropolitan University (TMU) Medical Centre", "university", "Toronto", "ON", "CA",
                "https://www.torontomu.ca/student-wellbeing/health/", decision_maker_title="Manager, Medical Centre"),
    Institution("University of Guelph Student Health Services", "university", "Guelph", "ON", "CA",
                "https://wellness.uoguelph.ca/health/", decision_maker_title="Director, Student Health"),
    Institution("Brock University Student Health Services", "university", "St. Catharines", "ON", "CA",
                "https://brocku.ca/student-health-services/", decision_maker_title="Director, Health Services"),
    Institution("Trent University Health Services", "university", "Peterborough", "ON", "CA",
                "https://www.trentu.ca/healthservices/", decision_maker_title="Manager, Health Services"),
    Institution("University of Windsor Student Health Services", "university", "Windsor", "ON", "CA",
                "https://www.uwindsor.ca/studenthealthservices/", decision_maker_title="Coordinator, Health Services"),
    Institution("Laurentian University Health Services", "university", "Sudbury", "ON", "CA",
                "https://laurentian.ca/health-services", decision_maker_title="Health Services Coordinator"),
    Institution("OCAD University Health & Wellness", "university", "Toronto", "ON", "CA",
                "https://www.ocadu.ca/student-life/health-wellness", decision_maker_title="Health & Wellness Coordinator"),
]

# Key Ontario community health centres — manually curated top targets
# Full directory: https://www.chcontario.ca/our-members/
ONTARIO_CHC_SEED = [
    Institution("Flemingdon Health Centre", "CHC", "Toronto", "ON", "CA",
                "https://www.flemingdonhealth.ca/", phone="416-429-4991",
                decision_maker_title="Executive Director / Director of Programs",
                research_notes="Demo scheduled April 8, 2026. Large CHC serving immigrant + racialized communities. Known for innovation partnerships."),
    Institution("Regent Park Community Health Centre", "CHC", "Toronto", "ON", "CA",
                "https://www.regentparkchc.org/", decision_maker_title="Executive Director"),
    Institution("Unison Health and Community Services", "CHC", "Toronto", "ON", "CA",
                "https://unisonhcs.org/", decision_maker_title="Executive Director"),
    Institution("Black Creek Community Health Centre", "CHC", "Toronto", "ON", "CA",
                "https://www.bcchc.com/", decision_maker_title="Executive Director"),
    Institution("Inner City Health Associates", "CHC", "Toronto", "ON", "CA",
                "https://www.icha-toronto.ca/", decision_maker_title="Medical Director"),
    Institution("St. Michael's Hospital Academic Family Health Team", "CHC", "Toronto", "ON", "CA",
                "https://www.stmichaelshospital.com/", decision_maker_title="Program Director"),
    Institution("Sherbourne Health", "CHC", "Toronto", "ON", "CA",
                "https://sherbourne.on.ca/", decision_maker_title="Executive Director"),
    Institution("Access Alliance Multicultural Health and Community Services", "CHC", "Toronto", "ON", "CA",
                "https://accessalliance.ca/", decision_maker_title="Executive Director"),
    Institution("Oriole Community Health Team", "CHC", "North York", "ON", "CA",
                "https://www.oriolefht.ca/", decision_maker_title="Executive Director"),
    Institution("North York General Family Health Team", "CHC", "North York", "ON", "CA",
                "https://www.nygh.on.ca/", decision_maker_title="Director, Primary Care"),
    Institution("Hamilton Urban Core Community Health Centre", "CHC", "Hamilton", "ON", "CA",
                "https://www.urbancore.ca/", decision_maker_title="Executive Director"),
    Institution("Waterloo Region Community Health Centre", "CHC", "Kitchener", "ON", "CA",
                "https://www.communitycare.on.ca/", decision_maker_title="Executive Director"),
    Institution("Ottawa Community Health Centre", "CHC", "Ottawa", "ON", "CA",
                "https://www.cscso.ca/", decision_maker_title="Executive Director"),
    Institution("Centretown Community Health Centre", "CHC", "Ottawa", "ON", "CA",
                "https://www.centretownchc.org/", decision_maker_title="Executive Director"),
    Institution("Somerset West Community Health Centre", "CHC", "Ottawa", "ON", "CA",
                "https://www.swchc.on.ca/", decision_maker_title="Executive Director"),
    Institution("Bruyère Continuing Care", "CHC", "Ottawa", "ON", "CA",
                "https://www.bruyere.org/", decision_maker_title="Director, Innovation"),
    Institution("Niagara Region Community Health Centre", "CHC", "Niagara Falls", "ON", "CA",
                "https://www.nrchc.ca/", decision_maker_title="Executive Director"),
    Institution("Planned Parenthood Toronto", "specialty", "Toronto", "ON", "CA",
                "https://www.ppt.on.ca/", decision_maker_title="Executive Director"),
]

# Ontario walk-in / independent clinic chains — targets for voice agent
ONTARIO_WALKIN_SEED = [
    Institution("Appletree Medical Group", "walk-in", "Ottawa/Toronto", "ON", "CA",
                "https://appletreemedical.ca/", decision_maker_title="VP Operations / CIO",
                research_notes="Large multi-site group, 30+ locations. If cracked = major reference customer."),
    Institution("Medicentres Canada", "walk-in", "Multiple", "ON", "CA",
                "https://www.medicentres.com/", decision_maker_title="VP Operations"),
    Institution("Appletree Medical — Toronto Flagship", "walk-in", "Toronto", "ON", "CA",
                "https://appletreemedical.ca/", decision_maker_title="Clinic Manager"),
    Institution("Shoppers Drug Mart Medical Clinics", "walk-in", "Multiple", "ON", "CA",
                "https://www.shoppersdrugmart.ca/", decision_maker_title="Director, Clinic Operations"),
    Institution("Cleveland Clinic Canada", "specialty", "Toronto", "ON", "CA",
                "https://my.clevelandclinic.org/canada", decision_maker_title="Director, Operations"),
    Institution("Medcan", "specialty", "Toronto", "ON", "CA",
                "https://www.medcan.com/", decision_maker_title="CTO / Director Digital Health"),
    Institution("Maple (virtual + in-person)", "walk-in", "Toronto", "ON", "CA",
                "https://www.getmaple.ca/", decision_maker_title="Head of Partnerships",
                research_notes="Tech-forward. May already have similar tools. Check competitor risk."),
    Institution("Well Health Technologies — Ontario clinics", "walk-in", "Multiple", "ON", "CA",
                "https://well.ca/pages/health", decision_maker_title="VP Digital Health",
                research_notes="Public co. on TSX. Has innovation budget. Harder to reach but enterprise value."),
]

# Top US university health centres — innovation-forward targets
US_UNIVERSITY_HEALTH_CENTRES = [
    Institution("NYU Student Health Center", "university", "New York", "NY", "US",
                "https://www.nyu.edu/students/health-and-wellness/student-health-center.html",
                decision_maker_title="Executive Director, Student Health"),
    Institution("Columbia Health", "university", "New York", "NY", "US",
                "https://health.columbia.edu/", decision_maker_title="Executive Director, Columbia Health"),
    Institution("Cornell Health", "university", "Ithaca", "NY", "US",
                "https://health.cornell.edu/", decision_maker_title="Executive Director"),
    Institution("Johns Hopkins Student Health", "university", "Baltimore", "MD", "US",
                "https://studentaffairs.jhu.edu/student-health/", decision_maker_title="Director, Student Health"),
    Institution("University of Michigan University Health Service", "university", "Ann Arbor", "MI", "US",
                "https://uhs.umich.edu/", decision_maker_title="Director, University Health Service"),
    Institution("UCLA Arthur Ashe Student Health and Wellness Center", "university", "Los Angeles", "CA", "US",
                "https://www.studenthealth.ucla.edu/", decision_maker_title="Director, Student Health"),
    Institution("University of Chicago Student Wellness", "university", "Chicago", "IL", "US",
                "https://wellness.uchicago.edu/", decision_maker_title="Executive Director"),
    Institution("Northwestern Student Health Service", "university", "Evanston", "IL", "US",
                "https://www.northwestern.edu/health-service/", decision_maker_title="Director"),
    Institution("Penn Student Health Service", "university", "Philadelphia", "PA", "US",
                "https://www.vpul.upenn.edu/shs/", decision_maker_title="Executive Director"),
    Institution("Harvard University Health Services", "university", "Cambridge", "MA", "US",
                "https://huhs.harvard.edu/", decision_maker_title="Chief Medical Officer",
                research_notes="Prestigious but hard to access. Good for brand. Try through alumni network."),
    Institution("MIT Medical", "university", "Cambridge", "MA", "US",
                "https://medical.mit.edu/", decision_maker_title="Chief Medical Officer",
                research_notes="Very tech-forward by nature. High innovation score expected."),
    Institution("Stanford Vaden Health Center", "university", "Palo Alto", "CA", "US",
                "https://vaden.stanford.edu/", decision_maker_title="Executive Director"),
    Institution("University of Texas at Austin Student Health Services", "university", "Austin", "TX", "US",
                "https://healthyhorns.utexas.edu/", decision_maker_title="Director"),
    Institution("University of Florida Student Health Care Center", "university", "Gainesville", "FL", "US",
                "https://shcc.ufl.edu/", decision_maker_title="Director"),
    Institution("Georgia Tech Student Health Center", "university", "Atlanta", "GA", "US",
                "https://health.gatech.edu/", decision_maker_title="Director"),
    Institution("Carnegie Mellon University Health Services", "university", "Pittsburgh", "PA", "US",
                "https://www.cmu.edu/health-services/", decision_maker_title="Medical Director",
                research_notes="Tech-focused student body. Strong fit for AI-first product pitch."),
]

# US FQHCs — pull from HRSA API, filtered to target metros
def pull_us_fqhcs(states: list[str] = None, limit: int = 50) -> list[Institution]:
    """
    Pull Federally Qualified Health Centers from HRSA's public API.
    FQHCs receive federal funding and are often more open to innovation pilots.
    """
    target_states = states or ["NY", "CA", "FL", "TX", "IL", "MA", "PA", "WA"]
    institutions = []

    print(f"  Pulling US FQHCs from HRSA for states: {', '.join(target_states)}...")

    for state in target_states:
        try:
            url = f"https://findahealthcenter.hrsa.gov/api/health-centers"
            params = {"query": state, "pageNumber": 1, "pageSize": 100}
            resp = requests.get(url, params=params, timeout=15)

            if resp.status_code != 200:
                # HRSA API occasionally changes — fall back to known centres
                print(f"    HRSA API unavailable for {state}, using seed data")
                continue

            data = resp.json()
            centers = data.get("data", data) if isinstance(data, dict) else data

            count = 0
            for c in centers:
                if count >= limit // len(target_states):
                    break
                name = c.get("name", c.get("site_name", ""))
                city = c.get("city", "")
                if not name or not city:
                    continue

                institutions.append(Institution(
                    name=name,
                    inst_type="FQHC",
                    city=city,
                    province_state=state,
                    country="US",
                    website=c.get("website", ""),
                    phone=c.get("phone", ""),
                    decision_maker_title="Executive Director / CEO",
                    source="HRSA API"
                ))
                count += 1

            time.sleep(0.5)

        except Exception as e:
            print(f"    Could not pull HRSA data for {state}: {e}")

    return institutions


def pull_chc_ontario_directory() -> list[Institution]:
    """
    Scrape CHC Ontario member directory.
    URL: https://www.chcontario.ca/our-members/
    """
    institutions = []
    print("  Scraping CHC Ontario member directory...")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (research bot for healthcare startup)"}
        resp = requests.get("https://www.chcontario.ca/our-members/", headers=headers, timeout=15)

        if resp.status_code != 200:
            print(f"    CHC Ontario returned {resp.status_code}, using seed data")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # CHC Ontario lists members — parse whatever structure exists
        links = soup.find_all("a", href=True)
        seen = set()

        for link in links:
            text = link.get_text(strip=True)
            href = link["href"]

            if (len(text) > 10 and
                ("health" in text.lower() or "community" in text.lower() or "centre" in text.lower()) and
                text not in seen and
                not any(skip in text.lower() for skip in ["login", "contact", "about", "news", "policy"])):

                seen.add(text)
                institutions.append(Institution(
                    name=text,
                    inst_type="CHC",
                    city="Ontario",
                    province_state="ON",
                    country="CA",
                    website=href if href.startswith("http") else f"https://www.chcontario.ca{href}",
                    decision_maker_title="Executive Director",
                    source="CHC Ontario Directory"
                ))

        print(f"    Found {len(institutions)} CHCs from directory")

    except Exception as e:
        print(f"    CHC Ontario scrape failed: {e}")

    return institutions


def build_institution_list(include_countries: list[str] = None) -> list[Institution]:
    """Combine all sources into a deduplicated institution list."""
    countries = include_countries or ["CA", "US"]
    all_institutions = []

    if "CA" in countries:
        print("\n[Stage 1] Building Ontario institution list...")
        all_institutions.extend(ONTARIO_UNIVERSITY_HEALTH_CENTRES)
        all_institutions.extend(ONTARIO_CHC_SEED)
        all_institutions.extend(ONTARIO_WALKIN_SEED)

        # Try to get more CHCs from live directory
        live_chcs = pull_chc_ontario_directory()
        # Deduplicate against seed
        seed_names = {i.name.lower() for i in ONTARIO_CHC_SEED}
        new_chcs = [c for c in live_chcs if c.name.lower() not in seed_names]
        all_institutions.extend(new_chcs[:30])  # cap at 30 additional

    if "US" in countries:
        print("\n[Stage 1] Building US institution list...")
        all_institutions.extend(US_UNIVERSITY_HEALTH_CENTRES)

        # Pull FQHCs from HRSA
        fqhcs = pull_us_fqhcs(limit=60)
        all_institutions.extend(fqhcs)

    # Tag sources for seed data
    for inst in all_institutions:
        if not inst.source:
            inst.source = "curated"

    print(f"\n  Total institutions to research: {len(all_institutions)}")
    return all_institutions


# ─────────────────────────────────────────────
# Stage 2 — Deep research + Groq LLM scoring
# ─────────────────────────────────────────────

def fetch_website_text(url: str, max_chars: int = 3000) -> str:
    """Fetch and clean text from a website. Returns empty string on failure."""
    if not url or not url.startswith("http"):
        return ""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts and style
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Clean up whitespace
        text = " ".join(text.split())
        return text[:max_chars]
    except Exception:
        return ""


def _fetch_additional_pages(base_url: str, max_pages: int = 2, max_chars: int = 1500) -> str:
    """
    Try common sub-pages to gather richer content for research.
    Returns concatenated text from the first pages that return content.
    """
    if not base_url or not base_url.startswith("http"):
        return ""

    # Normalise base: strip trailing slash
    base = base_url.rstrip("/")
    candidate_paths = ["/about", "/about-us", "/team", "/staff", "/leadership", "/contact"]

    collected = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    for path in candidate_paths:
        if len(collected) >= max_pages:
            break
        try:
            resp = requests.get(f"{base}{path}", headers=headers, timeout=8)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = " ".join(soup.get_text(separator=" ", strip=True).split())
            if len(text) > 100:  # only count pages with real content
                collected.append(f"[{path}]: {text[:max_chars]}")
        except Exception:
            continue

    return "\n\n".join(collected)


def call_groq(prompt: str, groq_api_key: str, model: str = "llama-3.3-70b-versatile") -> str:
    """Call Groq's OpenAI-compatible chat completions endpoint."""
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 800,
            "temperature": 0.1
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


_GROQ_RESEARCH_PROMPT = """\
You are helping MedPort, an AI healthcare startup founded by 5 university students in Toronto, identify the best early customers for their AI voice agent product.

MedPort's product:
- An AI voice agent (powered by ElevenLabs) that handles incoming patient calls for clinics
- Answers calls, books appointments, transcribes intake info, exports to Google Sheets or EHR
- Saves clinics 10-20 staff hours/week on phone admin
- Price: ~$300-600/month per clinic
- No EHR integration required — just a phone number redirect
- Founded by Indian immigrant students at a Toronto university

Ideal customer profile:
- Community health centres, university health services, walk-in clinics, FQHCs
- 2-30 practitioners, understaffed admin
- Open to working with student founders / startups
- Government-funded or grant-seeking
- NOT already using: Vocca, Assort Health, Nuance DAX, Suki, Klara, Luma Health

Institution to research:
Name: {name}
Type: {inst_type}
Location: {city}, {province_state}, {country}
Website: {website}
Known info: {research_notes}

Website content:
{website_text}

Respond ONLY with valid JSON (no markdown, no explanation):
{{
  "innovation_score": <1-10>,
  "accessibility_score": <1-10, where 10 = easy for student founder to get a meeting>,
  "fit_score": <1-10, where 10 = perfect match for MedPort>,
  "competitor_risk": "<none|low|medium|high>",
  "decision_maker_name": "<name if found on website, else empty string>",
  "decision_maker_title": "<best title to target>",
  "decision_maker_linkedin_search": "<LinkedIn search string to find them>",
  "research_notes": "<2-3 sentences: key signals, red flags, current tech situation>",
  "outreach_angle": "<1-2 sentence specific pitch hook for THIS institution>",
  "priority_tier": "<A|B|C>"
}}"""


def _parse_groq_response(content: str, inst: Institution) -> Institution:
    """Parse Groq JSON response and populate institution fields."""
    # Strip markdown code fences if the model wrapped the JSON
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        # Drop first and last fence lines
        content = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    data = json.loads(content)

    inst.innovation_score = int(data.get("innovation_score", inst.innovation_score) or 0)
    inst.accessibility_score = int(data.get("accessibility_score", inst.accessibility_score) or 0)
    inst.fit_score = int(data.get("fit_score", inst.fit_score) or 0)
    inst.competitor_risk = str(data.get("competitor_risk", inst.competitor_risk) or "none")

    # Only overwrite decision maker fields if we got something new and useful
    dm_name = str(data.get("decision_maker_name", "") or "").strip()
    if dm_name and not inst.decision_maker_name:
        inst.decision_maker_name = dm_name

    dm_title = str(data.get("decision_maker_title", "") or "").strip()
    if dm_title:
        inst.decision_maker_title = dm_title

    dm_linkedin = str(data.get("decision_maker_linkedin_search", "") or "").strip()
    if dm_linkedin:
        inst.decision_maker_linkedin = dm_linkedin

    research_notes = str(data.get("research_notes", "") or "").strip()
    if research_notes:
        # Preserve pre-existing notes (e.g. "Demo scheduled") by prepending
        if inst.research_notes and inst.research_notes not in research_notes:
            inst.research_notes = inst.research_notes.rstrip(".") + ". " + research_notes
        else:
            inst.research_notes = research_notes

    outreach_angle = str(data.get("outreach_angle", "") or "").strip()
    if outreach_angle:
        inst.outreach_angle = outreach_angle

    tier = str(data.get("priority_tier", "C") or "C").upper()
    inst.priority_rank = {"A": 1, "B": 2, "C": 3}.get(tier, 3)

    # Clamp scores to valid range
    inst.innovation_score = max(1, min(10, inst.innovation_score))
    inst.accessibility_score = max(1, min(10, inst.accessibility_score))
    inst.fit_score = max(1, min(10, inst.fit_score))

    return inst


def research_institution_groq(inst: Institution, groq_api_key: str) -> Institution:
    """
    Fetch website content (main page + up to 2 sub-pages) and send to Groq
    for structured research and scoring.
    """
    # Fetch main page
    main_text = fetch_website_text(inst.website, max_chars=3000)

    # Fetch additional sub-pages for richer context
    extra_text = _fetch_additional_pages(inst.website, max_pages=2, max_chars=1500)

    website_text = main_text
    if extra_text:
        website_text = main_text + "\n\n" + extra_text

    if not website_text:
        website_text = "(website not accessible)"

    prompt = _GROQ_RESEARCH_PROMPT.format(
        name=inst.name,
        inst_type=inst.inst_type,
        city=inst.city,
        province_state=inst.province_state,
        country=inst.country,
        website=inst.website or "(no website)",
        research_notes=inst.research_notes or "(none)",
        website_text=website_text[:4000],  # hard cap to stay within token budget
    )

    # Rate limiting: free tier is 30 RPM — sleep 2s between calls
    # Caller handles the sleep; here we handle 429 with one retry
    try:
        raw = call_groq(prompt, groq_api_key)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            print(" [429 rate limit, waiting 10s]", end="", flush=True)
            time.sleep(10)
            raw = call_groq(prompt, groq_api_key)
        else:
            raise

    try:
        inst = _parse_groq_response(raw, inst)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f" [Groq JSON parse error: {e} — falling back to keyword scoring]", end="", flush=True)
        inst = _keyword_score_fallback(inst, main_text)

    return inst


# ─────────────────────────────────────────────
# Keyword lists for fallback scoring
# ─────────────────────────────────────────────

INNOVATION_KEYWORDS = [
    "innovation", "digital health", "technology", "artificial intelligence", "ai",
    "machine learning", "pilot", "partnership", "research", "electronic health record",
    "ehr", "emr", "virtual care", "telehealth", "telemedicine", "digital",
    "modernize", "modernization", "transform", "transformation", "evidence-based",
    "data-driven", "analytics", "startup", "incubator", "accelerator", "grant",
    "funded", "award", "recognized", "leading", "forward-thinking", "cutting-edge",
    "innovative", "pioneering", "new model", "change", "improve", "efficiency"
]

FIT_KEYWORDS = [
    "phone", "appointment", "scheduling", "booking", "wait", "waiting",
    "overwhelmed", "understaffed", "staff shortage", "busy", "volume",
    "intake", "receptionist", "front desk", "administrative", "admin",
    "capacity", "high demand", "long wait", "patient experience", "access",
    "barrier", "underserved", "marginalized", "equity", "community",
    "after hours", "after-hours", "24/7", "on-call", "urgent"
]

COMPETITOR_KEYWORDS = [
    "vocca", "assort", "nuance", "suki", "klara", "luma health", "relatient",
    "bright.md", "well ai", "voice ai", "ai phone", "ai receptionist",
    "automated phone", "phone bot", "virtual receptionist", "ai assistant"
]

NEGATIVE_KEYWORDS = [
    "closed", "permanently closed", "no longer", "merged with", "acquired by"
]

ENTERPRISE_KEYWORDS = [
    "hospital system", "health network", "regional health", "university health network",
    "large hospital", "teaching hospital", "academic medical center", "health authority"
]

# Outreach angle templates by institution type
OUTREACH_TEMPLATES = {
    "CHC": (
        "Your team serves high volumes of patients with complex needs — your phones are likely non-stop. "
        "MedPort's AI voice agent handles patient intake calls, books appointments, and exports to your preferred system, "
        "freeing up 10-20 staff hours/week. We're offering free 30-day pilots to community health centres — "
        "would a 20-minute demo be worth your time?"
    ),
    "university": (
        "Student health centres get flooded with calls especially at semester start and flu season. "
        "MedPort's AI voice agent answers patient calls, books appointments, and handles intake — "
        "no EHR integration needed, just a phone number redirect. We're student founders ourselves "
        "and would love to show you a live demo. Can we get 20 minutes?"
    ),
    "FQHC": (
        "FQHCs serve the most underserved patients with the leanest admin teams. "
        "MedPort's AI voice agent takes patient intake calls, books appointments, and exports info to Google Sheets or your EHR — "
        "saving 10-20 hours/week at ~$300/month. We're offering free pilots. Would a quick demo make sense?"
    ),
    "walk-in": (
        "Walk-in clinics live and die by patient volume — and that starts with the phone. "
        "MedPort's AI voice agent handles every incoming call, captures intake, books appointments, "
        "and hands off to your team. No EHR needed. Would a 20-minute demo be worth it?"
    ),
    "specialty": (
        "Specialty clinics spend too much staff time on scheduling and intake calls. "
        "MedPort's AI voice agent handles that automatically, integrates with Google Sheets or your EHR, "
        "and costs less than one hour of staff time per month. Can we show you a live demo?"
    ),
    "dental": (
        "Dental practices waste hours every week on intake and confirmation calls. "
        "MedPort's AI voice agent handles it all — appointment booking, reminders, intake — "
        "for less than the cost of a part-time receptionist. 20-minute demo?"
    ),
}


def _keyword_score_fallback(inst: Institution, website_text: str) -> Institution:
    """
    Score an institution using keyword analysis of website text.
    100% free — no API calls. Used when no Groq key is available or as error fallback.
    """
    text_lower = (website_text + " " + inst.name + " " + inst.research_notes).lower()

    # ── Innovation score (1-10) ──
    innovation_hits = sum(1 for kw in INNOVATION_KEYWORDS if kw in text_lower)
    # Base by institution type
    type_innovation_base = {
        "university": 6, "CHC": 6, "FQHC": 5, "walk-in": 4, "specialty": 4, "dental": 3
    }.get(inst.inst_type, 4)
    # Keyword bonus (cap at +4)
    innovation_bonus = min(4, innovation_hits // 2)
    inst.innovation_score = min(10, type_innovation_base + innovation_bonus)

    # ── Accessibility score (1-10) ──
    # CHCs and university health centres are the most reachable for student founders
    type_accessibility = {
        "CHC": 8, "university": 7, "FQHC": 7, "walk-in": 6, "specialty": 5, "dental": 5
    }.get(inst.inst_type, 5)
    # Enterprise/large system penalty
    enterprise_hits = sum(1 for kw in ENTERPRISE_KEYWORDS if kw in text_lower)
    accessibility_penalty = min(3, enterprise_hits)
    # Known contact bonus
    contact_bonus = 1 if inst.decision_maker_name else 0
    inst.accessibility_score = max(1, min(10, type_accessibility - accessibility_penalty + contact_bonus))

    # ── Fit score (1-10) ──
    fit_hits = sum(1 for kw in FIT_KEYWORDS if kw in text_lower)
    type_fit_base = {
        "CHC": 7, "university": 7, "FQHC": 7, "walk-in": 6, "specialty": 5, "dental": 5
    }.get(inst.inst_type, 5)
    fit_bonus = min(3, fit_hits // 2)
    inst.fit_score = min(10, type_fit_base + fit_bonus)

    # ── Competitor risk ──
    competitor_hits = [kw for kw in COMPETITOR_KEYWORDS if kw in text_lower]
    if len(competitor_hits) >= 2:
        inst.competitor_risk = "high"
    elif len(competitor_hits) == 1:
        inst.competitor_risk = "medium"
    elif any(kw in text_lower for kw in ["phone system", "automated", "ivr", "interactive voice"]):
        inst.competitor_risk = "low"
    else:
        inst.competitor_risk = "none"

    # ── Research notes (free-form summary from keyword signals) ──
    signals = []
    if innovation_hits >= 4:
        signals.append("Strong innovation signals on website")
    elif innovation_hits >= 2:
        signals.append("Some tech/innovation language present")
    else:
        signals.append("Limited tech language — cold pitch needed")

    if fit_hits >= 4:
        signals.append("explicit scheduling/phone/access pain signals")
    elif fit_hits >= 2:
        signals.append("moderate fit signals")

    if competitor_hits:
        signals.append(f"possible competitor overlap: {', '.join(competitor_hits[:2])}")

    if not website_text:
        signals.append("website not accessible — verify manually")

    if not inst.research_notes:
        inst.research_notes = ". ".join(s.capitalize() for s in signals) + "."

    # ── Outreach angle ──
    if not inst.outreach_angle:
        inst.outreach_angle = OUTREACH_TEMPLATES.get(inst.inst_type, OUTREACH_TEMPLATES["walk-in"])

    # ── Priority tier → rank ──
    composite = inst.innovation_score + inst.accessibility_score + inst.fit_score
    if composite >= 22 and inst.competitor_risk in ("none", "low"):
        inst.priority_rank = 1   # Tier A
    elif composite >= 16:
        inst.priority_rank = 2   # Tier B
    else:
        inst.priority_rank = 3   # Tier C

    # Known warm intro = always Tier A
    if inst.decision_maker_name and ("intro" in inst.decision_maker_name.lower() or
                                      "demo scheduled" in inst.research_notes.lower() or
                                      "demo" in inst.research_notes.lower()):
        inst.priority_rank = 1

    # Build LinkedIn search hint
    if not inst.decision_maker_linkedin and inst.decision_maker_title:
        inst.decision_maker_linkedin = (
            f"{inst.decision_maker_title} {inst.name} LinkedIn"
        )

    return inst


def research_institution(inst: Institution, groq_api_key: str = None) -> Institution:
    """
    Research and score a single institution.
    Uses Groq LLM when groq_api_key is provided; falls back to keyword scoring otherwise.
    """
    if groq_api_key:
        return research_institution_groq(inst, groq_api_key)
    else:
        website_text = fetch_website_text(inst.website)
        return _keyword_score_fallback(inst, website_text)


def research_all(institutions: list[Institution],
                 limit: int = None,
                 resume_from: set = None,
                 groq_api_key: str = None) -> list[Institution]:
    """Research all institutions with progress output."""
    to_research = institutions
    if resume_from:
        to_research = [i for i in institutions if i.name not in resume_from]
    if limit:
        to_research = to_research[:limit]

    total = len(to_research)
    mode = "Groq AI (llama-3.3-70b)" if groq_api_key else "keyword scoring (no Groq key)"
    print(f"\n[Stage 2] Researching {total} institutions via {mode}...\n")

    for idx, inst in enumerate(to_research):
        print(f"  [{idx+1}/{total}] {inst.name} ({inst.city}, {inst.country})", end="", flush=True)

        inst = research_institution(inst, groq_api_key=groq_api_key)

        score = inst.innovation_score + inst.accessibility_score + inst.fit_score
        tier = {1: "A", 2: "B", 3: "C"}.get(inst.priority_rank, "C")
        print(f" -> Tier {tier} | Score {score}/30 | Competitor risk: {inst.competitor_risk}")

        if groq_api_key:
            # Groq free tier: 30 RPM — sleep 2s between calls
            time.sleep(2)
        else:
            # Be polite to web servers
            time.sleep(0.5)

    return institutions


# ─────────────────────────────────────────────
# Stage 3 — Output
# ─────────────────────────────────────────────

FIELDS = [
    "priority_rank", "name", "inst_type", "city", "province_state", "country",
    "innovation_score", "accessibility_score", "fit_score", "competitor_risk",
    "decision_maker_name", "decision_maker_title", "decision_maker_linkedin",
    "website", "phone", "email",
    "outreach_angle", "research_notes", "source"
]


def save_csv(institutions: list[Institution], output_path: str):
    """Save results to CSV sorted by priority."""
    # Sort: A tier first, then by composite score descending
    def sort_key(i):
        return (i.priority_rank, -(i.innovation_score + i.accessibility_score + i.fit_score))

    institutions.sort(key=sort_key)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for inst in institutions:
            row = asdict(inst)
            writer.writerow({k: row.get(k, "") for k in FIELDS})

    print(f"\n[Stage 3] Saved {len(institutions)} institutions to: {output_path}")


def load_existing_names(output_path: str) -> set:
    """Load names from existing CSV for resume support."""
    names = set()
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                names.add(row.get("name", ""))
    return names


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MedPort Customer Discovery Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Uses Groq free tier (llama-3.3-70b) for AI research.\n"
            "Get a free key at https://console.groq.com and set GROQ_API_KEY env var."
        )
    )
    parser.add_argument("--stage1-only", action="store_true",
                        help="Only build institution list, skip research")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max institutions to research (for testing)")
    parser.add_argument("--country", choices=["ca", "us", "both"], default="both",
                        help="Which countries to include")
    parser.add_argument("--resume", action="store_true",
                        help="Skip institutions already in output CSV")
    parser.add_argument("--output", default="medport_prospects.csv",
                        help="Output CSV filename (default: medport_prospects.csv)")
    parser.add_argument("--groq-key", default=None,
                        help="Groq API key (overrides GROQ_API_KEY env var)")
    args = parser.parse_args()

    countries = {
        "ca": ["CA"],
        "us": ["US"],
        "both": ["CA", "US"]
    }[args.country]

    print("\n" + "="*60)
    print("  MedPort Customer Discovery Engine")
    print("="*60)

    groq_key = args.groq_key or os.environ.get("GROQ_API_KEY")
    if not groq_key and not args.stage1_only:
        print("No GROQ_API_KEY found. Using keyword-based scoring (less accurate).")
        print("Get a free key at https://console.groq.com and set GROQ_API_KEY env var.")

    # Stage 1
    institutions = build_institution_list(include_countries=countries)

    if args.stage1_only:
        save_csv(institutions, args.output)
        print(f"\nStage 1 complete. {len(institutions)} institutions saved (unscored).")
        return

    # Stage 2
    resume_from = load_existing_names(args.output) if args.resume else set()
    if resume_from:
        print(f"\nResuming — skipping {len(resume_from)} already-researched institutions")

    institutions = research_all(
        institutions,
        limit=args.limit,
        resume_from=resume_from,
        groq_api_key=groq_key,
    )

    # Stage 3
    save_csv(institutions, args.output)

    # Print summary
    tier_a = [i for i in institutions if i.priority_rank == 1]
    tier_b = [i for i in institutions if i.priority_rank == 2]
    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  Tier A (reach out this week): {len(tier_a)}")
    print(f"  Tier B (reach out this month): {len(tier_b)}")
    print(f"  Total: {len(institutions)}")
    print(f"\nTop 5 priority targets:")
    for inst in institutions[:5]:
        print(f"  - {inst.name} ({inst.city}) — Score: {inst.innovation_score + inst.accessibility_score + inst.fit_score}/30")
        if inst.outreach_angle:
            print(f"    Hook: {inst.outreach_angle[:120]}...")
    print(f"\nFull results in: {args.output}")
    print()


if __name__ == "__main__":
    main()
