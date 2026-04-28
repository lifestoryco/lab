# Coin Scheduler — Setup Guide

## What it does

A launchd job fires daily at **7:00 AM local time**, runs
`scripts/discover.py` to scrape fresh roles, then runs
`scripts/notify.py` which sends Sean a single iMessage **only** for
A-grade roles (composite fit ≥ 85) discovered in the last 24 hours.
Everything else accumulates silently in the dashboard.

Spam is the failure mode this design prevents — A-grade roles are
rare enough (target: < 2/week) that an interrupt is justified.

## Required environment variable

Add to `.env`:

```bash
COIN_NOTIFY_PHONE=+18018033084     # E.164 — your iPhone-registered Apple ID number
```

`.env.example` ships with the placeholder `+15551234567`. If unset,
notify.py logs `"COIN_NOTIFY_PHONE not set — skipping notify"` and
exits 0 (the job still scrapes; you just don't get pings).

## Required one-time permission grant

The first time osascript tries to send a message, macOS will prompt:

> "Terminal" wants access to control "Messages". Allowing control will
> provide access to documents and data in "Messages" and to perform
> actions within that app.

Click **Allow**. (The prompting app is whichever terminal/process
launched the script the first time — Terminal, iTerm, Claude Code,
or launchd itself.)

If you click "Don't Allow", silently every subsequent run will fail.
Reset with:

```bash
tccutil reset AppleEvents
```

Then re-run `/coin scheduler test` to retrigger the prompt.

## iMessage prerequisite

Your Mac must be signed into iMessage with the same Apple ID as your
phone, and the phone number must be reachable via iMessage. Verify
by sending yourself a test from Messages.app on the Mac — if it
delivers, AppleScript will too. There is no SMS fallback.

## Install

```bash
/coin scheduler install
# or directly:
bash scripts/scheduler/install.sh
```

Idempotent — re-running reloads the plist (use this after editing the
plist).

## Verify

```bash
launchctl list | grep co.lifestory.coin.discover
launchctl print user/$UID/co.lifestory.coin.discover
```

Both should show the job loaded.

## Test fire

```bash
/coin scheduler test
```

Force-fires the job out of band. Watch the discover + notify logs
update under `data/logs/`.

## Disable temporarily

```bash
launchctl unload ~/Library/LaunchAgents/co.lifestory.coin.discover.plist
# Re-enable:
launchctl load -w ~/Library/LaunchAgents/co.lifestory.coin.discover.plist
```

## Uninstall

```bash
/coin scheduler uninstall
```

## Logs

| Path | Contents |
|---|---|
| `data/logs/discover_<YYYY-MM-DD>.log` | discover.py stdout + stderr |
| `data/logs/notify_<YYYY-MM-DD>.log` | notify.py stdout (sent=N counts) |
| `data/logs/notify_<YYYY-MM-DD>.error.log` | osascript stderr from failed sends |
| `data/logs/launchd_stdout.log` | launchd-level stdout (rare) |
| `data/logs/launchd_stderr.log` | launchd-level stderr (rare) |

Optional log rotation (run weekly via separate cron / launchd job):

```bash
find data/logs -mtime +14 -name "*.log" -delete
```

## Disclaimer — Mac must be awake

launchd will fire the job at the next wake if the Mac was asleep at
7am. For consistent 7am behavior:

- run `caffeinate -d` overnight, OR
- enable System Settings → Energy Saver → Wake for network access, OR
- accept that the job runs on next wake (fine for daily cadence).

## Why iMessage and not email/Slack

Sean already gets too many emails. iMessage on his phone is the
channel he actually reads, and A-grade roles are rare enough that the
interrupt is genuinely useful. No third-party service, no API key —
just AppleScript + Messages.app.
