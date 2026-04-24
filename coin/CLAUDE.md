# Coin — Career Ops Engine

**Updated:** 2026-04-24 | **Status:** Phase 1 — Core pipeline build

> **Session Start:** Always read `docs/state/project-state.md` first.
> **Context Budget:** Load only CLAUDE.md at startup. Load other docs on demand.

---

## What This Project Is

Coin is an agentic job-hunting pipeline for Sean Ivins (PMP, MBA). It scrapes
high-compensation roles across Technical Program Management, Product Management,
and Technical Sales Engineering, then dynamically rewrites his resume to match
each target lane. The goal is to maximize total compensation (base + RSUs/equity).

---

## Identity — Sean Ivins

This is the canonical professional baseline. Every resume output must draw from here.

**Title:** Senior Technical Program Manager | 15+ years experience
**Credentials:** PMP, MBA
**Domains:** Wireless infrastructure, IoT systems, B2B SaaS, aerospace/defense

### Career Highlights (always available to the transformer)

| Story | Metric | Weight by Lane |
|-------|--------|----------------|
| Cox Communications True Local Labs — full program exec, concept to production | $1M Year 1 revenue, 12 months ahead of schedule | TPM, PM |
| Fractional COO TitanX — scaled sales intelligence platform | $27M Series A in under 2 years | PM, Sales |
| Utah Broadband — drove revenue growth to acquisition | $27M acquisition by Boston Omaha Corporation | TPM, Sales |
| Enterprise Account Manager — ARR growth | $6M → $13M ARR | Sales, TPM |
| Global engineering orchestration | Cross-continental teams | TPM |

**Methodologies:** Agile, Waterfall, Requirement Decomposition, Cross-Functional Orchestration

---

## Target Lanes

| Lane ID | Label | Resume Emphasis |
|---------|-------|----------------|
| `tpm-high` | High-Tier TPM | Cox program exec, global eng orchestration, PMP credential |
| `pm-ai` | AI Product Manager | TitanX product scaling, SaaS domain, data-driven outcomes |
| `sales-ent` | Enterprise Technical Sales | $6M→$13M ARR, TitanX, domain credibility (RF/IoT/SaaS) |

---

## Non-Negotiable Rules

| # | Rule |
|---|------|
| 1 | Never fabricate metrics — only use data from `data/resumes/base.json` or user-provided facts |
| 2 | Never write a resume that doesn't specify a target lane — all output is lane-specific |
| 3 | Compensation filter minimum: $180K base — never surface roles below this threshold without explicit user override |
| 4 | Never store API keys in code — always read from environment variables |
| 5 | Never commit `data/db/pipeline.db` or `.env` to git |
| 6 | All Claude API calls must use prompt caching where input tokens exceed 1024 |

---

## Architecture Constraints

- **Language:** Python 3.11+ only
- **Database:** SQLite (`data/db/pipeline.db`) — no external DB dependencies in Phase 1
- **Claude API:** `claude-sonnet-4-6` for analysis/transformation; batch for bulk JD processing
- **Scraping:** `httpx` + `BeautifulSoup4` — no Selenium/Playwright unless explicitly needed
- **Terminal output:** `rich` library — Bloomberg-style cards matching holo's aesthetic
- **No ORM:** raw `sqlite3` module — schema in `careerops/pipeline.py`

---

## Self-Verification

After writing or modifying code, ALWAYS run:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short 2>&1 | tail -20
.venv/bin/python -c "from careerops import scraper, analyzer, transformer, pipeline, compensation; print('imports OK')"
```

Fix all errors before marking work complete.

---

## Git Commit Format

```bash
git commit -m "type: your message

Authored by: Sean @ coin"
```

Prefixes: `feat:` | `fix:` | `refactor:` | `docs:` | `test:` | `chore:`

---

## Directory Structure

```
coin/
  careerops/          # Core Python modules
    scraper.py        # Job board fetcher (LinkedIn, Indeed, Levels.fyi)
    analyzer.py       # JD parser — Claude API extracts skills + comp bands
    transformer.py    # Resume rewriter — lane-aware Claude API agent
    pipeline.py       # SQLite CRUD for application tracking
    compensation.py   # Salary band extraction + filtering
  data/
    resumes/
      base.json       # Sean's canonical professional data model
      generated/      # Lane-specific output resumes (gitignored)
    db/
      pipeline.db     # Application tracking DB (gitignored)
  docs/
    state/
      project-state.md
    tasks/prompts/
      pending/        # Task prompt files ready to run
      complete/       # Completed task prompts (archive)
    roadmap.md
  scripts/
    start.sh
    end.sh
  tests/
  .claude/commands/   # Slash commands
  config.py           # Tunable thresholds and targets
  requirements.txt
  .env.example
```

---

## External Services

| Service | Purpose | Rule |
|---------|---------|------|
| Anthropic API | JD analysis + resume transformation | Use `claude-sonnet-4-6`; cache prompts >1024 tokens |
| LinkedIn (HTML) | Job discovery — primary source | Respect rate limits; 2s delay between requests |
| Indeed (HTML) | Job discovery — secondary source | Same rate limit rules |
| Levels.fyi | Compensation verification | Scrape comp bands for target companies |
| Glassdoor (HTML) | Salary range cross-reference | Tertiary — use only when band is unverified |

---

## Contacts

Sean Ivins — sean@lifestory.co
