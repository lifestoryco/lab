---
description: Multi-agent parallel code review. Four specialist subagents (Security, Logic, Architecture, UX) examine the same code simultaneously and produce independent reports. Use before any commit or PR.
---

# /code-review

Runs a 4-agent parallel code review against the holo codebase. Specialists examine code simultaneously — more thorough than a single-agent review.

Usage:
  /code-review           → review all uncommitted changes
  /code-review --fix     → review + auto-remediate CRITICAL and HIGH issues
  /code-review [paths]   → scope review to specific files

---

## PHASE 1: SCOPE DISCOVERY

**Target:** `$ARGUMENTS`

1. **Determine scope.** If `$ARGUMENTS` is empty or `--fix`, review ALL uncommitted changes:
   ```bash
   git diff --stat && git diff --cached --stat && git status -s
   ```
   If `$ARGUMENTS` contains file paths, scope to those files only.

2. **Capture the full diff.** Run `git diff` and `git diff --cached`. For specific files, read them in full.

3. **Load project rules.** Read `CLAUDE.md`. These rules are LAW — violations are automatically CRITICAL.

Print scope summary:
```
================================================================
  REVIEW SCOPE
  Files:    [N] changed
  Domains:  [api | pokequant | scraper | frontend | tests | config]
  Mode:     [report-only | report + auto-fix]
================================================================
```

---

## PHASE 2: PARALLEL REVIEW — 4 AGENTS SIMULTANEOUSLY

Launch all four subagents in parallel via the Agent tool. Pass the full diff to each.

### Agent 1 — Security Reviewer

```
prompt: |
  Paranoid security audit for the Holo Pokémon TCG price tool.
  Assume every card name input is adversarial.

  HOLO SECURITY RULES (violations are CRITICAL):
  - card_name and all user-supplied params MUST be sanitised before use in
    shell commands, file paths, or SQL queries. No f-string injection.
  - SQLite cache MUST live in /tmp/ (Vercel read-only FS). Any write to a
    path outside /tmp/ is a CRITICAL serverless failure.
  - No API keys or secrets hardcoded in source. Use os.environ.get() only.
  - CORS: Access-Control-Allow-Origin must never be '*' in production
    handlers — it must be the specific handoffpack.com origin.
  - requests.get() calls MUST have a timeout= argument. Missing timeout
    allows infinite hang that kills the Vercel function.
  - Do not log raw card names or prices to stdout in JSON-protocol paths
    (stdout is reserved for the JSON response; use logger.* to stderr).

  DIFF / FILES: [paste full diff]

  SCAN FOR: injection via card_name, hardcoded secrets, missing request
  timeouts, writes outside /tmp, CORS wildcards, SQL injection in raw
  SQLite queries, missing input bounds checks on numeric params (days,
  cost, etc.).

  OUTPUT (strict JSON):
  { "findings": [{ "severity": "CRITICAL|HIGH|MEDIUM|LOW", "file": "...",
    "line": 0, "title": "...", "why": "...", "fix": "...",
    "preExisting": false, "effort": "LOW|MED|HIGH" }],
    "positives": [] }
```

### Agent 2 — Logic Reviewer

```
prompt: |
  Domain expert reviewing holo's price analysis logic and data pipeline.

  HOLO LOGIC RULES (violations are CRITICAL):
  - Cache key in fetch_sales() MUST include days. Key form:
    "{source}_{grade}_{days}d" — omitting days causes range tabs to return
    stale data (this exact bug was fixed; regressions are CRITICAL).
  - All pd.to_datetime() calls on sale dates MUST pass utc=True to produce
    timezone-aware timestamps. Naive timestamps break IQR normalisation.
  - _handle_history() MUST apply a hard cutoff filter:
    cutoff = date.today() - timedelta(days=days)
    filtering buckets before building the points list is required.
  - RSI computation MUST use Wilder's smoothed EWM:
    ewm(alpha=1/period, adjust=False). Simple rolling mean is wrong.
  - sales_used <= 2 MUST set insufficient_data_warning on CompResult.
  - _lookup_card_meta() MUST NOT cache empty results ({} or missing "id").
    Only cache when meta.get("id") is truthy.
  - Grading ROI EV formula: gross_10 + gross_9 + gross_sub - grading_cost
    - shipping. Missing any term produces a wrong verdict.

  DIFF / FILES: [paste full diff]

  SCAN FOR: cache key missing days, naive timestamps, missing cutoff filter
  in history handler, wrong RSI formula, empty-meta cache poisoning,
  incorrect EV math, off-by-one in date ranges, silent division-by-zero
  in percentage calculations (guard with `if first_price > 0`).

  OUTPUT: same strict JSON format as Security Reviewer.
```

### Agent 3 — Architecture Reviewer

```
prompt: |
  Senior Python/TypeScript architect reviewing holo for correctness and
  Vercel serverless constraints.

  HOLO ARCHITECTURE RULES (violations are CRITICAL):
  - Vercel Python functions have a 60s maxDuration and a read-only FS
    outside /tmp. Any file write outside /tmp is a deployment bug.
  - os.environ.setdefault("HOLO_CACHE_DB", "/tmp/holo_cache.db") MUST be
    called before any import that reads _CACHE_DB at module level.
  - All public pokequant functions MUST have Python type hints. No implicit
    Any. Return types required.
  - New scraper logic MUST have corresponding pytest tests in tests/.
    Untested scraper paths are HIGH (they will silently break on site
    redesigns like the 2026 PriceCharting overhaul).
  - Do not import pandas, numpy, or beautifulsoup4 at module level inside
    api/index.py — they are slow and kill cold-start time. Import inside
    handler functions only.
  - config.py is the single source of truth for all numeric thresholds
    (fees, RSI periods, SMA windows, shipping costs). Hardcoded magic
    numbers anywhere else are HIGH.
  - pokequant modules must not import from api/. Circular dependency
    api/ → pokequant/ → api/ is a CRITICAL import error.

  DIFF / FILES: [paste full diff]

  SCAN FOR: writes outside /tmp, module-level heavy imports in api/index.py,
  magic numbers that belong in config.py, missing type hints, circular
  imports, missing tests for new scraper branches, N+1 SQLite queries,
  BeautifulSoup objects not GC'd (pass soup to a function, don't store
  globally), stale closures in async fetch patterns.

  OUTPUT: same strict JSON format as Security Reviewer.
```

### Agent 4 — UX Reviewer

```
prompt: |
  Senior frontend engineer reviewing holo's Next.js UI in
  handoffpack-www/components/lab/holo/.

  Only review frontend files (.tsx, .css, files under components/ or app/).
  If no frontend files changed, return:
  { "findings": [], "positives": ["No frontend files in changeset."] }

  HOLO FRONTEND RULES (violations are CRITICAL):
  - NEVER use raw <img> tags. Always use <Image> from next/image.
    Raw <img> bypasses Next.js optimisation AND hits CSP restrictions.
  - External image domains (images.pokemontcg.io) MUST be in both
    next.config.js remotePatterns AND the CSP img-src header.
  - All price / numeric displays MUST use tabular-nums class and
    JetBrains Mono font family. Proportional fonts cause layout shift.
  - Min touch target: 48px height on ALL buttons and interactive elements.
  - Design tokens: amber-400 (brand), emerald-400 (up), red-400 (down),
    zinc-900 (panels), #000 (background). No other accent colors.
  - Do NOT show raw API field names, "undefined", "null", or "—" for
    values that should have loaded. Show a Spinner or skeleton instead.
  - useEffect deps arrays MUST include all values read inside the effect
    (card name, grade, range). Missing deps cause stale data bugs.
  - The Sparkline component must receive at least 2 points to render;
    guard with `if (!points || points.length < 2)` before SVG path math.
  - GradeChip, DeltaChip, StarButton: if onClick is provided, render as
    <button> not <div> for keyboard and screen-reader accessibility.

  DIFF / FILES: [paste full diff]

  SCAN FOR: raw <img> tags, missing CSP entries for new image domains,
  non-tabular price displays, touch targets under 48px, wrong brand colors,
  missing useEffect deps, missing loading/error/empty states, SVG path NaN
  (division by zero when min === max in Sparkline), SSR hydration mismatches
  (localStorage access outside useEffect), missing aria-label on icon buttons.

  OUTPUT: same strict JSON format as Security Reviewer.
```

---

## PHASE 3: SYNTHESIS & REPORT

1. Parse each agent's JSON. Extract findings manually if prose was returned.
2. Deduplicate — same file + line + issue = merge, keep highest severity.
3. Filter false positives that contradict explicit project rules.
4. Sort: CRITICAL → HIGH → MEDIUM → LOW. Within tier, sort by effort (LOW first).
5. Verdict: **PASS** (0 CRITICAL, 0 HIGH) | **NEEDS ATTENTION** (0 CRITICAL, 1+ HIGH) | **NEEDS WORK** (1+ CRITICAL)

```
================================================================
  CODE REVIEW — [N] files | [M] findings
  Verdict: [PASS | NEEDS ATTENTION | NEEDS WORK]
================================================================

WHAT'S GOOD
  [merged positives, deduplicated]

CRITICAL (resolve before merging)
  [file:line] Title
  Impact: [why]
  Fix: [code]
  Effort: LOW|MED|HIGH  Pre-existing: yes|no

HIGH (resolve soon)
  [same format]

MEDIUM (address in follow-up)
  [same format]

LOW (informational / style)
  [same format]

PRE-EXISTING ([count])
  [preExisting: true items, listed separately]

Approved by: Security, Logic, Architecture, UX
Issues requiring attention: [CRITICAL + HIGH count]
```

---

## PHASE 4: AUTO-FIX

**Only runs if `$ARGUMENTS` contains `--fix`.**

Fix order: CRITICAL → HIGH. Skip MEDIUM, LOW, and PRE-EXISTING.

For each fix: Read file → Edit tool → verify no downstream breakage.
No `# TODO` or placeholder comments — write the actual implementation.

`--fix` does NOT apply security fixes, public API changes, or architecture restructuring.

If `--fix` is absent:
```
Tip: Run /code-review --fix to auto-remediate CRITICAL and HIGH issues.
```

---

## PHASE 5: QUALITY GATE

```bash
# Python type check (if mypy is installed)
.venv/bin/mypy api/index.py pokequant/ --ignore-missing-imports 2>/dev/null || echo "mypy not installed — skipping"

# Run the test suite
.venv/bin/pytest tests/ -q --tb=short 2>&1 | tail -20
```

If `--fix` was applied and failures appear, fix your own mistakes (up to 3 cycles).

```
================================================================
  QUALITY GATE: [PASS | FAIL]
  Tests:      [N passed, M failed]
  Type check: [clean | N errors]
================================================================
```

---

## Rules

- Do NOT sugarcoat bad code. Be direct and specific.
- Every finding MUST include a concrete fix (code snippet, not advice).
- Every finding MUST explain WHY it matters (impact, not just "bad practice").
- CLAUDE.md rules are LAW — violations are always CRITICAL.
- Pre-existing issues are flagged but kept separate from new issues.
- Review is read-only by default. Only `--fix` enables writes.
- If nothing changed and no files specified: "Nothing to review." and stop.
