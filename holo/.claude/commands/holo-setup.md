> **Important:** Run these commands with Claude Code opened from the `holo/` project directory (the folder containing `CLAUDE.md`). All paths are relative to that root.

Run the Holo first-time setup. Check everything is working, install dependencies, and confirm the system is ready.

Follow these steps exactly, in order. Show a checklist as you go:

**Step 1 — Check Python version**
Run: `python3 --version`
- If Python 3.11 or higher: ✅ 
- If Python 3.10 or lower: tell the user to install Python 3.11+ from python.org and stop.
- If not found: tell the user to install Python 3 from python.org and stop.

**Step 2 — Create virtual environment**
Run: `python3 -m venv .venv`
- If it already exists, skip silently: ✅ (already exists)
- If it fails: explain the error in plain English and stop.

**Step 3 — Install dependencies**
Run: `.venv/bin/pip install pandas numpy requests beautifulsoup4 python-dateutil --quiet`
- Show: ✅ Installing dependencies...
- If it fails: show the error and tell the user to check their internet connection.

**Step 4 — Create data directories**
Run: `mkdir -p data/db`
- Show: ✅ Data directories ready

**Step 5 — Smoke test (live data fetch)**
Run: `.venv/bin/python pokequant/scraper.py --card "Charizard V" --days 5`
- If the output is a JSON array with at least 1 result: ✅ Live data connection working
- If the output contains `"error"`: ⚠️ Data fetch failed (network or site issue) — tell the user this is non-critical and they can still use the tool with a retry later
- If Python crashes with an import error: tell the user to run Step 3 again

**Final output — always end with this block:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Holo is ready.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Try these commands:

  /holo-buy-sell Charizard V
  /holo-price-check Umbreon VMAX
  /holo-box-value Obsidian Flames 149.99
  /holo-bulk-sell
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If any step failed, replace ✅ with ❌ and tell the user what to fix before using Holo.
