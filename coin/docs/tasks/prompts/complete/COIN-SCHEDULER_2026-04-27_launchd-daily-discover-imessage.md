---
task: COIN-SCHEDULER
title: launchd daily discover + iMessage A-grade interrupt
phase: Automation
size: L
depends_on: COIN-SCORE-V2, COIN-MULTI-BOARD, COIN-LEVELS-CROSSREF
created: 2026-04-27
---

# COIN-SCHEDULER: Daily auto-discover + iMessage interrupt for A-grade roles

## Context

Coin is currently on-demand only. Sean has to remember to run `/coin discover`. The window between a hot $160K+ role being posted and it filling with applicants is short — sometimes <72hr for top postings. Roles that match Sean's archetypes at the comp floor are rare enough that missing one because he forgot to scrape on a Tuesday is a real cost.

We want Coin to discover daily at 7am Pacific without Sean lifting a finger, and to interrupt him via iMessage **only** when an A-grade (composite ≥85) role lands. Quiet, but actionable. No spam — only the rare A-grade role earns an interrupt; B/C/D-grade roles wait silently in the dashboard for Sean to check at his convenience.

This task wires the macOS-native pieces: `launchd` for the daily fire, `osascript` + Messages.app for the iMessage bridge.

## Pre-conditions

- [ ] **COIN-SCORE-V2 has shipped** — A-grade composite from stage 2 (skills + comp + lane fit) is meaningful. Stage-1-only A-grade produces too many false positives (cf. the #4 / #13 / #14 misses logged in Session 4).
- [ ] **COIN-MULTI-BOARD has shipped** — Greenhouse + Lever + Ashby boards are wired so daily discovery has multiple sources, not just LinkedIn guest API. More sources = more A-grade chances.
- [ ] **COIN-LEVELS-CROSSREF has shipped** — Levels.fyi cross-reference is filling in verified comp on more roles, which feeds the comp-floor portion of the A-grade composite.
- [ ] `scripts/discover.py` accepts `--boards` and `--deep-score N` flags
- [ ] `careerops.score.grade_from_score` (or equivalent) returns `A`/`B`/`C`/`D`/`F` from a 0–100 composite
- [ ] Migration framework `scripts/migrations/m00X_*.py` pattern is in place (m003–m006 already exist)
- [ ] `.venv/bin/python` resolves and `pytest tests/ -q` is green at HEAD

## Goal

When Sean wakes up tomorrow and grabs his phone, if a role at his comp floor with strong skill match was posted yesterday, his Mac has already scraped it, scored it, and texted him the role + URL. Otherwise his phone is silent and the dashboard quietly accumulates B/C-grade rows for his next manual check.

## Steps

### Step 1 — New script `scripts/notify.py`

Create `scripts/notify.py` with this CLI surface:

```bash
python scripts/notify.py [--since-hours N] [--min-grade A|B|C] [--dry-run]
```

Defaults: `--since-hours 24 --min-grade A`.

**Logic:**

1. Open `data/db/pipeline.db`.
2. Select roles where `discovered_at >= datetime('now', ?)` (with `?` bound from `--since-hours`) AND `grade_from_score(fit_score) >= min_grade` AND `status = 'scored'` AND `notified_at IS NULL`.
3. For each row, build the message exactly:
   ```
   🎯 Coin: A-grade role
   <Company> — <Title>
   Lane: <lane> · Fit <score> (<grade>) · <comp_label>
   Posted <age> · <location>
   <url>
   ```
   - `age` = humanized delta from `discovered_at` to now (e.g. `3h ago`, `1d ago`).
   - `comp_label` = use `careerops.compensation.format_comp_band(role)` or whatever the canonical helper is — fall back to `"comp unknown"` if null.
4. Send via macOS Messages.app:
   ```python
   subprocess.run(
       ["osascript", "-e",
        f'tell application "Messages" to send "{escaped_msg}" to buddy "{phone}" of service "iMessage"'],
       check=False, capture_output=True, text=True, timeout=15,
   )
   ```
   **Never use `shell=True` and never use Python f-string interpolation into a shell string** — the message text contains user-controlled JD content (quotes, backticks, `$`). Use the `args=` list form. The AppleScript itself is a single string with the `escaped_msg` substituted; escape any embedded `"` and `\` in the message before substitution (helper `_applescript_escape(s)`).
5. Phone number: read from `config.NOTIFY_PHONE`, which reads env var `COIN_NOTIFY_PHONE`. If unset or empty, log `"COIN_NOTIFY_PHONE not set — skipping notify"` and exit 0 (do not crash).
6. On `osascript` returncode != 0: append the stderr to `data/logs/notify_<YYYY-MM-DD>.error.log`, do not crash, continue to next role.
7. On success (returncode == 0): `UPDATE roles SET notified_at = datetime('now') WHERE id = ?` — idempotent, never double-notifies.
8. `--dry-run`: print each would-send message to stdout, **do not** call `osascript`, **do not** write `notified_at`.

**Special case — discover failure flag:**

`scripts/discover.py` should be patched (small one-line change) to write `data/.discover_failed.flag` (containing the timestamp + brief error) on any unhandled exception path, and to delete that flag at the start of every successful run. In `notify.py`, **before** the role-loop, check for that flag:

- If present and `--dry-run` not set: send a single iMessage `"🚨 Coin discover failed today — check logs at data/logs/discover_<YYYY-MM-DD>.log"`, then delete the flag, then exit 0 without processing roles.
- If `--dry-run`: print the would-send failure message, do not delete the flag.

### Step 2 — Migration `scripts/migrations/m007_notified_at.py`

Follow the m003–m006 idempotent pattern:

- Adds `notified_at TEXT NULL` to `roles`.
- Inserts a row into `schema_migrations` (`version='m007'`, `applied_at=now`).
- `if 'notified_at' in existing_columns: return` — safe to re-run.
- Wired into the migration runner so `python scripts/migrate.py` (or however the runner is invoked) picks it up automatically.

### Step 3 — launchd plist `scripts/scheduler/co.lifestory.coin.discover.plist`

Create `scripts/scheduler/co.lifestory.coin.discover.plist`:

- **Label:** `co.lifestory.coin.discover` (reverse-DNS; `lifestory.co` per CLAUDE.md).
- **ProgramArguments:** a 3-element array — `/bin/bash`, `-c`, and one shell string that does:
  ```
  cd /Users/tealizard/Documents/lab/coin && \
  .venv/bin/python scripts/discover.py --location 'Utah, United States' --deep-score 15 --boards linkedin,greenhouse,lever,ashby \
    >> data/logs/discover_$(date +\%Y-\%m-\%d).log 2>&1 ; \
  .venv/bin/python scripts/notify.py --since-hours 24 --min-grade A \
    >> data/logs/notify_$(date +\%Y-\%m-\%d).log 2>&1
  ```
  Note `\%Y-\%m-\%d` — `%` must be escaped inside plist XML strings because launchd treats `%` as a substitution char.
  Use `;` not `&&` between discover and notify so notify still runs even if discover partially failed (the discover-failed flag handles the alert path).
- **StartCalendarInterval:** `<dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>` — fires at 7:00 system-local time daily. Sean's Mac is on Pacific.
- **StandardOutPath:** `/Users/tealizard/Documents/lab/coin/data/logs/launchd_stdout.log`
- **StandardErrorPath:** `/Users/tealizard/Documents/lab/coin/data/logs/launchd_stderr.log`
- **RunAtLoad:** `<false/>` (we don't want `install.sh` to fire it immediately — Sean uses `scheduler test` for that).
- **WorkingDirectory:** `/Users/tealizard/Documents/lab/coin`

All paths in the plist must be absolute — no `~`, no relative paths. launchd does not expand `~`.

### Step 4 — Installer `scripts/scheduler/install.sh`

Idempotent installer:

```bash
#!/usr/bin/env bash
set -euo pipefail
PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/co.lifestory.coin.discover.plist"
PLIST_DST="$HOME/Library/LaunchAgents/co.lifestory.coin.discover.plist"

if launchctl list | grep -q co.lifestory.coin.discover ; then
  echo "Unloading existing job..."
  launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"
launchctl load -w "$PLIST_DST"

if launchctl list | grep -q co.lifestory.coin.discover ; then
  echo "✓ Installed: co.lifestory.coin.discover"
  echo "  Plist: $PLIST_DST"
  echo "  Next fire: 7:00 AM local time daily"
else
  echo "✗ Install failed — job not in launchctl list"
  exit 1
fi
```

Companion `scripts/scheduler/uninstall.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
PLIST_DST="$HOME/Library/LaunchAgents/co.lifestory.coin.discover.plist"
if launchctl list | grep -q co.lifestory.coin.discover ; then
  launchctl unload "$PLIST_DST"
fi
rm -f "$PLIST_DST"
echo "✓ Uninstalled: co.lifestory.coin.discover"
```

Both scripts must be `chmod +x` after creation.

### Step 5 — Mode `modes/scheduler.md`

Author `modes/scheduler.md` following the existing mode-file conventions (cf. `modes/discover.md`, `modes/audit.md`). Sub-commands:

| Sub-command | Action |
|---|---|
| `/coin scheduler install` | `bash scripts/scheduler/install.sh`, surface stdout |
| `/coin scheduler status` | `launchctl list \| grep coin`, then tail `data/logs/discover_$(date +%Y-%m-%d).log` (last 30 lines), then tail `data/logs/notify_$(date +%Y-%m-%d).log` |
| `/coin scheduler uninstall` | `bash scripts/scheduler/uninstall.sh` |
| `/coin scheduler test` | `launchctl start co.lifestory.coin.discover` (force-fires the job out of band), wait 5s, then tail today's discover + notify logs |
| `/coin scheduler logs` | tail last 100 lines of today's discover + notify logs (handy without re-firing) |

Mode file should also include a "first-time setup" section that mirrors `docs/scheduler_setup.md` (Step 7), and call out that a one-time macOS Automation permission grant is required.

### Step 6 — SKILL.md routing

Add to `.claude/skills/coin/SKILL.md` routing table:

| Pattern | Routes to |
|---|---|
| `scheduler install`, `scheduler status`, `scheduler uninstall`, `scheduler test`, `scheduler logs` | `modes/scheduler.md` |
| bare `scheduler` | `modes/scheduler.md` (mode prints the sub-command help) |

### Step 7 — Documentation `docs/scheduler_setup.md`

Author `docs/scheduler_setup.md` covering:

1. **What it does** — 7am daily discover + A-grade iMessage interrupt.
2. **Required env var:** `COIN_NOTIFY_PHONE` — Sean's iPhone-registered Apple ID number, format `+18018033084` (E.164). Add to `.env` and to `.env.example` (with placeholder `+15551234567`).
3. **Required one-time permission:** macOS System Settings → Privacy & Security → Automation → grant Terminal (or iTerm, or Claude Code) permission to control Messages.app. The first invocation will trigger this prompt — if denied, all subsequent runs silently fail until granted. Document how to reset if Sean clicks "Don't Allow": `tccutil reset AppleEvents`.
4. **iMessage prerequisite:** Sean's phone must be reachable via iMessage (verify by sending himself a test from Messages.app). There's no programmatic SMS fallback — AppleScript only bridges iMessage.
5. **Install:** `/coin scheduler install` (or `bash scripts/scheduler/install.sh`).
6. **Verify:** `launchctl print user/$UID/co.lifestory.coin.discover` shows the job; `launchctl list | grep coin` shows it loaded.
7. **Test fire:** `/coin scheduler test`.
8. **Disable temporarily:** `launchctl unload ~/Library/LaunchAgents/co.lifestory.coin.discover.plist` (re-enable with `load -w`).
9. **Uninstall:** `/coin scheduler uninstall`.
10. **Logs:** `data/logs/discover_<date>.log`, `data/logs/notify_<date>.log`, `data/logs/launchd_stdout.log`, `data/logs/launchd_stderr.log`. Optional rotation: `find data/logs -mtime +14 -delete` weekly via a separate launchd job or manual cron — not in scope here, just mentioned.
11. **Disclaimer — Mac must be awake:** launchd will fire the job at the next wake if the Mac was asleep at 7am. For consistent 7am behavior either run `caffeinate -d` overnight, set System Settings → Energy Saver → Wake for network access, or accept that the job runs on next wake (fine for daily-cadence use).
12. **Why iMessage and not email/Slack:** Sean already gets too many emails. iMessage on his phone is the channel he actually reads. A-grade roles are rare enough (target: <2/week) that the interrupt is justified.

### Step 8 — Tests

**`tests/test_notify.py`** — 10 tests, all using `unittest.mock.patch('subprocess.run')` so no real iMessages send during pytest:

1. `test_notify_no_fresh_roles_is_noop` — empty DB → 0 osascript calls, exit 0.
2. `test_notify_fresh_a_grade_builds_correct_message` — seed an A-grade row from 2h ago; assert `subprocess.run` called once with `args[0] == 'osascript'`, message contains company + title + URL + `🎯 Coin: A-grade role`.
3. `test_notify_b_grade_skipped_when_min_grade_a` — seed B-grade row → 0 osascript calls.
4. `test_notify_marks_notified_at_after_success` — mock returncode=0 → assert `notified_at` is non-null after the run.
5. `test_notify_does_not_resend_already_notified` — row with `notified_at` already set → 0 osascript calls.
6. `test_dry_run_does_not_call_osascript` — `--dry-run` flag → 0 osascript calls, message printed to stdout, `notified_at` still NULL.
7. `test_osascript_failure_logged_does_not_crash` — mock returncode=1, stderr="permission denied" → script exits 0, error log file exists with the stderr content, `notified_at` still NULL for the failed row.
8. `test_missing_phone_skips_silently` — `COIN_NOTIFY_PHONE` env var unset → exit 0, no osascript calls, log message printed.
9. `test_discover_failed_flag_triggers_alert_message` — write `data/.discover_failed.flag`, seed an A-grade row → assert exactly one osascript call with the failure message (not the role message), flag is deleted after.
10. `test_applescript_escaping` — seed a role whose title contains `"` and `\` → assert the osascript args do not contain unescaped quote chars that would break the shell-free AppleScript.

**`tests/test_migrations_m007.py`** — 3 tests:

1. `test_m007_adds_notified_at_column` — fresh DB → run m007 → `PRAGMA table_info(roles)` includes `notified_at`.
2. `test_m007_idempotent` — run twice → no error, schema unchanged.
3. `test_m007_records_schema_migrations_row` — `SELECT version FROM schema_migrations WHERE version='m007'` returns one row.

All tests use the existing `tmp_path` / in-memory DB fixture pattern from `tests/test_migrations_m006.py`.

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/ -q --tb=short
# Expect: prior count + 13 new tests, all green

# Smoke
.venv/bin/python scripts/migrate.py                      # apply m007
.venv/bin/python scripts/notify.py --dry-run             # prints would-send messages or nothing
bash scripts/scheduler/install.sh                        # installs plist
launchctl list | grep co.lifestory.coin.discover        # shows the job
launchctl start co.lifestory.coin.discover              # force-fires (Sean should grant Automation permission here)
tail -50 data/logs/discover_$(date +%Y-%m-%d).log
tail -50 data/logs/notify_$(date +%Y-%m-%d).log
bash scripts/scheduler/uninstall.sh                      # cleanup
```

- [ ] All 13 new tests pass; no regressions in existing suite.
- [ ] `bash scripts/scheduler/install.sh` is idempotent (run twice, no errors).
- [ ] `launchctl list` shows `co.lifestory.coin.discover` after install.
- [ ] `launchctl start co.lifestory.coin.discover` populates today's `discover_*.log` and `notify_*.log`.
- [ ] If an A-grade role exists in the last 24h, Sean receives one (1) iMessage with the spec'd message shape.
- [ ] If no A-grade role exists, Sean receives zero iMessages (silent).
- [ ] `python scripts/notify.py --dry-run` prints would-send messages without sending or marking `notified_at`.
- [ ] `bash scripts/scheduler/uninstall.sh` removes the plist and unloads cleanly.

## Style notes

- **Quiet by design.** Only A-grade interrupts. B/C/D-grade waits for Sean's manual `/coin status` check. Resist the temptation to lower the threshold "just in case" — the whole value of this feature evaporates if it spams.
- **Mac must be awake at 7am** or the job fires on next wake. Document clearly; do not add daemons or polling — launchd is the right primitive.
- **macOS Automation permission is a one-time human grant.** Document in `docs/scheduler_setup.md` so the first-fire failure is expected and recoverable, not mysterious.
- **iMessage is bridged via AppleScript.** No SMS fallback, no API, no third-party service. Sean's phone must be on iMessage (verified by sending himself a test from Messages.app on the Mac).
- **Plist label `co.lifestory.coin.discover`** follows reverse-DNS convention from CLAUDE.md (lifestory.co).
- **Never use `shell=True`** in the osascript subprocess call — JD content is user-controlled and contains shell metacharacters. Use the `args=[...]` list form and a small `_applescript_escape()` helper for the message body.
- **Failure mode for Sean's Mac asleep at 7am:** job runs on next wake. Acceptable — Coin is daily-cadence, not minute-cadence.
- **No new Python deps.** All of this is stdlib `subprocess` + `sqlite3` + `os` + the existing `careerops.*` modules.

## Definition of Done

- [ ] `scripts/notify.py` exists with the documented CLI and behavior
- [ ] `scripts/migrations/m007_notified_at.py` exists; runner picks it up
- [ ] `scripts/scheduler/co.lifestory.coin.discover.plist` exists
- [ ] `scripts/scheduler/install.sh` and `scripts/scheduler/uninstall.sh` exist and are executable
- [ ] `modes/scheduler.md` exists with all 5 sub-commands
- [ ] `.claude/skills/coin/SKILL.md` routes `scheduler *` to the mode
- [ ] `docs/scheduler_setup.md` exists and covers all 12 sections from Step 7
- [ ] `.env.example` includes `COIN_NOTIFY_PHONE=+15551234567` placeholder
- [ ] `config.NOTIFY_PHONE` reads `COIN_NOTIFY_PHONE` env var
- [ ] Discover script writes `data/.discover_failed.flag` on unhandled error and clears it on success
- [ ] All 13 new tests pass; full `pytest tests/ -q` is green
- [ ] `docs/state/project-state.md` updated with the new mode + scheduler architecture note
- [ ] No new entries in `pip list` (stdlib only)

## Rollback

```bash
# Remove the launchd job if installed
bash scripts/scheduler/uninstall.sh 2>/dev/null || true

# Remove all created files
rm -f scripts/notify.py
rm -f scripts/migrations/m007_notified_at.py
rm -rf scripts/scheduler/
rm -f modes/scheduler.md
rm -f docs/scheduler_setup.md
rm -f tests/test_notify.py tests/test_migrations_m007.py

# Drop the column (only if rollback is real, not just a re-attempt)
.venv/bin/python -c "
import sqlite3
db = sqlite3.connect('data/db/pipeline.db')
# SQLite doesn't support DROP COLUMN pre-3.35; if needed do a table rebuild.
# For rollback we usually just leave the column — it's nullable and harmless.
db.execute(\"DELETE FROM schema_migrations WHERE version='m007'\")
db.commit()
"

# Revert SKILL.md routing additions
git checkout .claude/skills/coin/SKILL.md
git checkout .env.example config.py docs/state/project-state.md scripts/discover.py
```

The discover script and all existing modes remain functional standalone — this task is purely additive infrastructure.
