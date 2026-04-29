# Coin — Project State

## What Was Just Done (2026-04-28, eloquent-lichterman session — final pass)

### `www.handoffpack.com/lab/coin` is live, password-gated, end-to-end ✅ COMPLETE

**What changed:**
- Set `LAB_URL=https://lab-lifestoryco.vercel.app` on `handoffpack-www` Vercel production env (no repo file change for the env itself).
- One-line `next.config.js` edit in **`lifestoryco/handoffpack-www`** (commit `ae49fde`): added `/api/coin/:path*` to the rewrite list alongside the existing `/lab/*` rewrite. Without this, login POSTs hit handoffpack-www's marketing 404 and the cookie never reached the user-facing domain.
- Redeployed `handoffpack-www` to pick up the env var + new rewrite rule.

**Verified end-to-end against `https://www.handoffpack.com/lab/coin`:**
| Check | Result |
|---|---|
| Unauthed `/lab/coin` | 307 → `/lab/coin/login` |
| Wrong password | 401 |
| Correct password (`jobs`) | 200, `coin_auth` cookie set HttpOnly on `www.handoffpack.com` |
| Authed dashboard | 95 roles served from bundled DB snapshot |
| Authed page render | `<title>Coin — Career Ops</title>` |
| Mutation attempt | 503 read-only (correct contract) |
| `/lab/coy` sanity | unchanged, still served by handoffpack-www's static files |

**Active Blockers (current):**
- **The `coin_auth` cookie value IS the plaintext password.** Security review HIGH from earlier this session — brute-force on a 4-char `jobs` password is trivial. Rotate to a 16+ char random string before sharing the URL with anyone:
  ```
  cd web && vercel env rm COIN_WEB_PASSWORD production && vercel env add COIN_WEB_PASSWORD production
  # paste the new password (echo won't display)
  vercel --prod --yes
  ```
  Has to be done on `lab-lifestoryco` (the side that actually validates) — handoffpack-www does not check the password directly.
- **`COIN_NOTIFY_PHONE` still unset** + launchd job not yet installed. Scheduler shipped but inert.

**No new code in `lifestoryco/lab` this turn** — work was all in `handoffpack-www` plus Vercel env config.

---

## What Was Just Done (2026-04-28, eloquent-lichterman session — extended)

### Lab repo split + COIN UX hardening + 4-agent code-review pass ✅ COMPLETE

**Tests:** 380 → **381 passing** (+1: `test_dry_run_does_not_delete_failed_flag`).
**Commits added on top of the earlier 4-task batch:**
- `0c0bd66` — Revert botched merge of stale Coy work into main (only the
  authoritative copy in `handoffpack-www` should drive the live site)
- `2c80aac` — Two-repo boundary docs (`lab/CLAUDE.md`, `web/components/lab/coin/README.md`),
  dedicated `lab-lifestoryco` Vercel project, predeploy guard script
  refusing builds against the wrong project link
- `0409373` — COIN UX hardening + Vercel read-only deploy + 4-agent
  code-review remediations (22 files, +1022/-328)

**`/lab/coin` is now live and read-only at:** `https://lab-lifestoryco.vercel.app/lab/coin`
(password `jobs`, set on the lab-lifestoryco Vercel env). The
`handoffpack-www` Vercel env's `LAB_URL` is NOT set yet — flipping it on
will route `www.handoffpack.com/lab/*` (except `/lab/coy`) to this deploy
via the existing rewrite. That's a one-env-var change in the
handoffpack-www Vercel dashboard whenever you want to surface the lab
gallery on the marketing domain.

**Known limits of the deployed COIN dashboard:**
- Read-only: track / tailor / notes endpoints all return 503 with a
  "use the local Coin CLI" message. By design — Vercel can't run the
  Python `careerops.web_cli` subprocess and the bundled DB is immutable.
- DB freshness depends on snapshot refreshes. To pick up new local
  discover/track activity on prod: `cd web && npm run sync-coin-db`,
  commit, push. Auto-deploys via lab-lifestoryco.
- COIN_NOTIFY_PHONE for the launchd scheduler is still unset (this was
  flagged in the previous session and still needs Sean to do).

**New kanban columns from this session's UX work:**
- "Resume Builder" — drop a role here to enqueue a tailored resume build
  (writes marker file at `data/tailor_pending/<id>.txt`)
- "Not a Fit" — drop a role here to dismiss it (`no_apply` with note
  tagged `[user_dismissed:not_a_fit]`). The note tag is a parseable token
  so a future scoring iteration can mine the rejection corpus.

**Docs added you should read once:**
- `lab/CLAUDE.md` — the two-repo deployment map (`handoffpack-www` owns
  the marketing site + Coy; `lab` owns the dynamic lab projects via
  `LAB_URL` rewrite). Read this before any future deploy work.
- `lab/web/components/lab/coin/README.md` — the COIN web tier overview,
  including the read-only deploy contract and the gotchas (don't reintroduce
  `fileMustExist:true`; keep the `serverComponentsExternalPackages` entry).

---

## What Was Just Done (2026-04-28, eloquent-lichterman session — 4 tasks shipped)

### COIN-SCORE-V2, COIN-WEB-UI, COIN-EXPERIENCE-DEEPDIVE, COIN-SCHEDULER ✅ ALL COMPLETE

**Tests:** 310 → **380 passing** (+70 across the four tasks; 0 regressions). All four prompt files moved from `pending/` to `complete/`.

**Commits pushed to `lifestoryco/lab` main:**
- `1e4cfcc` — COIN-SCORE-V2: two-stage JD-aware scoring (m008 migration, score helpers, deep-score loop hooks)
- `73d88d5` — COIN-WEB-UI: Next.js dashboard at `/lab/coin` with password gate
- `f40a373` — COIN-EXPERIENCE-DEEPDIVE: STAR proof-point library + audit Check 5 hardening
- `0b494af` — COIN-SCHEDULER: launchd 7am daily discover + iMessage A-grade interrupt

### COIN-WEB-UI — live in production

- **URL:** https://www.handoffpack.com/lab/coin
- **Password:** `jobs` (set via `COIN_WEB_PASSWORD` Vercel env var on `handoffpack-www` project, production scope)
- **Architecture:** read path uses `better-sqlite3` against pipeline.db for SSR (zero-latency); mutate path spawns Python `careerops.web_cli` subprocess so Python remains source of truth for state-machine validation
- **Gate:** middleware redirects unauth `/lab/coin/*` → `/lab/coin/login`; cookie `coin_auth` set on successful POST `/api/coin/login`
- **Tabs:** Pipeline (kanban, framer-motion DnD), Discover, Roles, Network, Ofertas, Stories
- **Local dev:** `cd web && npm run dev` — `web/.env.local` already has `COIN_WEB_PASSWORD=jobs` (gitignored)

### COIN-SCHEDULER — code shipped, ⚠️ NOT INSTALLED YET

The launchd job is **not** loaded. Sean needs to run two things to activate it:

1. **Add phone number to `coin/.env`** (gitignored — not the .env.example):
   ```
   COIN_NOTIFY_PHONE=+18018033084
   ```
   (or whichever number is registered to iMessage on your Apple ID, E.164 format)

2. **Install + grant Automation permission:**
   ```
   /coin scheduler install
   /coin scheduler test
   ```
   The `test` invocation will trigger macOS's "allow your terminal to control Messages.app?" prompt. **Click Allow.** If you click Don't Allow, run `tccutil reset AppleEvents` and try `test` again.

After that the launchd job fires daily at 7am local time. Quiet by design — only roles graded A (composite ≥ 85) discovered in the last 24h get an iMessage. Failures write `data/.discover_failed.flag`; notify.py sends a single failure-alert iMessage.

### COIN-EXPERIENCE-DEEPDIVE — corpus seeded with 5 stories

`data/resumes/stories.yml` is committed with 5 STAR-format proof points migrated from PROFILE: Cox True Local Labs, TitanX Series A, Utah Broadband acquisition, ARR 6M→13M, global engineering orchestration. Run `/coin deep-dive` to walk role-by-role and grow the corpus — 30-min sessions, 3–5 new stories per position. Tailor now consults stories.yml first via `find_stories_for_skills` (skill overlap × grade × recency); audit Check 5 is hardened to FAIL on unattributed metrics.

### COIN-SCORE-V2 — two-stage scoring landed earlier this session

m008 migration adds `score_stage1`/`score_stage2`/`score_stage`/`jd_parsed_at`. `discover.py --deep-score N` (default 15) prepares a JD-fetched candidate set and writes `data/.deep_score_pending.json` with a `### DEEP-SCORE-PENDING` marker; `modes/discover.md` Step 4a is the host-session prompt that re-scores the top-N with full JD parsing + DQ.

### Sidequest fixed mid-session

The dev server was 404-ing `/lab/coin` for hours because the `.claude/launch.json` in this worktree was pointing `npm run dev` at a stale `objective-rosalind` worktree's `web/` (not the actual `lab/web/`). Fixed in both `.claude/launch.json` files (worktree + parent). Old `lab/web/.next.old/` rename remains as a benign artifact you can `rm -rf` whenever.

### Live verification

- `curl -sI https://www.handoffpack.com/lab/coin` → 307 → `/lab/coin/login` ✓
- `curl -L https://www.handoffpack.com/lab/coin` → 200 (login page renders) ✓
- Vercel deploy: `https://handoffpack-orou6cxy8-handoffpack.vercel.app` aliased to `www.handoffpack.com`

---

## What Was Just Done (2026-04-28, COIN-LEVELS-CROSSREF)

### COIN-LEVELS-CROSSREF — Comp imputation from Levels.fyi seed ✅ COMPLETE (Option-1 scope)

**Tests:** 293 → **310 passing** (+17; 0 regressions). Anthropic dep absent.

**Why:** LinkedIn-only roles arrived with `comp_source='unverified'`, hard-capped at score 55. For ~50 known-paying companies the penalty is unfair noise that pushes real opportunities below LinkedIn junk.

**Scope decision (with Sean, 2026-04-28):** ship the infrastructure with a small high-confidence seed (Datadog, Cloudflare, Vercel, Ramp — all sourced live from Levels.fyi component pages); mark the remaining 33 target companies `unknown: true` so the lookup function returns None honestly. Sean fills the rest quarterly via `/coin levels-refresh`. The acceptance criterion "≥30 of 40 Utah roles imputed" is deferred to that refresh — most Utah-anchored Filevine/Awardco/Weave/etc. have no usable Levels.fyi presence anyway.

**1. New seed `data/levels_seed.yml`** — 37 companies. 4 with verified component breakdowns (base + stock/yr × 4 = rsu_4yr_p50 + bonus). 33 marked `unknown: true` (some have no Levels presence at all; some have totals but no component breakdown). YAML header documents the "no spread → p25=p50=p75 point estimate" convention used when Levels gives only the median.

**2. New module `careerops/levels.py`:**
- `load_levels_seed()` — module-level cache; `_reset_cache()` exposed for tests
- `lookup_company(company)` — exact → suffix-stripped → one-direction substring (mirrors `score_company_tier`'s convention; `'Hash'` does NOT match `'HashiCorp'`). Returns None on miss or `unknown: true`
- `impute_comp(company, role_title)` — picks level from title hints (staff/principal/director/vp → 0.7 confidence) or company default (L5-first → 0.5). Walks down the fallback ladder if exact level missing (-0.1 per step, floor 0.3). Returns `{comp_min, comp_max, comp_source='imputed_levels', level_matched, confidence}` rounded to nearest $1K
- `get_seed_age(company)` and `flag_stale(threshold_days=90)` — for `/coin levels-refresh`

**3. Migration `m007_comp_confidence.py`** — adds `roles.comp_confidence REAL`. Idempotent + rollback (3.35 DROP COLUMN, pre-3.35 rebuild).

**4. `careerops/score.py::score_comp` extended:**
- New signature: `score_comp(comp_min, comp_max, comp_source=None, comp_confidence=None)`
- `imputed_levels` applies haircut `raw * (0.5 + 0.5 * confidence)`. Confidence 0.7 → 85% credit; 0.5 → 75%; 0.3 → 65%. Verified comp at the same band always scores higher than imputed
- `unverified` still hard-caps at 55 (regression-guarded by test)

**5. `careerops/pipeline.py::upsert_role` auto-impute hook** — after the row lands, if `comp_source='unverified'` AND the company is in the seed, an UPDATE patches `comp_min/comp_max/comp_source='imputed_levels'/comp_confidence` and appends `[imputed comp from Levels.fyi seed: <level> @ confidence <X>]` to `notes`. Idempotent on subsequent upserts (the row is no longer `unverified` so the hook skips). Verified live: a fake `unverified` Vercel SE role landed as `imputed_levels` with `$197K, 0.5 confidence`.

**6. `modes/levels-refresh.md`** — quarterly walk-through. Calls `flag_stale(90)`, surfaces each entry's source URL, asks Sean for new bands per level via `AskUserQuestion`, atomically updates the YAML. Documents the v2.1 manual approach; never auto-scrapes Levels.fyi.

**7. `modes/audit.md` Check 5** — added imputed-comp guard: any resume/cover-letter prose that references a comp range derived from `comp_source='imputed_levels'` flags CRITICAL. Same fabrication failure mode the 2026-04-24 review caught with Cox/TitanX inflation.

**8. SKILL.md routing** — `/coin levels-refresh` → `modes/levels-refresh.md`. Discovery menu updated.

**9. Tests in `tests/test_levels_crossref.py` (17 tests):**
- YAML structure validation
- `lookup_company` exact / lowercase / suffix-stripped / one-direction substring / unknown-flag / miss / malformed-entry edge cases
- `impute_comp` title-matched-staff / default-L5-on-Senior / unknown-company-returns-None
- `score_comp` haircut formula correctness, unverified hard-cap regression
- `upsert_role` auto-impute integration test (fresh DB, asserts `comp_source='imputed_levels'`, populated bands, notes audit trail)
- `get_seed_age` known/unknown
- `flag_stale` threshold filter

**Scope deferred to /coin levels-refresh:** populating component breakdowns for the remaining 33 stub companies. Sean owns this — it's a quarterly chore, not engineering work.

**Unblocks:** COIN-SCORE-V2 (final pre-condition cleared).

---

## What Was Just Done (2026-04-28, COIN-MULTI-BOARD)

### COIN-MULTI-BOARD — Greenhouse / Lever / Ashby scrapers ✅ COMPLETE

**Tests:** 265 → **293 passing** (+28; 0 regressions). Anthropic dep confirmed absent.

**Why:** Pre-task, every role in the DB was LinkedIn-only with `comp_source='unverified'`. The comp floor was being enforced against zero verified bands. Live smoke now produces 237 board roles across 7 companies with 100% verified comp on the top 10.

**1. New package `careerops/boards/`** — three public-API scrapers behind a shared ABC:
- `BoardScraper` (base): rate-limited GET (1.5s/instance), HTML strip, regex comp fallback (`COMP_REGEX`), normalized location handling, common `_to_role_dict` shape
- `GreenhouseBoard` — `boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`. Comp priority: structured `metadata` (e.g. Datadog's `currency_range`) → regex on rendered content → none
- `LeverBoard` — `api.lever.co/v0/postings/{slug}?mode=json`. Priority: structured `salaryRange.min/max` → regex on `descriptionPlain + additionalPlain`
- `AshbyBoard` — `api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true`. Priority: `compensationTier{minValue,maxValue}` → `compensationTiers[].components` → `compensationTierSummary` string parse → regex fallback. Highest-signal source overall
- All cite santifer/career-ops scan.mjs (MIT) in module docstrings

**2. `config.TARGET_COMPANIES` registry** — 32 companies, slugs verified live on 2026-04-28:
- Greenhouse (verified): lucidsoftware, weave, qualtrics, awardco, mastercontrol, recursionpharmaceuticals, vercel, datadog, cloudflare
- Lever (verified): spotify
- Ashby (verified): airbyte, hightouch, ramp, writer, linear
- 17 entries marked `# TODO verify` — Filevine, Pluralsight, Podium, Domo, Vivint, Spiff, Notion, RevenueCat, Block, Snowflake, MongoDB, Confluent, HashiCorp, dbt Labs, Census, Retool, Fivetran. None of the standard ATS slugs returned 200 — these companies likely use non-standard ATS endpoints (Workday, custom). Slug discovery deferred
- Adobe / Stripe / Anthropic / FAANG explicitly excluded — pedigree filter
- New env override: `COIN_BOARD_SCORE_FLOOR` (default 55) — title-score gate before a board role surfaces

**3. `careerops/scraper.py`** — orchestrator + dedup:
- New `search_boards(lane, location, boards, companies)` — ThreadPoolExecutor(max_workers=4) over `(company × board) tasks`. Each task swallows exceptions per-board so one failure doesn't kill the run
- New `_canonical_url(url)` — strips query/fragment/trailing slash, lowercases. Used to dedupe across LinkedIn ↔ board sources
- `search_all_lanes(...)` extended with `boards`/`companies` kwargs; default sources now `linkedin,greenhouse,lever,ashby`
- Location filter: substring match against role.location, with remote roles always passing (Sean is remote-friendly)

**4. `scripts/discover.py`** — two new flags (existing flags preserved):
- `--boards linkedin,greenhouse,lever,ashby` (default = all four). Drop a name to skip
- `--companies "Vercel,Datadog,Weave"` — limit board scrapes to a subset; ignored for LinkedIn

**5. `careerops/compensation.py`** — `filter_by_comp` now respects pre-populated `comp_min/comp_source` instead of overwriting them with `parse_comp_string(role['comp_raw'])` (LinkedIn-only field). Critical fix — without this, board scraper output collapsed to `unverified` on its way through `discover.py`

**6. `careerops/pipeline.py` + migration `m006_comp_currency.py`:**
- `roles.comp_currency TEXT DEFAULT 'USD'` column added; idempotent migration with rollback path (handles SQLite ≥3.35 DROP COLUMN and pre-3.35 rebuild)
- `upsert_role` accepts/persists `comp_currency`; `init_db` schema updated for fresh DBs
- `comp_source` enum (TEXT, no CHECK) accepts `explicit | parsed | imputed_levels | unverified` — no schema change needed; the four values flow through string storage

**7. Tests (28 new):**
- `tests/test_boards_greenhouse.py` (8) — fixture: `greenhouse_filevine.json`
- `tests/test_boards_lever.py` (8) — fixture: `lever_lucidsoftware.json`
- `tests/test_boards_ashby.py` (8) — fixture: `ashby_vercel.json`
- `tests/test_boards_orchestrator.py` (4) — lane-score floor, LinkedIn↔board dedup, per-board failure isolation, `companies` flag scope

**Live smoke (network):** `discover.py --boards greenhouse,lever,ashby --companies "Weave,Vercel,Airbyte,Spotify,Linear,Ramp,Writer"` → 237 roles (greenhouse 47, lever 92, ashby 98); top 10 all carry `comp_min`/`comp_max` with `comp_source` in {explicit, parsed}. Top: Ramp Senior Security PM ($160K-$259K, ashby explicit, 89.7 fit).

**Unblocks:** COIN-LEVELS-CROSSREF (next), then COIN-SCORE-V2.

---

## What Was Just Done (2026-04-27, Session 6 — COIN-DISQUALIFIERS)

### COIN-DISQUALIFIERS — JD-aware quarantine + soft-penalty layer ✅ COMPLETE

**Tests:** 239 → **265 passing** (+26; 0 regressions).

**1. New module `careerops/disqualifiers.py`** — pure-regex scanner. Public API:
- `scan_jd(jd_text, profile) -> DqResult` (hard_dq/soft_dq/matched_phrases)
- `apply_disqualifiers(role, parsed_jd, profile) -> DqResult` (mutating helper:
  sets `role['lane']='out_of_band'` + appends `DQ: <reasons>` to notes on hard hits)
- 3 hard rules: `clearance_required` (Secret/TS/SCI/Public Trust), `itar_restricted`
  (ITAR / 22 CFR 120/121 / export controlled), `degree_required` (BS/MS in CS/SE/EE/ME/
  Materials/Chem). Equivalence carve-out: "or equivalent" within 30 chars demotes degree
  match to no-DQ (Sean's 15yr experience qualifies)
- 2 soft rules: `msft_stack_mismatch` (-20, gated on profile.skills not containing
  Azure/D365/Power BI/etc), `narrow_security_domain` (-20, requires 3+ infosec mentions
  AND title contains security|cyber prefix)

**2. `careerops/score.py::score_breakdown`** — backward-compatible `dq_result` kwarg:
- `hard_dq` → composite=0, grade=F, `disqualified=True`, `dq_reasons=[...]`
- `soft_dq` → composite clamped[0,100] after penalty, `domain_fit` info dimension
  (weight=0, doesn't double-count), `dq_reasons=[...]`
- `dq_result=None` → byte-identical to prior output (no new keys; 239 existing tests untouched)

**3. `coin/config.py`** — `DISQUALIFIER_PATTERNS` and `DOMAIN_PENALTY_RULES` lists
mirror the regexes for hand-editability. disqualifiers.py remains source of truth.

**4. `modes/score.md` Step 4a + Step 5** — disqualifier scan inline before re-score,
hard-DQ stop with override hint, soft-DQ threading via `dq_result` kwarg.

**5. `modes/auto-pipeline.md` Step 2.1/2.2** — same insertion; quarantine stop message
extended to surface `dq_reasons` (was FAANG-only).

**6. `tests/test_disqualifiers.py` (26 tests)** — Rock West / HPE / JourneyTeam / Coda
verbatim JD fixtures, parametrized clearance + ITAR variants, equivalence-clause carve-out,
msft skill-presence gate, security-title-+-frequency dual gate, score_breakdown DQ
integration (hard zero, soft penalty, no-DQ identity, domain_fit weight=0).

**Files touched (5):** `careerops/disqualifiers.py` (new), `careerops/score.py`,
`config.py`, `modes/score.md`, `modes/auto-pipeline.md`, `tests/test_disqualifiers.py` (new).

**Decisions:**
- Pure regex, no LLM. Deterministic by design — must be cheap to call on every JD parse.
- Hard-DQ short-circuits BEFORE the existing `lane='out_of_band'` quarantine guard so
  the new `dq_reasons` field is populated when DQ caused the quarantine (vs. FAANG-pedigree
  filter which doesn't carry reasons).
- `domain_fit` dimension carries weight=0 — penalty already hit composite; the dimension
  exists purely so the future dashboard can render "soft-penalized -20" without rebuilding
  the math from dq_reasons.

---

## What Was Just Done (2026-04-27, Session 6 — Coin v2 program kickoff)

### Authored 7 v2 task prompts + executed 1 (COIN-SCRAPER-POSTED-AT) ✅

**Session goal:** Plan and kick off the Coin v2 program (Sean: $99K → $160K+).
Today's `/coin discover --utah` exposed structural gaps — JD-blind scoring,
LinkedIn-only sourcing, no posting freshness, no UI beyond Rich CLI, thin
story library. Locked plan via AskUserQuestion (7 forking questions answered),
then authored 8 self-contained task prompts and executed the first one.

**Plan file:** `~/.claude/plans/great-work-yes-please-polymorphic-hollerith.md`
(approved by Sean — context, vision, 8 workstreams, 4-sprint sequence).

**Authored prompts** (all in `docs/tasks/prompts/pending/`, ~3.3K lines total):
- `COIN-DISQUALIFIERS` (S) — JD-aware quarantine: clearance/ITAR/CS-deg hard
  DQ, MSFT-stack/narrow-domain-SE soft -20pt penalty. Catches the
  #4/#9/#13/#14 false positives Sean flagged today.
- `COIN-MULTI-BOARD` (M) — Greenhouse/Lever/Ashby scrapers (port santifer
  scan.mjs MIT). Solves "all comp unverified" — Ashby exposes comp directly.
- `COIN-LEVELS-CROSSREF` (M) — Manual Levels.fyi seed (~50 cos), comp
  imputation with confidence haircut. Auto-runs during upsert.
- `COIN-SCORE-V2` (L) — 2-stage discovery: stage 1 cheap title-only,
  stage 2 host-Claude-session JD parse + DQ scan + re-score top-N.
- `COIN-WEB-UI` (L) — `/lab/coin` Next.js page in existing `web/` app.
  Mirrors `/lab/holo` pattern (better-sqlite3 reads, Python subprocess
  mutations). Kanban + role detail + ofertas + stories views.
- `COIN-EXPERIENCE-DEEPDIVE` (M) — Conversational interview mode.
  Expands `data/resumes/base.py`'s ~5 stories to 30-50 in `stories.yml`.
  Hardens audit Check 5 (metric provenance must trace to story id).
- `COIN-SCHEDULER` (S) — launchd 7am daily discover + iMessage on A-grade
  (≥85). Quiet by design. Requires SCORE-V2 first (A-grade trustworthy).

**Executed prompts:**
- `COIN-SCRAPER-POSTED-AT` — see detailed entry below.

**Decisions locked via AskUserQuestion:**
- UI surface → `/lab/coin` in existing `web/` (mirror `/lab/holo`)
- Score V2 → LLM-augmented JD parsing (host session, not Anthropic SDK)
- Comp data → Multi-board direct (Greenhouse/Lever/Ashby)
- Deep-dive format → Conversational interview, Coin transcribes
- Disqualifiers → Hard for clearance/ITAR/CS-deg; soft for MSFT-stack +
  narrow-domain SE. Sean is a US citizen (citizenship is NOT a DQ).
- Scheduler → Daily launchd at 7am + iMessage on A-grade only
- Privacy/NDA → None — `base.py` is fair game

**Repos audited for borrowable code:**
- `santifer/career-ops` (MIT) — port `scan.mjs` API-detection switch +
  pipeline tab taxonomy. Direct port-source for COIN-MULTI-BOARD + WEB-UI.
- `drbarzaga/JobPortal` — archived MERN job-board product, wrong shape. Skip.
- `doreanbyte/katswiri` (Unlicense) — Dart/Flutter, Malawi job boards.
  Useful only as `BoardScraper` ABC pattern reference.

**Sequencing for next sessions:**
- Sprint 1: COIN-DISQUALIFIERS, COIN-MULTI-BOARD, COIN-LEVELS-CROSSREF
  (sequential — they all touch `score.py`, `pipeline.py`, `config.py`)
- Sprint 2: COIN-SCORE-V2 (depends on Sprint 1)
- Sprint 3: COIN-WEB-UI + COIN-EXPERIENCE-DEEPDIVE (parallel, both after Sprint 2)
- Sprint 4: COIN-SCHEDULER (after SCORE-V2)

Estimated remaining execution: 12-15 hours across 3-4 sessions. Prompts
are the leverage — once written, `/run-task` walks each one autonomously.

---

## What Was Just Done (2026-04-27, COIN-SCRAPER-POSTED-AT)

### Capture posting age and surface freshness ✅ COMPLETE

**Tests:** 223 → **239 passing** (+16; 0 regressions).

**Motivating example:** Sean flagged role #11 (Filevine) — a posting that
LinkedIn was still showing but had actually been live ~30 days. Coin's
`discovered_at` only records when the scraper first saw the role, so
month-old reqs masquerade as fresh in the dashboard. Stale reqs rarely
convert (the recruiter screen window is 5–14d), so tailoring effort
spent on them is wasted throughput.

**What shipped:**
- `scripts/migrations/m005_posted_at.py` — `roles.posted_at TEXT` column,
  idempotent, supports `--rollback` (uses `ALTER TABLE ... DROP COLUMN`
  on SQLite ≥3.35, falls back to table rebuild otherwise).
- `careerops/scraper.py::_extract_posted_at` — pulls posted_at off LinkedIn
  cards, preferring the machine-readable `datetime` attribute and
  falling back to a `RELATIVE_AGE_RE` regex against the human string.
- `careerops/pipeline.py::upsert_role` — persists `posted_at` with
  `COALESCE(excluded.posted_at, roles.posted_at)` so a future scrape
  that misses the element never clobbers a known date.
- `careerops/score.py::score_freshness` — new dimension wired into
  `score_breakdown`. Buckets: ≤7d=100, ≤14d=80, ≤30d=60, ≤90d=30,
  >90d=10, unknown=50.
- `config.FIT_SCORE_WEIGHTS` rebalanced (sum still 1.0):
  `freshness 0.04` added; `application_effort 0.04 → 0.02`,
  `culture_fit 0.03 → 0.01`.
- `scripts/discover.py --max-age-days N` — drops roles older than N days
  before scoring/upserting; reports `dropped X of Y` to stderr. Verified
  live: dropped 10 of 20 roles older than 14 days.
- `scripts/dashboard.py` — new "Age" column (between Lane and Company),
  rendered via `pipeline.format_age` (`3d` / `1w` / `5mo` / `1y+` / `?`).

## What Was Just Done (2026-04-25, Session 5 — Deferred-followup batch 2)

### COIN-NETWORK-LIVE-SCRAPE + COIN-OFERTAS-LEVELS-FYI + COIN-COVER-RECIPIENT-FROM-NETWORK ✅ COMPLETE

**Tests:** 193 → **223 passing** (+30; 0 regressions). Verdict: PASS.

**1. COIN-NETWORK-LIVE-SCRAPE** — wire the LinkedIn search-page fallback
- `careerops/network_scrape.py` — `parse_linkedin_people_search(html, target_company)` (BeautifulSoup parser tolerant of LinkedIn's class-name churn, dedupes by URL, strips connection-degree suffixes "• 2nd", normalizes relative `/in/<slug>` to absolute https) + `upsert_scraped(rows, db_path)` (parameterized UPSERT with COALESCE preserving more-specific company strings from prior CSV imports)
- `tests/fixtures/network/sample_search_page.html` — 5-card fixture covering valid cards, malformed cards (no profile URL, parser must skip), duplicate URLs (parser must dedupe), relative-vs-absolute href forms, connection-degree suffix stripping
- `tests/test_network_scrape.py` (10 tests) — parser unit tests + upsert idempotency + the COALESCE-preserves-export-company contract test
- `modes/network-scan.md` Step 3 rewritten: explicit browser MCP invocation (`Claude_in_Chrome` preferred, `Claude_Preview` fallback), HTML capture to `/tmp/linkedin_search.html` (not into project tree because LinkedIn HTML carries incidental sidebar PII), `parse_linkedin_people_search` → `upsert_scraped` pipeline, graceful degradation when LinkedIn re-skins the search HTML
- No live LinkedIn auth scripted from Python (Sean's browser session belongs to him; Coin only consumes the rendered HTML he can already see)

**2. COIN-OFERTAS-LEVELS-FYI** — market-comp anchor when only one real offer exists
- `careerops.pipeline.insert_market_anchor(company, title, base_salary, *, rsu_total_value=0, ...)` — wraps `insert_offer` with `status='market_anchor'` so synthetic comps stay out of `list_offers(status='active')` (the Y1-best ranking in ofertas Step 3 stays clean) but join the comparison via `combined = list_offers(active) + list_market_anchors()`
- `careerops.pipeline.list_market_anchors()`
- `tests/test_market_anchor.py` (4 tests) — happy path, status segregation from active offers, required-field validation, combined-list pattern
- `modes/ofertas.md` adds Step 5.5 — when 1 active offer + 0 anchors, prompt Sean to look up the same role/level on Levels.fyi and capture the P50 base + RSU + bonus; counter-brief then cites "Levels.fyi P50 for &lt;company&gt; &lt;title&gt;" instead of bluffing a competing offer. Skip path emits a soft counter ("Below market based on independent research") that still refuses to fabricate

**3. COIN-COVER-RECIPIENT-FROM-NETWORK** — cover-letter recipient_name auto-population
- `scripts/migrations/m004_outreach_role_tag.py` — adds `outreach.contact_role TEXT` + `outreach.target_role_id INTEGER` + `idx_outreach_contact_role`. Idempotent (PRAGMA-checked column adds, applied flag in schema_migrations). Self-bootstraps m003 inline if applied to a fresh DB
- `careerops.pipeline.tag_outreach_role(outreach_id, contact_role, target_role_id=None)` — validates against `VALID_CONTACT_ROLES = ('hiring_manager', 'team_member', 'recruiter', 'exec_sponsor', 'alumni_intro')`
- `careerops.pipeline.find_hiring_manager_for_role(role_id)` — joins `outreach × connections` filtered to `contact_role='hiring_manager'`; checks both `role_id` and `target_role_id` columns so the same contact can be tagged for a different role; returns most-recently-drafted match; tolerates missing tables / missing column on fresh DBs (returns None instead of raising)
- `tests/test_hiring_manager_lookup.py` (11 tests) — m004 schema + idempotency + m003-bootstrap, tag validation, recursive lookup paths, ignores non-hiring-manager tags, picks most-recent on multi-tag, missing-schema graceful return, target_role_id branch
- `modes/network-scan.md` Step 6.5 — optional hiring-manager tagging prompt after the brief; instructs the agent to call `tag_outreach_role` with the right enum value; documents all 5 valid contact roles
- `modes/cover-letter.md` Step 1 — auto-lookup via `find_hiring_manager_for_role(<role_id>)`; `recipient_name = hm['full_name']` when present, null when not; explicit refusal to invent a hiring manager
- `modes/_shared.md` adds a new "Cross-mode helpers" section enumerating all the helpers + valid `contact_role` values (so future modes don't grep around)

**Schema migrations applied to live DB:** m003 (already), m004 (this session). 002 + 003 + 004 all tracked in `schema_migrations`.

**New tests (30):**
- `test_network_scrape.py` (10): parser dedupe, malformed-card skip, URL normalization, tracking-param strip, target_company propagation, seniority classification, empty-HTML handling, fresh-DB schema bootstrap, upsert idempotency, COALESCE preserves CSV-export company over scraper target
- `test_market_anchor.py` (4): happy path, status segregation, required-field validation, combined-list pattern
- `test_hiring_manager_lookup.py` (11): m004 schema/idempotency/bootstrap, tag validation, lookup paths
- `test_cover_letter_mode.py` extended (1): recipient_name lookup documented + anti-fabrication guard
- `test_network_scan_mode.py` extended (2): live-scrape pipeline documented + hiring-manager tagging documented with all 5 valid roles
- `test_ofertas_mode.py` extended (2): Step 5.5 documented + market-anchor truthfulness gate

**Files touched:** 13 (4 mode .md, _shared.md, 1 new careerops module, 1 pipeline.py extension, 1 new migration, 1 new HTML fixture, 4 new test files + 3 extended test files, this state doc).

**Decisions:**
- Live-scrape stays parser-only (no Python-driven LinkedIn auth) — keeps Sean's session uncompromised and avoids TOS exposure on auth-script paths.
- Market anchors live in the same `offers` table with `status='market_anchor'` instead of a separate table — same math (`year_one_tc`, `three_year_tc`) applies, ofertas comparison code stays trivial.
- Hiring-manager tagging on `outreach` rather than a new table — `outreach` already has the role↔connection link; one column add is cleaner than a junction table.

---

## What Was Just Done (2026-04-25, Session 5 — Code-review --fix EVERYTHING)

### All review findings resolved (CRITICAL → HIGH → MEDIUM → LOW + pre-existing) ✅ COMPLETE

**Tests:** 170 → **193 passing** (23 net new, 0 regressions). Verdict: PASS.

**HIGH (6) — all fixed:**
- `import_linkedin_connections.py` rows_inserted/rows_updated counter — replaced ON-CONFLICT-rowcount-hack with explicit pre-SELECT existence check; per-row insert/update accounting now accurate (test: `test_inserted_vs_updated_counts_are_accurate`)
- `offer_math.py` STATE_TAX_RATES + ANNUAL_BASE_BUMP + DEFAULT_VEST_SCHEDULE moved to `config.py`; offer_math now imports them
- `import_linkedin_connections.py` DEFAULT_CSV reads `config.LINKEDIN_CONNECTIONS_CSV`
- `cover-letter.md` Greenhouse field 5 → 6 (was wrong; field 5 is Resume); Lever 7 → 10 (was wrong; field 7 is Current company)
- `network-scan.md` `/coin track-outreach` reference now backed by a real `scripts/track_outreach.py` helper (8 tests in `test_track_outreach.py`); SKILL.md routes `track-outreach <id> sent|replied [--note]` and `track-outreach --list`

**MEDIUM (9) — all fixed:**
- `three_year_tc` Y2/Y3 RSU growth exponents: was `**2` / `**3` (one year too many on each); now `**1` / `**2` so Y2 vest sits 1 year past grant FMV and Y3 sits 2 years past. Test `test_three_year_tc_y3_growth_uses_squared_exponent` locks in the math (Y3 @ +10% = 25k × 1.21 = 30,250 exactly)
- `vest_curve` ZeroDivisionError when `rsu_vest_years=0` — `_safe_vest_years` helper coerces to default 4. Test `test_zero_vest_years_does_not_crash`
- `connections` + `outreach` schema now in `scripts/migrations/m003_connections_outreach.py`; importer keeps `ensure_schema()` for fresh-DB compat. 3 tests in `test_migrations_m003.py`
- Migrations renamed: `001_archetypes_5_to_4.py` → `m001_…`, `002_offers_table.py` → `m002_…`, plus new `m003_…`. All importable as Python modules now. Test loader updated.
- `render_pdf.py` + `render_cover_letter.py` `base_url` anchored to `ROOT` (script's project) instead of `Path.cwd()` — invariant under shell cwd, fixes a parity defect that was pre-existing in `render_pdf.py` since session 3
- `render_cover_letter.py` `--out` and `--input` constrained to `data/resumes/generated/` via `_validate_under_generated`; refuses path traversal
- `onboarding.md` question-count: header / steps / summary now consistently say 7 (was 9 / 7 / 8); SKILL.md Onboarding section follows. Test `test_question_count_consistent`
- SKILL.md Discovery menu adds `/coin setup` and `/coin track-outreach <id>`
- `import_linkedin_connections.py::import_csv` now mkdir-s the DB parent inside the function (not just in `main()`) — works when called from tests / non-CLI

**LOW (13) — all fixed:**
- `render_cover_letter.py` defers Jinja2 + WeasyPrint imports into `_build_env()` / `render()` so the no-op CLI path is fast; prints `Selected cover JSON: <path>` so Sean sees which lane was picked
- `pipeline.insert_offer` raises `ValueError` listing missing required keys instead of low-context `IntegrityError`. Bonus fix discovered: also stops emitting NULL for unset columns so DDL DEFAULTs (status='active', signing_bonus=0, etc.) actually apply. Test `test_insert_offer_writes_row` + `test_insert_offer_missing_required_raises`
- `vest_curve` strips per-element whitespace ("25 / 25 / 25 / 25" parses identically to "25/25/25/25"). Test `test_whitespace_in_schedule_parses`
- `delta_table` returns a proper `TypedDict(DeltaRow)` shape. Test `test_delta_table_returns_typed_dict_shape`
- `m002_offers_table.main()` consolidated through `apply()` so connection lifecycle is guarded by try/finally on every path
- `import_linkedin_connections.py::main` validates `--db` is under `data/db/` (rejects writes outside the project)
- `network-scan.md` Step 2 + Step 7 SQL examples gain "NEVER f-string into SQL" comments + use parameterized `?` bindings explicitly
- `network-scan.md` Step 5 clarifies that `seniority='recruiter'` is a *scan-time* concept — the import classifier emits leadership/senior_ic/peer only; recruiter override is title-pattern matching at scan time
- `network-scan.md` refusal table gains: "Citing a metric not in PROFILE.positions in any draft DM" — parity with cover-letter.md
- `onboarding.md` raw resume now staged via `tempfile.mkstemp` and unlinked after Step 9 success (PII off disk once profile is written)
- `onboarding.md` Step 7 surfaces $160K/$200K Sean default + warns on lower fat-finger
- `cover-letter.md` audit subset now uses audit.md's exact check labels (Check 1 Education / 2 Pedigree / 3 Cox attribution / 4 Vague-flex / 5 Metric provenance) — drops the "verb authenticity" mismatch that wasn't a numbered check
- `ofertas.md` adds explicit Step 0 "Load the AskUserQuestion tool" (mirrors onboarding); Step 2 references the load instead of conditional
- `auto-pipeline.md` lane list now reads from `config.LANES.keys()` instead of hardcoded literal; `update_lane()` and `update_role_notes()` helpers are now invoked instead of raw SQL (TODOs were stale — helpers exist)
- `cover_letter_template.html` recipient block: `{% if recipient_name %}{{ recipient_name }}{% else %}Hiring Team — {{ company }}{% endif %}` (was double-printing both)
- `config.py` adds `ONBOARDING_MARKER`, `ONBOARDING_DIR`, `ONBOARDING_RAW_RESUME`, `LINKEDIN_CONNECTIONS_CSV`, `NETWORK_DATA_DIR` constants — all path duplications now route through one source

**PRE-EXISTING (2) — also fixed:**
- `CLAUDE.md` refreshed: 5 archetypes → 4 (with Removed-lanes note); comp floor `$180K base / $250K total` → `$160K base / $200K total`; new Rule #7 codifies the truthfulness gates from `_shared.md` Operating Principle #3; date stamp 2026-04-24 → 2026-04-25
- `render_pdf.py` `base_url` defect (cwd-dependent) fixed at the same time as `render_cover_letter.py` for parity

**New tests added (23):**
- `test_track_outreach.py` (8): update sent/replied paths, note attachment, invalid action, unknown id, list_open semantics, role filter, missing-table error
- `test_migrations_m003.py` (3): tables created, idempotency, indexes
- `test_pipeline_offers.py` (3): insert_offer happy path, missing-keys ValueError, list_offers default-active filter
- `test_offer_math.py` extended (5): Y3 growth squared exponent locked in, STATE_TAX_RATES from config, zero-vest crash guard, whitespace parsing, TypedDict shape
- `test_import_linkedin_connections.py` extended (3): accurate inserted/updated split on re-import, parent-dir mkdir, DEFAULT_CSV from config
- `test_cover_letter_mode.py` updated (1): audit subset uses audit.md's actual check labels
- `test_ofertas_mode.py` updated (no count change): m002 import via package path, not file path

**Files touched:** 26 (4 mode files, SKILL.md, CLAUDE.md, 4 careerops/scripts files, 3 migration files, 1 template, 13 test files including 3 new). One commit per logical group below.

---

## What Was Just Done (2026-04-25, Session 5 — Follow-up batch)

### All four deferred follow-ups landed in one session ✅ COMPLETE

**Tests:** 98 → **170 passing** (72 net new, 0 regressions).

**1. COIN-OFERTAS — multi-offer comparison + negotiation brief** (santifer port)
- `modes/ofertas.md` (7-step decision-support flow with 5 hard refusals;
  "Coin does NOT recommend a specific offer" — surfaces math + trade-offs only)
- `careerops/offer_math.py` — pure functions: `vest_share_y1`, `vest_curve`,
  `year_one_tc`, `three_year_tc` with ±growth sensitivity, `historical_hit_rate`,
  `state_tax_rate` (top-marginal approximation), `delta_table`
- `scripts/migrations/002_offers_table.py` (idempotent, tracked)
- `careerops.pipeline.insert_offer` + `list_offers` helpers
- 24 new tests (offer math + mode structure + migration smoke)

**2. COIN-COVER-LETTER — separate cover letter generation** (proficiently port)
- `modes/cover-letter.md` (7-step flow; 280-word hard cap; story-parity +
  JD-keyword-parity checks against tailored resume; reuses audit checks 1-5
  for truthfulness — skips orthogonality/lane checks; 7 hard refusals)
- `scripts/render_cover_letter.py` — refuses on `audit_passes != true`,
  Jinja autoescape on, base_url scoped to `data/` (security parity with
  render_pdf.py)
- `data/cover_letter_template.html` (single-page Letter, Georgia serif)
- `config.COVER_TEMPLATE_PATH`
- Auto-pipeline integration (Step 6): cover-letter is additive — resume
  still ships if cover audit fails
- Apply mode integration: Greenhouse field 6 + Lever field 10 wire the
  cover artifact (cover.pdf for upload, paragraphs.hook for textarea)
- 13 new tests

**3. COIN-NETWORK-SCAN — LinkedIn warm-intro discovery** (proficiently port)
- `modes/network-scan.md` (7-step discovery+drafting flow; 6 hard refusals;
  warmth = 40% recency + 35% seniority + 25% relevance; recruiter override
  scores 90; truthfulness gate via `_shared.md` Operating Principle #3)
- `.claude/skills/coin/references/network-patterns.md` — CSV schema,
  recency tiers, seniority classifier, relevance signals, 4 outreach
  templates by recency tier (hot/warm/cold/recruiter), forbidden behaviors
- `scripts/import_linkedin_connections.py` — idempotent CSV ingest from
  LinkedIn's "Get a copy of your data" export; creates `connections` +
  `outreach` tables; company normalization collapses Inc./LLC/punctuation
  variants; preamble-tolerant CSV reader for LinkedIn's variable header
- 17 new tests (mode structure + reference content + schema + idempotency
  + company normalization + dry-run)
- Coin does NOT auto-send DMs and does NOT scrape with logged-in cookies

**4. COIN-ONBOARDING-EXECUTABLE — convert SKILL.md prose to executable mode**
  (job-scout pattern)
- `modes/onboarding.md` (9 deterministic AskUserQuestion blocks; Step 0
  loads AskUserQuestion via ToolSearch; Step 1 safety gate for existing
  profile with Re-onboard / Update specific fields / Cancel branches;
  Step 8 pedigree-constraint question explicitly load-bearing; Step 9
  atomic write via staging file + yaml.safe_load round-trip; identity
  slice only — never touches positions/education/skills_grid)
- SKILL.md: deleted the 9-step prose Onboarding section; replaced with
  pointer at modes/onboarding.md; routing table adds
  `setup`/`onboard`/`re-onboard`; First-Run Setup Checklist now dispatches
  onboarding between init-DB and smoke-test
- 18 new tests including SKILL.md regression (deleted prose markers must
  not reappear; First-Run Checklist must dispatch onboarding)
- 5 hard refusals (no silent overwrite, no inferred pedigree, identity-slice
  only, no question-skipping, no >5 smoke discovery)

**Cross-cutting infrastructure:**
- `.gitignore`: added `data/network/`, `data/onboarding/`
- `_shared.md` mode catalog: 4 new rows (ofertas, cover-letter,
  network-scan, onboarding)
- SKILL.md: 4 new routing entries + 3 new Discovery menu lines
- `scripts/migrations/__init__.py` for importable migration package

**Open follow-ups (after this batch — none from the original four):**
- ~~COIN-NETWORK-LIVE-SCRAPE~~ ✅ landed in Session 5 batch 2
- ~~COIN-OFERTAS-LEVELS-FYI~~ ✅ landed in Session 5 batch 2
- ~~COIN-COVER-RECIPIENT-FROM-NETWORK~~ ✅ landed in Session 5 batch 2

---

## What Was Just Done (2026-04-25, Session 4 — Part 5)

### /code-review --fix pass: ALL severities resolved ✅ COMPLETE

**Tests:** 98/98 pass (up from 83/91; 7 net new tests, 8 stale assertions corrected, 0 regressions).

**Group A — Audit hardening (modes/audit.md):**
- Check 3: positive-test rule (Cox/TitanX/Safeguard MUST contain Hydrant framing) + verb list expanded (ran/headed/spearheaded/architected/championed)
- Check 4 escalated WARN→CRITICAL; trigger list +12 phrases (NASDAQ:, hypergrowth, mission-critical, multi-billion, etc.)
- Check 5 broadened: numeric + spelled-out + collective-noun + team-shape + tenure all require source
- Check 7 removed mid-market-tpm exemption — target_role now required for every lane
- Orthogonality "trumps" rules added per check

**Group B — Tailor mode aligned (modes/tailor.md):**
- 5 → 4 archetypes
- target_role required (with per-lane table)
- Self-audit step 7 added
- Audit-aware writing rules section (7 rules tracking the 9 checks)

**Group C — 3 phantom modes built:**
- modes/followup.md (cadence tracker, 7d/14d/21d windows)
- modes/patterns.md (rejection cluster analysis with lane×tier×grade pivot)
- modes/interview-prep.md (round-aware brief: recruiter/HM/technical/panel/final)

**Group D — commands/coin.md regenerated** (4 archetypes, 16 modes, current routing).

**Group E — Render hardening (scripts/render_pdf.py + config.py):**
- Jinja2 `Environment(autoescape=select_autoescape(['html']))` replaces raw `Template()`
- WeasyPrint `base_url` scoped to `data/` (was `cwd` → file:// could read .env)
- RECRUITER_TEMPLATE_PATH moved to config.py
- Dead branch in out_path collapsed to single line
- Wrapped-JSON missing key now raises (was silent fallback)
- target_role wired through template; recruiter HTML uses `header_role or profile.title`

**Group F — Scoring fixes (careerops/score.py + careerops/pipeline.py):**
- score_breakdown: early-return composite=0/grade=F when lane='out_of_band' OR lane not in LANES (kills resurrection bug part 1)
- upsert_role: ON CONFLICT now uses CASE WHEN roles.lane='out_of_band' THEN 0 (kills resurrection bug part 2)
- score_company_tier: bidirectional substring → one-direction word-boundary match
- Added update_lane(), update_role_notes() helpers
- Stale weights docstring updated

**Group G — test_score.py inversion alignment:**
- 8 stale assertions rewritten (FAANG=100 → FAANG=25, default=45 → default=65)
- 4 new defensive tests added (out_of_band quarantine, unknown lane treated as quarantine, FAANG-LOWER-than-unknown inversion proof, substring safety)
- All 44 score tests pass

**Group H — Hygiene:**
- .env.example floors updated 180K/250K → 160K/200K
- target_locations dropped from base.py PROFILE; profile.yml is canonical (new get_target_locations() helper)
- scripts/migrations/001_archetypes_5_to_4.py: idempotent, tracked in schema_migrations table, applied successfully

**Group I — Audit fixture isolated:**
- tests/fixtures/audit/0137_filevine_se_known_bad.json (frozen copy)
- /coin pdf 137 in dev no longer overwrites the regression baseline

**Group J — Auto-pipeline hardened:**
- LinkedIn search-URL detection (rejects /jobs/search?keywords=... before wasting fetch_jd)
- Per-ATS URL pattern table for the URL ingest step
- Audit-fix oscillation diagnostic (detects ping-pong between competing checks; never runs 3rd iteration)

**Group K — Operating infrastructure:**
- .claude/settings.json with 30+ permission allowlist entries (Python venv calls, sqlite3 reads, git read-only, common file ops) + 8 deny rules (rm -rf, force-push, hard-reset, curl|sh)
- Removed unused agents: frontend-engineer.md, devops-engineer.md (Python+SQLite stack)
- Adapted db-architect.md from Postgres+RLS to SQLite + quarantine-aware
- New python-engineer.md agent (coin-stack-specific)

**Open follow-ups (deferred, low priority):**
- ~~COIN-NETWORK-SCAN~~ ✅ landed in Session 5
- ~~COIN-OFERTAS~~ ✅ landed in Session 5
- ~~COIN-COVER-LETTER~~ ✅ landed in Session 5
- ~~COIN-AUTO-PIPELINE-EXECUTABLE / COIN-ONBOARDING-EXECUTABLE~~ ✅ landed in Session 5

---

## What Was Just Done (2026-04-25, Session 4 — Part 4)

### Mode build-out + _shared.md refresh ✅ COMPLETE

**3 task prompts authored, executed, and shipped:**
- `COIN-AUDIT` → `modes/audit.md` (159 lines, 9 truthfulness checks) + `tests/test_audit_mode.py` (10 passing)
- `COIN-AUTOPIPELINE` → `modes/auto-pipeline.md` (200+ lines, 8 strict steps) + `tests/test_auto_pipeline.py` (14 passing)
- `COIN-APPLY` → `modes/apply.md` (200+ lines, 6 hard refusals) + `tests/test_apply_mode.py` (19 passing)

**modes/_shared.md refreshed:**
- 5 archetypes → 4 (current truth)
- Comp floor $180K/$250K → $160K/$200K
- Company tier scoring documented as INVERTED (FAANG penalized for Sean)
- Truthfulness gates promoted from implicit to explicit Operating Principle #3
- Out-of-band quarantine + the known resurrection bug documented
- Mode catalog cross-references all 9 active modes
- Open-follow-ups list captures: SCORE-TESTS, QUARANTINE-RESURRECTION, PIPELINE-HELPERS, TAILOR-FORCE, EMAIL-CANONICAL

**Tests:** 83 pass / 8 pre-existing failures (all in test_score.py, all from the company_tier
inversion done earlier this session — covered by COIN-SCORE-TESTS follow-up).

**Decisions:** Mode authoring done as prompt-driven markdown (no Python implementation).
The agent reads the mode at execution time. This keeps the LLM-as-runtime model intact
while still allowing structural regression tests (each test asserts the mode markdown
contains required sections, refusals, gates).

---

## What Was Just Done (2026-04-25, Session 4 — Part 1)

### COIN-AUDIT — modes/audit.md (truthfulness check) ✅ COMPLETE

**New files:**
- `modes/audit.md` (159 lines) — 9-check truthfulness audit with auto-fix flow + human gate
- `tests/test_audit_mode.py` (10 tests) — structural + regression tests against the known-bad Filevine JSON
- `docs/tasks/prompts/complete/COIN-AUDIT_04-25_modes-audit.md` — task prompt

**Tests:** 10/10 audit tests pass. Pre-existing 8 failures in `test_score.py` are from
this session's earlier company_tier inversion (FAANG 100 → 25 as pedigree filter); not
caused by COIN-AUDIT. Needs follow-up task `COIN-SCORE-TESTS` to update assertions.

**Decisions:** 9 audit checks encoded directly from the 2026-04-24 code review's CRITICAL/HIGH
findings. Each check has an explicit fail condition, severity, and fix template — refusing
to soften them is a hard rule.

---

## What Was Just Done (2026-04-25, Session 3 — Part 3)

### santifer feature parity: scoring richness + liveness + PDF ✅ COMPLETE

**4 features added:**

**1. 8-dimension scoring with A-F grades** (`config.py`, `careerops/score.py`):
- Old: 4 dimensions (comp, skill, title, remote)
- New: 8 dimensions — added `company_tier` (FAANG+ vs unicorn vs unknown),
  `application_effort` (LinkedIn easy vs ATS vs custom), `seniority_fit`
  (staff/principal vs senior vs junior), `culture_fit` (red flag count)
- New `score_breakdown()` returns per-dimension raw scores, weights, and
  contributions — useful for diagnosing why a role scored low
- New `score_grade()` converts composite to A–F (A≥85, B≥70, C≥55, D≥40, F<40)
- Netflix TPM Infrastructure: 76.1 → **80.0 (B)** under new weights
- Tests: 20 → **48 passing**

**2. Dashboard shows Grade column** (`careerops/pipeline.py`):
- Fit column still present; Grade column added with color coding
  (bold green=A, green=B, yellow=C, red=D, dim red=F)

**3. Liveness check** (`scripts/liveness_check.py`):
- Pings all non-terminal roles; marks `closed` if HTTP 404 or JD removal
  phrases detected. `--dry-run` flag for report-only mode.
- System dep: requires `httpx` (already in deps)

**4. PDF generation** (`scripts/render_pdf.py`, `data/resume_template.html`):
- Reads generated resume JSON, renders via Jinja2 HTML template, writes
  print-ready PDF via weasyprint
- System dep: requires `brew install pango` (one-time, done on this machine)
- First PDF: `data/resumes/generated/0004_cox-style-tpm_2026-04-25.pdf`
- `requirements.txt` now includes `jinja2>=3.1.0`

---

## What Was Just Done (2026-04-25, Session 3 — Part 2)

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

1. **Submit the Netflix application.** Resume + PDF are generated:
   `data/resumes/generated/0004_cox-style-tpm_2026-04-25.{json,pdf}`.
   Sean reviews, applies, then: `/coin track 4 applied`.
2. **Score + tailor the Netflix TPM 6 — Data Systems role** — same company,
   different infra focus; $420K–$630K comp range expected.
3. **Re-score all 31 existing roles** under the new 8-dimension weights —
   run: `python scripts/discover.py --rescore-existing` (not yet wired) or
   inline Python loop against `list_roles()`.
4. **Add comp extraction to scraper** — most roles have null comp_min;
   cross-reference Levels.fyi for Tier 1 companies.

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
| S-3.1 | Scheduler: daily auto-search cron | ✅ Done (COIN-SCHEDULER — launchd 7am + iMessage A-grade interrupt; needs `/coin scheduler install` + Automation grant to activate) |
| S-3.2 | Multi-board: Greenhouse / Lever / Workday | ✅ Done (COIN-MULTI-BOARD — Greenhouse + Lever + Ashby) |
| S-3.3 | Two-stage JD-aware scoring | ✅ Done (COIN-SCORE-V2) |
| S-3.4 | Web dashboard at /lab/coin | ✅ Done (COIN-WEB-UI — gated at handoffpack.com/lab/coin) |
| S-3.5 | STAR proof-point library + deep-dive mode | ✅ Done (COIN-EXPERIENCE-DEEPDIVE) |

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
