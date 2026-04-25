# Coin — Project State

## What Was Just Done (2026-04-25, Session 3)

### First end-to-end run on new machine ✅ COMPLETE

**Goal:** Set up Coin on new machine, fix bugs found during first live run, execute
full discover → score → tailor pipeline.

**Setup:**
- Created `.venv/` at `/Users/tealizard/Documents/lab/coin/`
- Installed all deps from `requirements.txt` — 20/20 tests pass
- Fixed stale path `/Users/sean/Documents/Handoffpack/...` → `/Users/tealizard/Documents/lab/coin/` in `SKILL.md` and `modes/_shared.md`

**Bug fixed — comp-blindness in score_fit:**
- `score_fit()` was reading `comp_min`/`comp_max` from the DB row only, ignoring the
  parsed JD. When the JD has `comp_explicit=True`, the real comp was silently dropped,
  collapsing every explicitly-priced role to score 55 (unverified penalty).
- Fix 1: `score.py` — fallback to `parsed_jd["comp_min"]` when DB row comp is null
  and `comp_explicit` is True.
- Fix 2: `pipeline.py` `update_jd_parsed()` — now also persists `comp_min`/`comp_max`
  to the DB row when `comp_explicit=True`, so subsequent calls don't need the fallback.

**Live discovery:** 32 roles across all 5 archetypes, all active in pipeline.

**First resume generated:**
- Role: Netflix "Technical Program Manager - Infrastructure Engineering"
- Comp: $420K–$630K (explicitly stated in JD)
- Fit score: 76.1 (was 58.1 before comp-blindness fix)
- Saved to `data/resumes/generated/0004_cox-style-tpm_2026-04-25.json`
- Status: `resume_generated`

---

## What Was Just Done (2026-04-24, Session 2)

### Alpha-Squad rearchitecture ✅ COMPLETE

**Goal:** Eliminate Anthropic API dependency so Coin runs entirely inside
Sean's Claude Code subscription. Borrow heavily from santifer/career-ops.

**New files:**
- `.claude/skills/coin/SKILL.md` — modal router
- `modes/_shared.md, discover.md, score.md, tailor.md, track.md, status.md, url.md`
- `config/profile.yml` — 5 Sean-grounded archetypes with North Star pitches
- `careerops/score.py` — pure-Python fit scoring (comp-first weighting)
- `scripts/discover.py, print_role.py, save_resume.py, update_role.py, fetch_jd.py, dashboard.py`

**Deleted files:**
- `careerops/analyzer.py` (logic moved to `modes/score.md`)
- `careerops/transformer.py` (logic moved to `modes/tailor.md`)

**Rewritten files:**
- `config.py` — 3 coarse lanes → 5 archetypes (cox-style-tpm, titanx-style-pm,
  enterprise-sales-engineer, revenue-ops-transformation, global-eng-orchestrator)
- `careerops/scraper.py` — now hits LinkedIn guest API (public, no auth);
  live results confirmed (10+ real roles scraped and scored)
- `careerops/pipeline.py` — extended state machine (11 states from santifer);
  added list_roles, update_fit_score, update_jd_raw; Rich dashboard with
  comp-trajectory header
- `requirements.txt` — removed `anthropic`; added `pyyaml`, `httpx[http2]`, `h2`
- `.env.example` — removed `ANTHROPIC_API_KEY`; added `COIN_MIN_TC`, `COIN_LOCATION`
- `CLAUDE.md` — rewrote for skill-host architecture
- `.claude/commands/coin.md` — now a thin router that invokes the skill
- `.claude/commands/coin-{apply,search,setup,track}.md` — deleted (superseded by modal `/coin`)

**Tests:** 6/6 passing.
**Live verification:** `scripts/discover.py --lane cox-style-tpm --limit 10`
returns 10 real LinkedIn postings with titles, companies, locations, and
heuristic fit scores 65–83.

---

## Next Session Agenda

1. **Submit the Netflix application.** Resume is generated. Sean reviews
   `data/resumes/generated/0004_cox-style-tpm_2026-04-25.json`, copies into
   his template, and applies. Then: `/coin track 4 applied`.
2. **Score + tailor the Netflix TPM 6 — Data Systems role (role 5)** — same
   company, different infra focus; $420K–$630K comp range expected.
3. **Add comp extraction to scraper** — currently `comp_min` is null for
   most roles because LinkedIn's card HTML rarely includes ranges. Consider
   cross-referencing Levels.fyi for high-signal companies (Netflix, Stripe,
   Meta, Airbnb).
4. **Phase 2 kickoff:** batch scoring for 50+ roles — port santifer's
   `claude -p` pattern or use `/coin discover --all-lanes --limit 20` in a
   loop and auto-score the top-10 by heuristic.

## Active Blockers

None. No API key needed.

---

## Roadmap

| Task | Description | Status |
|------|-------------|--------|
| S-1.1 | Scraper: LinkedIn + Indeed live results | ✅ Done (LinkedIn live; Indeed Cloudflare-degraded as expected) |
| S-1.2 | Analyzer: JD parsing via Claude | ✅ Done (moved to `modes/score.md` — session-native) |
| S-1.3 | Transformer: lane-aware resume rewriting | ✅ Done (moved to `modes/tailor.md`) |
| S-1.4 | Pipeline DB: CRUD + dashboard | ✅ Done (11-state machine + Rich dashboard) |
| S-1.5 | Compensation: Levels.fyi cross-reference | 🚧 Pending — Phase 2 |
| S-2.1 | Resume quality: PDF via weasyprint | 🔲 Backlog |
| S-2.2 | Glassdoor comp band scraping | 🔲 Backlog |
| S-2.3 | Full cover letter generation (beyond hook) | 🔲 Backlog |
| S-2.4 | Batch resumability per santifer (claude -p workers) | 🔲 Backlog |
| S-3.1 | Scheduler: daily auto-search cron | 🔲 Backlog |
| S-3.2 | Multi-board: Greenhouse / Lever / Workday | 🔲 Backlog |

---

## Resolved Bugs

- httpx http2 support required explicit `h2` package install — added to requirements.
- Scripts couldn't find `careerops` module when invoked from `scripts/` dir
  → added `sys.path` bootstrap to each script (parent dir goes on path).
- `careerops/__init__.py` imported deleted `analyzer`/`transformer` modules
  → updated to export only current modules.

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Eliminate `anthropic` SDK | Sean has a Claude Code subscription; per-token billing is redundant. All LLM reasoning happens in the host session. |
| Modal skill router (santifer pattern) | One `/coin` entry beats a dozen flat `/coin-*` commands. Detects URL / mode keyword and dispatches. |
| Keep SQLite; reject markdown-as-DB | Coin already has pipeline.db and needs SQL ("fit ≥ 80 in lane X ordered by comp"). santifer uses .md files, which are greppable but not queryable. |
| 5 archetypes derived from Sean's real experience | 3 lanes (previous) were too coarse; 6 (santifer-parity) was overkill. Each archetype maps to a real proof point. |
| Comp-first fit weighting (comp 0.40, skills 0.30, title 0.20, remote 0.10) | Per CRO verdict in alpha-squad: comp delta is axis #1, not #3. |
| LinkedIn guest endpoint over scraping logged-in HTML | `jobs-guest/jobs/api/seeMoreJobPostings/search` is public, predictable, returns clean HTML cards. No cookie management. |
| Indeed best-effort (expect Cloudflare) | Rather than pull in Selenium/FlareSolverr, we let Indeed fail gracefully and rely on LinkedIn. Revisit with a paid scraping API if volume demands it. |
