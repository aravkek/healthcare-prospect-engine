# Healthcare Prospect Engine

An AI-powered customer discovery tool that finds and scores healthcare institutions most likely to adopt new technology — built to help early-stage healthcare startups identify and prioritize outreach targets.

## What it does

**Stage 1 — Discovery:** Pulls institutions from:
- Ontario Community Health Centre directory (CHCs)
- Curated Ontario university health services (14 campuses)
- US Federally Qualified Health Centers via HRSA public API
- Curated walk-in clinic chains and specialty clinics

**Stage 2 — AI Research:** For each institution, uses Groq's free LLM API (llama-3.3-70b) to:
- Scrape their website + about/team pages
- Score on Innovation (1-10), Accessibility (1-10), and Fit (1-10)
- Identify decision makers and their titles
- Assess competitor risk
- Generate a specific outreach angle

**Stage 3 — Dashboard:** Streamlit dashboard with filters, tier visualization, and one-click CSV export.

## Stack

- Python 3.10+
- [Groq API](https://console.groq.com) (free tier — llama-3.3-70b)
- [HRSA Find a Health Center API](https://findahealthcenter.hrsa.gov) (free, no key)
- BeautifulSoup4 for web scraping
- Streamlit for dashboard

## Setup

```bash
git clone https://github.com/aravkek/healthcare-prospect-engine
cd healthcare-prospect-engine
pip install -r requirements.txt

# Get a free Groq API key at console.groq.com
echo "GROQ_API_KEY=your_key_here" > .env
```

## Run

```bash
# Full discovery run (Ontario + US, ~100 institutions)
source .env && python customer_discovery.py --country both

# Ontario only, first 10 institutions (quick test)
source .env && python customer_discovery.py --country ca --limit 10

# Stage 1 only (no AI scoring, instant)
python customer_discovery.py --stage1-only

# Resume interrupted run
source .env && python customer_discovery.py --resume
```

## Dashboard

```bash
streamlit run medport_dashboard.py
```

Or deploy free to [Streamlit Community Cloud](https://share.streamlit.io) — connect your GitHub repo, add `GROQ_API_KEY` as a secret.

## Daily automated runs

```bash
# Install a macOS cron job (runs at 8am daily)
bash setup_cron.sh
```

## Ideal customer profile this tool is tuned for

- Community health centres and FQHCs (government-funded, innovation-friendly, understaffed admin)
- University / college health services (high call volume, tech-adjacent)
- Walk-in clinics with 2-30 practitioners
- Institutions NOT already using AI phone tools (Nuance, Vocca, Assort)

Scoring weights accessibility for student founders — i.e., it prioritizes places where a cold email from a student actually works.

## Scoring methodology

| Signal | Weight |
|--------|--------|
| Innovation keywords on website | +1-4 to innovation score |
| Institution type base score | Sets baseline for all 3 dimensions |
| Enterprise/large system penalty | -1 to -3 on accessibility |
| Known warm contact | Forces Tier A |
| Competitor product detected | Sets competitor_risk to medium/high |

Groq LLM scoring replaces simple keyword matching with genuine reasoning about the institution's website content, tech posture, and fit.

## Output

`medport_prospects.csv` — sorted by priority tier (A/B/C) then composite score, with columns:

`priority_rank, name, inst_type, city, province_state, country, innovation_score, accessibility_score, fit_score, competitor_risk, decision_maker_name, decision_maker_title, decision_maker_linkedin, website, phone, outreach_angle, research_notes, source`
