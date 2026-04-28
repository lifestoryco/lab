# Coin Mode — `scheduler` (launchd job + iMessage interrupt)

> Load `modes/_shared.md` first.

**Purpose:** Manage the daily 7am `discover` + `notify` launchd job.
Quiet by design — only **A-grade** roles (composite ≥ 85) trigger an
iMessage interrupt; everything else accumulates silently in the
dashboard for the next manual `/coin status` check.

The launchd job runs `scripts/discover.py` then `scripts/notify.py`.
On any unhandled discover error, `data/.discover_failed.flag` is
written, and notify.py sends a single failure-alert iMessage instead
of a role message.

---

## Sub-commands

### `/coin scheduler install`

```bash
bash scripts/scheduler/install.sh
```

Idempotent — re-running reloads the plist with any edits.

### `/coin scheduler status`

```bash
launchctl list | grep coin
tail -30 data/logs/discover_$(date +%Y-%m-%d).log 2>/dev/null
tail -30 data/logs/notify_$(date +%Y-%m-%d).log 2>/dev/null
```

Surfaces the launchctl entry plus today's tail. Useful first check
when "did it run this morning?" comes up.

### `/coin scheduler test`

```bash
launchctl start co.lifestory.coin.discover
sleep 5
tail -50 data/logs/discover_$(date +%Y-%m-%d).log 2>/dev/null
tail -50 data/logs/notify_$(date +%Y-%m-%d).log 2>/dev/null
```

Force-fires the job out of band. The first invocation is what
triggers the macOS Automation permission grant (Terminal/iTerm/Claude
Code → control Messages.app). If you click "Don't Allow", reset with
`tccutil reset AppleEvents` and try again.

### `/coin scheduler logs`

```bash
tail -100 data/logs/discover_$(date +%Y-%m-%d).log 2>/dev/null
tail -100 data/logs/notify_$(date +%Y-%m-%d).log 2>/dev/null
```

Same as `status` but no launchctl noise — handy when re-firing isn't
desired.

### `/coin scheduler uninstall`

```bash
bash scripts/scheduler/uninstall.sh
```

Unloads and deletes the LaunchAgent plist.

---

## First-time setup

See `docs/scheduler_setup.md` for the full runbook. Quick version:

1. Set `COIN_NOTIFY_PHONE` in `.env` (E.164 format, e.g. `+18018033084`).
2. Run `/coin scheduler install`.
3. Run `/coin scheduler test` once. macOS will prompt to allow your
   terminal/Claude Code to control Messages.app — click **Allow**.
4. Verify your phone received the test message (or the silent-no-roles
   case logs `"Notify: sent=0"`).

**Mac must be awake at 7am** or the job fires on next wake — that's
fine for daily cadence.

---

## Hard refusals

| Refusal | Why |
|---|---|
| Lowering `--min-grade` below A in the launchd plist | Spam destroys the value of the interrupt; only rare A-grade roles earn it |
| Running install.sh from outside `scripts/scheduler/` | Source-path detection is `dirname "$0"`; cd into the dir first |
| Editing the plist label | Other tooling greps for `co.lifestory.coin.discover` |
| Auto-resetting `tccutil reset AppleEvents` without telling Sean | Resets all of his AppleEvents grants, not just this one |
