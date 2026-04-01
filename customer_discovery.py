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
from pathlib import Path

# Load .env file if present (before any os.environ reads)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    with open(_env_path) as _ef:
        for _line in _ef:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

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

def load_seeds(seeds_file: str = None) -> list[Institution]:
    """
    Load seed institutions from a CSV file.
    Default path: seeds.csv in the same directory as this script.

    The CSV is kept out of the public repo (listed in .gitignore) so the
    curated target list stays private.
    """
    if seeds_file is None:
        seeds_file = str(Path(__file__).parent / "seeds.csv")

    if not os.path.exists(seeds_file):
        print(
            f"\nERROR: seeds.csv not found at: {seeds_file}\n"
            "Copy seeds.csv to this directory. "
            "(Kept private — not in the public repo.)"
        )
        sys.exit(1)

    institutions = []
    with open(seeds_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            institutions.append(Institution(
                name=row.get("name", ""),
                inst_type=row.get("inst_type", ""),
                city=row.get("city", ""),
                province_state=row.get("province_state", ""),
                country=row.get("country", ""),
                website=row.get("website", ""),
                phone=row.get("phone", ""),
                decision_maker_name=row.get("decision_maker_name", ""),
                decision_maker_title=row.get("decision_maker_title", ""),
                research_notes=row.get("research_notes", ""),
                source="curated",
            ))

    print(f"  Loaded {len(institutions)} seed institutions from {seeds_file}")
    return institutions

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


def build_institution_list(
    include_countries: list[str] = None,
    seeds_file: str = None,
) -> list[Institution]:
    """Combine all sources into a deduplicated institution list."""
    countries = include_countries or ["CA", "US"]
    all_institutions = []

    # Load all seeds and split by country
    seeds = load_seeds(seeds_file)
    seed_names = {i.name.lower() for i in seeds}

    if "CA" in countries:
        print("\n[Stage 1] Building Ontario institution list...")
        ca_seeds = [s for s in seeds if s.country == "CA"]
        all_institutions.extend(ca_seeds)

        # Try to get more CHCs from live directory
        live_chcs = pull_chc_ontario_directory()
        chc_seed_names = {i.name.lower() for i in ca_seeds if i.inst_type == "CHC"}
        new_chcs = [c for c in live_chcs if c.name.lower() not in chc_seed_names]
        all_institutions.extend(new_chcs[:30])  # cap at 30 additional

    if "US" in countries:
        print("\n[Stage 1] Building US institution list...")
        us_seeds = [s for s in seeds if s.country == "US"]
        all_institutions.extend(us_seeds)

        # Pull FQHCs from HRSA
        fqhcs = pull_us_fqhcs(limit=60)
        all_institutions.extend(fqhcs)

    # Tag sources for any institution missing a source tag
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


def _fetch_additional_pages(base_url: str, max_pages: int = 3, max_chars: int = 2000) -> str:
    """
    Fetch sub-pages most likely to reveal booking method, staffing, and tech stack.
    Priority: appointments/booking pages first, then about/team/contact.
    """
    if not base_url or not base_url.startswith("http"):
        return ""

    base = base_url.rstrip("/")
    # Booking/appointment pages first — these reveal phone vs online dependency
    candidate_paths = [
        "/appointments", "/book", "/booking", "/book-appointment",
        "/make-an-appointment", "/schedule", "/services/appointments",
        "/patient-services", "/new-patients", "/new-patient",
        "/about", "/about-us", "/team", "/staff", "/contact",
    ]

    collected = []
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

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
            if len(text) > 100:
                collected.append(f"[{path}]: {text[:max_chars]}")
        except Exception:
            continue

    return "\n\n".join(collected)


# Known online booking / EHR platforms — presence means they have non-phone booking
ONLINE_BOOKING_PLATFORMS = {
    "janeapp.com": "Jane App",
    "jane.app": "Jane App",
    "zocdoc.com": "Zocdoc",
    "mychart": "Epic MyChart",
    "epic.com": "Epic",
    "calendly.com": "Calendly",
    "acuityscheduling.com": "Acuity Scheduling",
    "simplepractice.com": "SimplePractice",
    "cognisantmd.com": "Ocean (CognisantMD)",
    "ocean.cognisantmd": "Ocean",
    "telus.com/health": "Telus Health",
    "qhrtechnologies": "QHR/Accuro",
    "accuro": "Accuro",
    "meditech": "Meditech",
    "athenahealth": "Athenahealth",
    "drchrono": "DrChrono",
    "healthengine": "HealthEngine",
    "patientnotebook": "Patient Notebook",
    "phreesia": "Phreesia",
    "opendental": "Open Dental",
    "dentrix": "Dentrix",
    "booksy": "Booksy",
    "mindbody": "Mindbody",
    "squareup.com/appointments": "Square Appointments",
    "patientpop": "PatientPop",
    "practicefusion": "Practice Fusion",
    "kareo": "Kareo",
    "luminare": "Luminare Health",
    "nextech": "NexTech",
    "netsmart": "Netsmart",
    "advancedmd": "AdvancedMD",
    "eclinicalworks": "eClinicalWorks",
    "book online": "generic online booking",
    "request an appointment": "online appointment request",
    "schedule online": "online scheduling",
}

# Direct AI voice/phone competitors — if detected, flag as competitor risk
# Includes Canadian and US players
AI_VOICE_COMPETITORS = {
    # Canadian
    "novoflow": "Novoflow",
    "decoda": "Decoda Health",
    "pine ai": "Pine AI",
    "pineai": "Pine AI",
    "league.com": "League",
    "inputhealth": "InputHealth",
    "talksoft": "Talksoft",
    # US voice/phone AI
    "hyro.ai": "Hyro",
    "hyro": "Hyro",
    "syllable": "Syllable",
    "artera": "Artera",
    "weave": "Weave Communications",
    "getweave": "Weave",
    "andorhealth": "Andor Health",
    "orbita": "Orbita",
    "vocca": "Vocca",
    "assort health": "Assort Health",
    "assortHealth": "Assort Health",
    "nuance": "Nuance DAX",
    "suki": "Suki",
    "klara": "Klara",
    "luma health": "Luma Health",
    "lumahealth": "Luma Health",
    "relatient": "Relatient",
    "notable health": "Notable Health",
    "notablehealth": "Notable Health",
    "kyruus": "Kyruus",
    "mend.com": "Mend",
    "updox": "Updox",
    "bright.md": "Bright.md",
    "healthjoy": "HealthJoy",
    "authenticx": "Authenticx",
    "rio.ai": "Rio AI",
    "nabla": "Nabla",
    "deepscribe": "DeepScribe",
    "abridge": "Abridge",
    "ambience": "Ambience Healthcare",
}

# Signals that the clinic is phone-dependent for booking (high MedPort fit)
PHONE_DEPENDENCY_SIGNALS = [
    "call us to book", "call to book", "call to schedule", "phone to book",
    "appointments by phone", "appointment by phone", "call our office",
    "please call", "to schedule an appointment, call", "to book, call",
    "appointments are available by calling", "contact us by phone",
    "due to high call volume", "high call volume", "leave a message",
    "please leave a message", "our lines are busy", "call during office hours",
    "appointments by calling", "reach us by phone", "phone only",
    "call reception", "call the clinic", "no online booking",
]

# Admin overload signals
ADMIN_OVERLOAD_SIGNALS = [
    "high call volume", "high volume", "please be patient", "allow 2-3 business days",
    "allow 3-5 business days", "limited appointment availability",
    "currently not accepting new patients", "waitlist", "wait list",
    "we are experiencing", "understaffed", "staff shortage",
    "reduced hours", "limited staff",
]


def _detect_booking_system(url: str) -> dict:
    """
    Scan website HTML source for embedded booking platforms and phone-dependency signals.
    Returns a dict with findings — this is the most reliable signal for MedPort fit.
    """
    result = {
        "online_booking_platforms": [],
        "phone_dependency_signals": [],
        "admin_overload_signals": [],
        "has_online_booking": False,
        "phone_dependent": False,
    }

    if not url or not url.startswith("http"):
        return result

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return result

        # Search raw HTML (catches embedded iframes, script srcs, etc.)
        html_lower = resp.text.lower()
        page_text_lower = " ".join(BeautifulSoup(resp.text, "html.parser").get_text().split()).lower()

        for signature, platform_name in ONLINE_BOOKING_PLATFORMS.items():
            if signature in html_lower and platform_name not in result["online_booking_platforms"]:
                result["online_booking_platforms"].append(platform_name)

        for signal in PHONE_DEPENDENCY_SIGNALS:
            if signal in page_text_lower:
                result["phone_dependency_signals"].append(signal)

        for signal in ADMIN_OVERLOAD_SIGNALS:
            if signal in page_text_lower:
                result["admin_overload_signals"].append(signal)

        competitors_found = []
        for signature, comp_name in AI_VOICE_COMPETITORS.items():
            if signature in html_lower or signature in page_text_lower:
                if comp_name not in competitors_found:
                    competitors_found.append(comp_name)
        result["competitors_detected"] = competitors_found

        result["has_online_booking"] = len(result["online_booking_platforms"]) > 0
        result["phone_dependent"] = (
            len(result["phone_dependency_signals"]) >= 1
            or (not result["has_online_booking"] and len(result["phone_dependency_signals"]) == 0)
        )

    except Exception:
        pass

    return result


def _ddg_search(query: str, max_results: int = 3) -> str:
    """Free DuckDuckGo search. Returns snippet text from top results."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result__snippet")[:max_results]:
            text = r.get_text(strip=True)
            if text:
                results.append(text)
        return " | ".join(results)
    except Exception:
        return ""


def _gather_external_intel(name: str, city: str, country: str, website: str) -> dict:
    """
    Run multiple targeted searches to gather external signals.
    Returns a dict with patient complaints, job postings, news, competitor mentions.
    """
    intel = {
        "patient_complaints": "",
        "job_postings": "",
        "recent_news": "",
        "competitor_mentions": "",
        "patient_count_signal": "",
    }

    time.sleep(0.3)  # be polite between searches

    # 1. Patient complaints about phones/wait — the strongest fit signal
    complaints = _ddg_search(
        f'"{name}" reviews "phone" OR "wait time" OR "hard to reach" OR "can\'t get through" OR "busy signal"',
        max_results=3,
    )
    if complaints:
        intel["patient_complaints"] = complaints

    time.sleep(0.3)

    # 2. Job postings for admin/receptionist — signals understaffed admin
    job_search = _ddg_search(
        f'"{name}" "medical receptionist" OR "medical secretary" OR "patient services representative" OR "administrative assistant" site:indeed.com OR site:linkedin.com OR site:workopolis.com',
        max_results=2,
    )
    if not job_search:
        job_search = _ddg_search(
            f'{name} {city} receptionist OR "front desk" hiring 2025 OR 2026',
            max_results=2,
        )
    if job_search:
        intel["job_postings"] = job_search

    time.sleep(0.3)

    # 3. Recent news — expansions, funding, staffing crises
    news = _ddg_search(
        f'"{name}" 2025 OR 2026 expansion OR funding OR "new clinic" OR "phone system" OR technology OR AI',
        max_results=2,
    )
    if news:
        intel["recent_news"] = news

    time.sleep(0.3)

    # 4. Competitor mentions — are they already using a competitor?
    competitor_names = "Novoflow OR Decoda OR Hyro OR Syllable OR Artera OR Nuance OR Vocca OR Weave OR Klara OR \"Luma Health\" OR \"Assort Health\" OR \"Pine AI\""
    comp = _ddg_search(f'"{name}" {competitor_names}', max_results=2)
    if comp:
        intel["competitor_mentions"] = comp

    time.sleep(0.3)

    # 5. Patient volume signals
    volume = _ddg_search(
        f'"{name}" "patients" OR "visits per year" OR "serves" OR "patient population" OR "annual visits"',
        max_results=2,
    )
    if volume:
        intel["patient_count_signal"] = volume

    return intel


def call_groq(prompt: str, groq_api_key: str, model: str = "llama-3.1-8b-instant") -> str:
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
You are a sales intelligence analyst helping MedPort — a 5-person student startup from Toronto — craft cold outreach so perfectly targeted that recipients feel "I can't believe this landed in my inbox at exactly the right time."

MedPort builds AI voice agents that answer patient phone calls 24/7, book appointments, capture intake, and sync to Google Sheets or any EHR. Setup = redirect a phone number. Cost = $300-600/month. No IT project. No EHR integration required. Free 30-day pilot for early partners.

The ONLY institutions worth emailing are ones where:
1. Phone calls are the PRIMARY or ONLY booking method (not self-serve online)
2. They're small-to-mid enough that a student founder can reach the decision maker directly
3. No competitor AI phone product is already deployed there

---
INSTITUTION PROFILE:
Name: {name}
Type: {inst_type}
Location: {city}, {province_state}, {country}
Website: {website}

BOOKING SYSTEM SCAN (from raw HTML — highly reliable):
  Online booking platforms detected in HTML: {online_platforms}
  Phone-dependency phrases found verbatim on site: {phone_signals}
  Admin overload phrases found verbatim on site: {admin_signals}
  Competitor AI tools detected on site: {competitors_detected}

WEBSITE TEXT (main page + appointment/about pages):
{website_text}

EXTERNAL INTELLIGENCE:
  Patient complaints about phones/wait: {patient_complaints}
  Job postings for admin/receptionist roles: {job_postings}
  Recent news (expansion, funding, staffing): {recent_news}
  Competitor product mentions in news/reviews: {competitor_mentions}
  Patient volume signals: {patient_count_signal}

---
YOUR JOB:

1. SCORE this institution honestly on three dimensions:
   - fit_score (1-10): ONLY high if phones are clearly the booking method AND they show admin burden
     * 9-10: Phone-only booking confirmed, patient complaints about wait, or job postings for reception = PERFECT
     * 7-8: Phone likely primary, mixed signals
     * 4-6: Has online booking but phones still used for intake/overflow
     * 1-3: Fully online self-serve, very little phone burden
   - innovation_score (1-10): Tech adoption signals, past startup partnerships, digital health language, government innovation grants
   - accessibility_score (1-10): Can a 22-year-old student founder get a reply?
     * 9-10: Small org, named director reachable by email, warm intro exists
     * 6-8: Mid-size, email reach is realistic
     * 1-5: Large health system, hospital network, requires procurement process

2. WRITE the outreach angle like THIS:
   BAD (generic, will be ignored): "Your clinic likely receives many calls. MedPort can help."
   GOOD (specific, evidence-based, will convert):
     "Your site still says 'call [phone] to book' — we found three Google reviews in the last 6 months where patients mentioned they 'couldn't get through.' MedPort's AI picks up every call, books the appointment, and logs it in your system. Takes 15 minutes to set up. Free for 30 days."

   The outreach_angle MUST:
   - Reference a SPECIFIC thing found in the research (a phrase from their website, a patient complaint, a job posting, a news item, their patient population)
   - Name their EXACT pain (not generic "phone burden" — be specific: "your phones go unanswered after 4pm", "patients waiting 3+ days for a callback", "you're hiring a receptionist while understaffed")
   - Make the value prop feel like it was written for them, not copy-pasted
   - End with a zero-risk ask ("free pilot, just a phone number redirect, 20-minute demo")

3. WRITE personalization_hooks: 3 specific, surprising things you found that Arav can reference when he emails. Each should be something the recipient will think "how did they know that?" Examples: a phrase from their website, a patient review quote, a news item, a job posting, their specific patient count.

4. FLAG competitor risk: If ANY of these are found — Novoflow, Decoda Health, Pine AI, Hyro, Syllable, Artera, Nuance, Vocca, Assort Health, Suki, Weave, Klara, Luma Health, Notable Health, Andor Health, Orbita — mark competitor_risk as high and name them.

Respond ONLY with valid JSON (no markdown fences, no explanation):
{{
  "innovation_score": <1-10>,
  "accessibility_score": <1-10>,
  "fit_score": <1-10>,
  "phone_dependency": "<phone-only|mixed|online-only|unknown>",
  "booking_system_used": "<platform name OR 'phone only' OR 'unknown'>",
  "estimated_weekly_call_volume": "<low <50/wk | medium 50-200/wk | high 200+/wk | unknown>",
  "competitor_risk": "<none|low|medium|high>",
  "competitors_found": "<comma-separated list or 'none'>",
  "existing_ai_tools": "<tools found or 'none detected'>",
  "decision_maker_name": "<name from website/about page, else empty>",
  "decision_maker_title": "<exact title to cold-email at this institution type>",
  "decision_maker_linkedin_search": "<first last title org LinkedIn>",
  "personalization_hooks": "<hook 1> | <hook 2> | <hook 3>",
  "research_notes": "<4-5 sentences: booking method evidence with quotes, patient volume, admin burden signals, tech posture, honest assessment of whether they'll say yes>",
  "outreach_angle": "<2-3 sentences — specific, evidence-based, references real finding, ends with zero-risk ask. Written AS Arav, a student founder who did his homework.>",
  "priority_tier": "<A = email this week | B = email this month | C = pipeline only>"
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

    # Fold personalization hooks into research notes for visibility
    hooks = str(data.get("personalization_hooks", "") or "").strip()
    research_notes = str(data.get("research_notes", "") or "").strip()
    if hooks:
        research_notes = f"[HOOKS: {hooks}] {research_notes}"
    if research_notes:
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
    Deep research: booking system scan + multi-page scrape + DuckDuckGo search + Groq scoring.
    """
    # 1. Scan HTML source for booking platform signatures and phone-dependency signals
    booking_scan = _detect_booking_system(inst.website)

    # 2. Fetch main page text
    main_text = fetch_website_text(inst.website, max_chars=2500)

    # 3. Fetch appointment/about/team sub-pages
    extra_text = _fetch_additional_pages(inst.website, max_pages=3, max_chars=2000)

    website_text = main_text
    if extra_text:
        website_text = main_text + "\n\n" + extra_text

    # 4. Gather external intelligence (patient complaints, job postings, news, competitors)
    intel = _gather_external_intel(inst.name, inst.city, inst.country, inst.website)

    if not website_text:
        website_text = "(website not accessible)"

    prompt = _GROQ_RESEARCH_PROMPT.format(
        name=inst.name,
        inst_type=inst.inst_type,
        city=inst.city,
        province_state=inst.province_state,
        country=inst.country,
        website=inst.website or "(no website)",
        online_platforms=", ".join(booking_scan["online_booking_platforms"]) or "none detected",
        phone_signals="; ".join(booking_scan["phone_dependency_signals"][:5]) or "none detected",
        admin_signals="; ".join(booking_scan["admin_overload_signals"][:3]) or "none detected",
        competitors_detected=", ".join(booking_scan.get("competitors_detected", [])) or "none detected",
        website_text=website_text[:1800],
        patient_complaints=(intel["patient_complaints"] or "none found")[:300],
        job_postings=(intel["job_postings"] or "none found")[:200],
        recent_news=(intel["recent_news"] or "none found")[:200],
        competitor_mentions=(intel["competitor_mentions"] or "none found")[:200],
        patient_count_signal=(intel["patient_count_signal"] or "unknown")[:150],
    )

    # Rate limiting: free tier 6000 tokens/min for llama-3.3-70b
    # With deep research prompts (~2500 tokens each), allow ~15s between calls
    # Retry up to 3 times with exponential backoff on 429
    raw = None
    for attempt in range(3):
        try:
            raw = call_groq(prompt, groq_api_key)
            break
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                wait = 20 * (attempt + 1)  # 20s, 40s, 60s
                print(f" [rate limit, waiting {wait}s]", end="", flush=True)
                time.sleep(wait)
            else:
                raise
    if raw is None:
        raise RuntimeError("Groq API rate limit — all retries exhausted")

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
            # 8B instant model: 30,000 TPM — 5s between calls is safe
            # 70B versatile model: 6,000 TPM — use --groq-model llama-3.3-70b-versatile + longer sleep
            time.sleep(5)
        else:
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
# Supabase integration
# ─────────────────────────────────────────────

def get_supabase_client(service_role_key: str, url: str):
    from supabase import create_client
    return create_client(url, service_role_key)


def upsert_to_supabase(
    institutions: list[Institution],
    supabase_url: str,
    service_role_key: str,
):
    """
    Upsert all institutions to the Supabase prospects table.
    Preserves CRM fields (status, assigned_to, contact_notes) on conflict —
    only discovery/scoring fields are overwritten.
    """
    client = get_supabase_client(service_role_key, supabase_url)
    rows = []
    for inst in institutions:
        row = {
            "name": inst.name,
            "inst_type": inst.inst_type,
            "city": inst.city,
            "province_state": inst.province_state,
            "country": inst.country,
            "website": inst.website,
            "phone": inst.phone,
            "email": inst.email,
            "decision_maker_name": inst.decision_maker_name,
            "decision_maker_title": inst.decision_maker_title,
            "decision_maker_linkedin": inst.decision_maker_linkedin,
            "innovation_score": inst.innovation_score,
            "accessibility_score": inst.accessibility_score,
            "fit_score": inst.fit_score,
            "competitor_risk": inst.competitor_risk,
            "priority_rank": inst.priority_rank,
            "research_notes": inst.research_notes,
            "outreach_angle": inst.outreach_angle,
            "source": inst.source,
        }
        rows.append(row)

    # Upsert in batches of 50
    for i in range(0, len(rows), 50):
        batch = rows[i : i + 50]
        client.table("prospects").upsert(
            batch, on_conflict="name", ignore_duplicates=False
        ).execute()

    print(f"\n[Supabase] Upserted {len(rows)} institutions to prospects table.")


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
    parser.add_argument(
        "--seeds-file",
        default=None,
        help="Path to seeds.csv (default: seeds.csv in script directory)",
    )
    parser.add_argument(
        "--supabase",
        action="store_true",
        default=False,
        help="Upsert results to Supabase after Stage 3 (requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)",
    )
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
    institutions = build_institution_list(
        include_countries=countries,
        seeds_file=args.seeds_file,
    )

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

    # Supabase upsert (optional — requires --supabase flag and env vars)
    if args.supabase:
        supabase_url = os.environ.get("SUPABASE_URL", "")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if supabase_url and supabase_key:
            try:
                upsert_to_supabase(institutions, supabase_url, supabase_key)
            except Exception as e:
                print(f"\n[Supabase] Upsert failed: {e}")
        else:
            print(
                "\n[Supabase] Skipping upsert — SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set."
            )

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
