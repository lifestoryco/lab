# Coin — Career Ops Engine

**Updated:** 2026-04-25 | **Status:** Phase 1 MVP — modal skill architecture

> **Session Start:** Always read `docs/state/project-state.md` first.
> **Context Budget:** Load CLAUDE.md + `.claude/skills/coin/SKILL.md` at startup.
> Load mode files and other docs on demand.

---

## What This Project Is

Coin is an agentic job-hunting pipeline for Sean Ivins (PMP, MBA). It
scrapes high-comp roles across **four** target archetypes, scores fit, and
generates lane-tailored resumes — **all inside Sean's Claude Code
subscription session**. There is no Anthropic API key. Python handles
I/O (scraping, SQLite, file saves); Claude (the host session) handles
reasoning (JD parsing, resume prose, recommendations).

The goal is to maximize Sean's total compensation (base + RSU / equity).

---

## Identity — Sean Ivins

This is the canonical professional baseline. Every resume output draws from
`data/resumes/base.py` (the PROFILE dict). North Star pitches per archetype
live in `config/profile.yml`.

**Title:** Senior Technical Program Manager · 15+ years
**Credentials:** PMP, MBA
**Domains:** Wireless infrastructure, IoT systems, B2B SaaS, aerospace/defense, RF

### Career proof points

| Story ID | Metric |
|---|---|
| `cox_true_local_labs` | $1M Year 1 revenue, 12 months ahead of schedule |
| `titanx_fractional_coo` | $27M Series A in under 2 years |
| `utah_broadband_acquisition` | $27M acquisition by Boston Omaha Corporation |
| `arr_growth_6m_to_13m` | $6M → $13M ARR (Enterprise AM) |
| `global_engineering_orchestration` | Cross-continental delivery (wireless, aerospace) |

---

## The four archetypes (current — refreshed 2026-04-25)

| ID | Label |
|---|---|
| `mid-market-tpm` | Mid-Market TPM (Series B–D, IoT/hardware/wireless/B2B SaaS) |
| `enterprise-sales-engineer` | Enterprise SE / Solutions Architect (IoT, wireless, industrial SaaS) |
| `iot-solutions-architect` | IoT / Wireless Solutions Architect (technical pre-sales + delivery) |
| `revenue-ops-operator` | RevOps / BizOps Operator (Series B–D, Utah-friendly) |

> **Removed lanes (do NOT use):** `cox-style-tpm` → renamed `mid-market-tpm`;
> `titanx-style-pm` → quarantined as `out_of_band` (FAANG-flavored PM —
> pedigree-filtered); `global-eng-orchestrator` → folded into
> `iot-solutions-architect`; `revenue-ops-transformation` → renamed
> `revenue-ops-operator`. See `modes/_shared.md` for the canonical reference.

---

## Non-Negotiable Rules

| # | Rule |
|---|---|
| 1 | Never fabricate metrics — source of truth is `data/resumes/base.py` + `config/profile.yml` |
| 2 | Never write a resume without a target archetype — output is always lane-specific |
| 3 | Comp floor: **$160K base / $200K total** (refreshed 2026-04-25; Sean is at $99K and $160K is the realistic 60%+ jump). Lower roles hidden unless Sean overrides |
| 4 | Never auto-submit applications — `applied` transition requires explicit "yes" |
| 5 | Never commit `data/db/pipeline.db`, `data/resumes/generated/`, or `.env` |
| 6 | **No Anthropic API calls.** Coin runs inside Claude Code; LLM work is the host session |
| 7 | Truthfulness gates (per `modes/_shared.md` Operating Principle #3): never claim Cox/TitanX/Safeguard outcomes as direct employment (Hydrant engagements only); no "Fortune 500" / "seven-figure" / "world-class" without a verifiable named account; no CS/engineering degree (Sean has BA History + MBA WGU + PMP) |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Claude Code session (this one) — ALL LLM reasoning here      │
│   .claude/skills/coin/SKILL.md     ← modal router            │
│   modes/_shared.md                 ← framework + rubric      │
│   modes/{discover,score,tailor,track,status,url}.md          │
└──────────────────────────────────────────────────────────────┘
              ↓ invokes (Bash tool)
┌──────────────────────────────────────────────────────────────┐
│ Python I/O workers — no LLM calls                            │
│   careerops/scraper.py      LinkedIn guest API + Indeed      │
│   careerops/compensation.py comp parse + filter              │
│   careerops/score.py        pure-Python fit scoring          │
│   careerops/pipeline.py     SQLite + Rich dashboard          │
│   scripts/*.py              discover, print_role, save_resume, │
│                             update_role, fetch_jd, dashboard  │
└──────────────────────────────────────────────────────────────┘
              ↓ reads/writes
┌──────────────────────────────────────────────────────────────┐
│ State                                                        │
│   data/db/pipeline.db       SQLite — role tracking           │
│   data/resumes/base.py      canonical PROFILE dict           │
│   config/profile.yml        North Star pitches per archetype │
│   data/resumes/generated/   lane-tailored resume JSON output │
└──────────────────────────────────────────────────────────────┘
```

**State machine** (from santifer/career-ops, translated):

```
discovered → scored → resume_generated → applied →
  responded → contact → interviewing → offer
                                          ↳ rejected / withdrawn / closed
                                          ↳ no_apply (bail anytime)
```

---

## Architecture Constraints

- **Language:** Python 3.11+ (system venv at `.venv/`, built on Python 3.13)
- **Database:** SQLite at `data/db/pipeline.db` — no external DB deps
- **Scraping:** `httpx[http2]` + `BeautifulSoup4` — LinkedIn guest endpoint,
  Indeed best-effort (often Cloudflare-blocked)
- **Terminal output:** `rich` — Bloomberg-style cards
- **No ORM:** raw `sqlite3` — schema in `careerops/pipeline.py`
- **LLM integration:** NONE. All reasoning runs in the host Claude Code
  session. Do not add `anthropic` to requirements.
- **PDF generation:** `weasyprint` + `jinja2` — `scripts/render_pdf.py` reads
  a generated resume JSON and produces a print-ready PDF.

---

## Self-Verification

After writing or modifying code, ALWAYS run:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/python -c "from careerops import scraper, pipeline, compensation, score; print('imports OK')"
# Confirm no anthropic dependency:
.venv/bin/pip list | grep -i anthropic || echo "anthropic: absent ✓"
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
  .claude/
    skills/coin/SKILL.md    # modal router
    commands/coin.md        # /coin slash command
  careerops/                # Python I/O workers
    scraper.py              # LinkedIn guest API + Indeed best-effort
    compensation.py         # comp parse, filter, band label
    score.py                # pure-Python fit scoring
    pipeline.py             # SQLite CRUD + Rich dashboard
  modes/                    # Claude-executed markdown modes
    _shared.md              # rubric + framework (loaded by every mode)
    discover.md             # find + score new roles
    score.md                # fetch + parse JD for a role
    tailor.md               # generate lane-tailored resume JSON
    track.md                # state machine transitions
    status.md               # Rich dashboard
    url.md                  # ingest a single URL
  scripts/                  # CLI helpers (invoked from mode files)
    discover.py             # full scrape + score + upsert pass
    print_role.py           # DB row → JSON for Claude to read
    save_resume.py          # resume JSON → disk + state transition
    update_role.py          # status / fit / parsed_jd updates
    fetch_jd.py             # pull JD text for one role
    dashboard.py            # print pipeline dashboard
    liveness_check.py       # ping open roles; mark dead ones closed
    render_pdf.py           # resume JSON → print-ready PDF via weasyprint
  config/
    profile.yml             # North Star pitches (editable by Sean)
  config.py                 # Python constants + archetype keywords
  data/
    resumes/
      base.py               # canonical PROFILE dict
      generated/            # lane-tailored outputs (gitignored)
    db/pipeline.db          # application tracking (gitignored)
  docs/
    state/project-state.md
    roadmap.md
  requirements.txt
  .env.example
```

---

## External Services

| Service | Purpose | Constraint |
|---|---|---|
| LinkedIn (guest jobs API) | Primary role discovery | Public endpoint; no auth; 2s delay between requests |
| Indeed (HTML) | Secondary discovery | Cloudflare-protected; often degrades to 0 results — expected |
| Levels.fyi | Comp cross-reference (Phase 2) | Not yet wired |
| Glassdoor | Tertiary comp band (Phase 2) | Not yet wired |

---

## Contacts

Sean Ivins — sean@lifestory.co
