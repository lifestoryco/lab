# Holo UX Hosting Recommendation

## 1. Recommended Approach: Telegram Bot

**Why Telegram wins for a phone-first TCG trader:**

- **Mobile-native by default.** Telegram is already on your phone. No browser tabs, no URLs to remember, no "open laptop to check a price." You message the bot the same way you'd text a friend. At a trade table, you type `/price Charizard ex` and get a comp back in 2 seconds.
- **Zero setup for end users.** Friends you trade with don't install anything new -- they search your bot's username in Telegram, tap Start, and they're in. Compare this to Discord (needs a server invite + account) or a web dashboard (needs a URL + bookmark).
- **Free forever at this scale.** Telegram's Bot API is completely free. You create a bot token via @BotFather in 30 seconds, no credit card, no API key application. There are no per-message fees and no monthly caps on messages for bots with small audiences. The only cost is hosting the Python process.
- **Inline keyboards map perfectly to Holo's workflow.** The `python-telegram-bot` library (v22.7, current stable) provides `InlineKeyboardMarkup` and `ConversationHandler` out of the box. A user taps `/price`, the bot replies with buttons for recent cards they've checked, or they type the card name. The response is a formatted message with the Bloomberg-style comp card Holo already generates. No HTML/CSS needed.
- **Battle-tested pattern for trading bots.** Multiple open-source trading alert bots exist on GitHub using this exact stack:
  - [Telegram-Crypto-Alerts](https://github.com/hschickdevs/Telegram-Crypto-Alerts) -- the most popular open-source crypto alerting bot, using `python-telegram-bot` + SQLite. Version 3.2.0 shipped February 2025.
  - [Telegram-Price-Tracker](https://github.com/JaySShah7/Telegram-Price-Tracker) -- uses `python-telegram-bot`, sqlite3, and BeautifulSoup for price scraping and alerts. Structurally identical to what Holo would need.
  - [telegram-crypto-alert-bot](https://github.com/paragrudani1/telegram-crypto-alert-bot) -- CoinGecko API + `python-telegram-bot` with price alerts and user-managed watchlists.
- **Shareability.** When you get a comp result, you can forward that exact message to a friend in Telegram, or to a group chat. No screenshots of a terminal needed.

### Hosting (free tier)

For a single-user polling bot, you don't even need a server -- run it on your Mac with `nohup` or `launchd` while you're at home. For always-on hosting:

| Platform | Free tier | Notes |
|----------|-----------|-------|
| **Railway** | $5/mo credits (after one-time $5 verification) | No cold starts. A typical Telegram bot uses $3-5/mo in compute. Best option for always-on. |
| **Fly.io** | 3 shared-cpu VMs, 256 MB RAM | Enough for a polling bot. May sleep after inactivity on free tier. |
| **PythonAnywhere** | Free tier with always-on tasks | Good for polling bots specifically. Limited outbound HTTP on free tier. |
| **Your own Mac** | $0 | `python bot.py` in a tmux session. Fine for 1 user. |

For 1 user: run locally ($0). For sharing with 10 friends: Railway at ~$3-5/month or within the free credit window.

---

## 2. Runner-Up: FastAPI + Single HTML File

If Telegram has a deployment blocker (e.g., Telegram is blocked in your region, or you want a URL you can paste into iMessage), a minimal FastAPI server with a single `index.html` is the next best option.

**Why it's the runner-up:**
- FastAPI natively serves JSON from SQLite -- this is exactly what `analyze.py` already outputs. You'd add 5 route handlers that call the same functions.
- A single HTML file with vanilla JavaScript `fetch()` calls can render the comp cards. No React, no build step.
- Deploys to Vercel's free tier as a serverless function with zero config. Vercel auto-detects FastAPI from `requirements.txt` and exposes it at a `.vercel.app` URL. A working Pokemon TCG price tracker already exists at [pokemon-price-tracking.vercel.app](https://pokemon-price-tracking.vercel.app/).
- [PokePrice](https://github.com/justinbchau/PokePrice) is an open-source example of exactly this: a Pokemon card price app using API calls deployed on Vercel.

**Why it loses to Telegram:**
- Requires opening a browser. On a phone at a trade event, this is slower than messaging a bot.
- You need to manage a URL and share it. Telegram bot discovery is simpler (search username).
- Vercel serverless functions have cold starts (~1-2s) and a 500ms shutdown timeout. The scraper + analysis pipeline can take 3-5 seconds, which may hit Vercel's 10-second free-tier function timeout on first call.
- SQLite on Vercel is read-only (ephemeral filesystem). You'd need to switch the cache to Vercel KV or an external DB, which adds complexity.

---

## 3. Options Considered and Rejected

### Streamlit
- Streamlit Community Cloud limits you to 3 free apps, requires a **public** GitHub repo (your scraper logic and any API patterns would be exposed), and apps sleep after inactivity.
- SQLite writes are unreliable on Streamlit Cloud -- multiple community threads report data loss because the filesystem is ephemeral. Holo's `history.db` cache would not persist between sessions.
- The [pokemon_dashboard](https://github.com/faurholdt/pokemon_dashboard) Streamlit project exists but is read-only visualization, not interactive trading analysis.
- Verdict: too many footguns for a trading tool that needs a writable cache and private logic.

### Discord Bot
- Discord bots require users to be in a Discord server. Your trade table friends may not use Discord or want to join a server just to check a price.
- Hosting requirements are identical to Telegram (always-on Python process), but Discord's gateway connection is heavier and more prone to disconnects on free hosting tiers.
- Discord slash commands have a 3-second response deadline before you must defer, which is tight for Holo's scraper pipeline.
- The [discord.py-masterclass](https://fallendeity.github.io/discord.py-masterclass/slash-commands/) guide and [Pycord guide](https://guide.pycord.dev/interactions/application-commands/slash-commands) show the pattern works, but the audience fit is wrong -- TCG traders at events use phones, not Discord.

### Vercel + Static HTML (no backend)
- A purely static site can't call `analyze.py` or the scraper. You'd need to pre-generate all data as JSON files and commit them to the repo, which defeats the purpose of live market data.
- Only viable if combined with FastAPI serverless functions (which is the runner-up option above, not this one).

---

## 4. What Holo Needs to Expose

The Telegram bot needs to call these `analyze.py` subcommands:

| Bot Command | analyze.py Subcommand | Input | Output (already JSON) |
|-------------|----------------------|-------|----------------------|
| `/price <card>` | `comp` | Scraper JSON for card (14 days) | `{cmc, mean, trend, confidence, volatility, ...}` |
| `/signal <card>` | `signal` | Scraper JSON for card (30 days) | `{signal, price, sma30, dip_pct, vol_surge_pct, ...}` |
| `/ev <set> <price>` | `ev` | Set name + retail price | `{ev, retail, delta, rec, top_card, ...}` |
| `/bulk` | `bulk` | Card counts (via conversation) | `{net, gross, shipping, liquidate, breakdown, ...}` |
| `/flip <card> <cost> <method>` | `flip` | Card name + cost + method | `{profit, margin_pct, verdict, ...}` |

### Input/output changes needed: **None.**

All subcommands already output clean JSON to stdout. The bot just needs to:
1. Call `scraper.fetch_sales()` (already a Python function) or shell out to `scraper.py`
2. Pass the result to the appropriate `analyze.py` `cmd_*` function (already importable)
3. Format the JSON result into a Telegram message string

The `_out()` helper in `analyze.py` writes to stdout, but the `cmd_*` functions can be refactored to return dicts instead of printing. Alternatively, the bot can call them as subprocesses and capture stdout -- this is simpler and avoids import-time side effects.

---

## 5. Implementation Sketch

```python
"""holo_bot.py -- Telegram bot wiring for Holo (minimal viable version)."""
import json
import subprocess
import sys
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters,
)

TOKEN = "YOUR_BOT_TOKEN"  # from @BotFather
VENV_PYTHON = str(Path(__file__).parent / ".venv" / "bin" / "python")
PROJECT_ROOT = str(Path(__file__).parent)


def run_analyze(args: list[str]) -> dict:
    """Shell out to analyze.py and return parsed JSON."""
    cmd = [VENV_PYTHON, "pokequant/analyze.py"] + args
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=15,
    )
    return json.loads(result.stdout)


def run_scraper(card_name: str, days: int = 14) -> str:
    """Fetch sales data via scraper.py, return raw JSON string."""
    cmd = [VENV_PYTHON, "pokequant/scraper.py",
           "--card", card_name, "--days", str(days)]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=15,
    )
    return result.stdout.strip()


def format_comp(data: dict, card: str) -> str:
    """Format a comp result as a Telegram message."""
    return (
        f"*{card.upper()} -- Price Check*\n"
        f"Comp (weighted): `${data['cmc']:.2f}`\n"
        f"Simple average:  `${data['mean']:.2f}`\n"
        f"Trend: {data['trend']}\n"
        f"Volatility: {data['volatility']} | Confidence: {data['confidence']}\n"
        f"_{data['sales_used']} sales | {data['newest']} to {data['oldest']}_"
    )


async def price_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    card = " ".join(ctx.args) if ctx.args else None
    if not card:
        await update.message.reply_text("Usage: /price Charizard ex")
        return
    await update.message.reply_text(f"Looking up {card}...")
    sales_json = run_scraper(card, days=14)
    result = run_analyze(["comp", "--data", sales_json, "--card-name", card])
    if "error" in result:
        await update.message.reply_text(f"Error: {result['error']}")
        return
    await update.message.reply_text(
        format_comp(result, card), parse_mode="Markdown",
    )


async def signal_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    card = " ".join(ctx.args) if ctx.args else None
    if not card:
        await update.message.reply_text("Usage: /signal Umbreon VMAX")
        return
    await update.message.reply_text(f"Checking signal for {card}...")
    sales_json = run_scraper(card, days=30)
    result = run_analyze(["signal", "--data", sales_json, "--card-name", card])
    signal = result.get("signal", "UNKNOWN")
    emoji = {"STRONG BUY": "🟢", "BUY": "🟡", "HOLD": "⚪",
             "SELL": "🟠", "STRONG SELL": "🔴"}.get(signal, "❓")
    await update.message.reply_text(
        f"*{card.upper()}*\nSignal: {emoji} *{signal}*\n"
        f"Price: `${result.get('price', 0):.2f}` | "
        f"30d avg: `${result.get('sma30', 0):.2f}`\n"
        f"Trend: {result.get('dip_pct', 0):+.1f}% | "
        f"Volume: {result.get('vol_surge_pct', 0):+.1f}%",
        parse_mode="Markdown",
    )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("signal", signal_cmd))
    # Add /ev, /bulk, /flip handlers following the same pattern
    print("Holo bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
```

This is ~65 lines. The `/ev`, `/bulk`, and `/flip` commands follow the identical pattern: parse args, call `run_analyze()` with the right subcommand, format the dict into a Telegram message string. The full bot would be ~120-150 lines.

---

## 6. Cost Summary

| Scenario | Telegram Bot | FastAPI + Vercel (runner-up) |
|----------|-------------|----------------------------|
| **Bot/API itself** | Free (Telegram Bot API, no limits at this scale) | Free (Vercel Hobby plan) |
| **1 user, run locally** | $0 -- run `python holo_bot.py` on your Mac | $0 -- `uvicorn main:app` locally |
| **1 user, always-on** | $0-5/mo (Railway free credits or Fly.io free tier) | $0 (Vercel serverless, cold starts) |
| **10 users, always-on** | $3-5/mo on Railway (same single process serves all users via polling) | $0 (Vercel scales serverless, but SQLite cache breaks -- need external DB at ~$5/mo) |
| **Domain/SSL** | Not needed (Telegram handles delivery) | Free on Vercel (.vercel.app subdomain) |
| **Total annual (1 user)** | $0-60 | $0 |
| **Total annual (10 users)** | $36-60 | $0-60 (if external DB needed) |

The Telegram bot is effectively free for personal use and costs at most $5/month to share with a group of friends. The bot token is free, the library is free, and the only variable cost is compute hosting -- which you can avoid entirely by running locally.
