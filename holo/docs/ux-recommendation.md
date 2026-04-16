# Holo UX Deployment Recommendation

> Researched 2026-04-15 -- deployment path for a phone-first TCG trading assistant

---

## 1. Recommended Approach: Telegram Bot

**Winner: Telegram Bot using `python-telegram-bot` (v22+) with polling mode, hosted on Railway free tier.**

### Why Telegram wins for Holo

- **Phone-first by definition.** Telegram is a mobile app. Every trader at a show already has it. No URL to load, no browser tab to manage -- just open the chat and type `/price Charizard V`.
- **Shareable results via Inline Queries.** Telegram's [Inline Mode](https://core.telegram.org/bots/inline) lets a user type `@HoloPriceBot Umbreon VMAX` *in any chat* and share the formatted comp result directly with friends. This is the killer feature for the "share comps with friends" requirement -- no screenshots, no copy-paste. The MTG community already uses this pattern: [telegram-mtg-bot](https://github.com/ImprontaAdvance/telegram-mtg-bot) does inline card lookups for Magic: The Gathering, proving the TCG-to-Telegram fit.
- **Zero setup for the user.** Search `@HoloPriceBot` in Telegram, tap Start, done. No accounts to create, no bookmarks, no app to install (Telegram is already installed).
- **Community precedent.** The TCG trading community on Telegram is large and active. Discord is popular too, but Telegram bots can be used *across* group chats via inline queries, while Discord bots are locked to a single server.
- **Python-native, async-native.** `python-telegram-bot` v22+ is fully asyncio-based ([docs](https://docs.python-telegram-bot.org/en/stable/examples.html)), which aligns with Holo's `requests`-based scraper calls without blocking. The library supports both polling (for development) and webhooks (for production).
- **Free hosting is straightforward.** Railway's free tier provides $5/month in credits -- more than enough for a single always-on bot process with 512 MB RAM. No cold starts, no sleep timers, no HTTPS certificate management needed for polling mode. See the [Railway Telegram deploy template](https://railway.com/deploy/a0ln90) and the [free hosting guide](https://www.esubalew.dev/blog/hosting-telegram-bots-python-free).

### What ruled out the alternatives

| Option | Fatal flaw for this use case |
|--------|------------------------------|
| **Streamlit** | Mobile responsiveness is [still problematic](https://discuss.streamlit.io/t/issues-with-mobile-responsiveness/22365) -- sidebars and widgets feel clunky on a phone at a trade show. Free tier limits to 3 apps on public repos only. Apps sleep after inactivity and take 30+ seconds to wake. |
| **FastAPI + HTML** | Requires you to build a frontend. Even a single HTML file needs CSS for mobile, JavaScript for interactivity, and CORS handling. You become a full-stack developer for what should be a single-input query. |
| **Discord Bot** | Strong choice if the community is Discord-native, but bots are locked to servers -- you cannot inline-share results in a DM or a different server. Slash commands require OAuth setup and server permissions. |
| **Vercel + Next.js** | Several Pokemon price dashboards exist on Vercel ([pokemon-price-tracking.vercel.app](https://pokemon-price-tracking.vercel.app/), [pokedy.vercel.app](https://pokedy.vercel.app/), [poke-price.vercel.app](https://poke-price.vercel.app/)), but they are read-only dashboards, not interactive query tools. Building an input-driven app on Vercel means writing a Next.js frontend, which is far outside the Python-only Holo codebase. |

---

## 2. Runner-Up: Streamlit on Community Cloud

If Telegram has a deployment blocker (e.g., the user's trade group is strictly Discord-only, or Telegram is blocked on their carrier), **Streamlit** is the fallback.

- Streamlit Community Cloud is free for public repos and supports up to 3 apps ([docs](https://docs.streamlit.io/deploy/streamlit-community-cloud)).
- The entire UI can be written in ~40 lines of Python with `st.text_input`, `st.selectbox`, and `st.json`.
- A Pokemon TCG Streamlit dashboard already exists at [faurholdt/pokemon_dashboard](https://github.com/faurholdt/pokemon_dashboard/blob/main/streamlit_app.py), and the [Streamlit Inventory Tracker](https://github.com/streamlit/Inventory-Tracker) example demonstrates SQLite integration patterns.
- The mobile experience is passable but not great -- chat-style input was fixed in the [2025 releases](https://docs.streamlit.io/develop/quick-reference/release-notes/2025), but the sidebar/widget layout still feels desktop-optimized.
- Apps sleep after ~7 days of inactivity and need ~30 seconds to cold-start, which is frustrating when you need a quick price check mid-trade.

---

## 3. What Holo Needs to Expose

Holo's `analyze.py` already outputs clean JSON to stdout for five subcommands. A Telegram bot needs to call these same functions programmatically rather than via the CLI. Here is the mapping:

| Telegram Command | analyze.py Subcommand | Input | Output (for bot message) |
|-----------------|----------------------|-------|--------------------------|
| `/price <card>` | `comp` | Card name (string) | CMC, trend arrow, confidence, volatility, sales_used |
| `/signal <card>` | `signal` | Card name (string) | BUY/SELL/HOLD signal, SMA-7, SMA-30, dip %, volume surge |
| `/ev <set> <price>` | `ev` | Set name + retail price | Total EV, delta vs retail, recommendation, top card |
| `/bulk <counts>` | `bulk` | Card type counts | Net profit, should_liquidate, breakdown |
| `/flip <card> <cost> <method>` | `flip` | Card name + cost + acquisition method | Profit, margin %, verdict, fees breakdown |
| Inline: `@HoloBot <card>` | `comp` | Card name | One-line CMC summary for inline sharing |

### Required changes to analyze.py

**None for the core logic.** The five `cmd_*` functions in `analyze.py` already produce JSON dicts via `_out()`. The bot should import the underlying functions directly rather than shelling out:

- `pokequant.comps.generator.generate_comp_from_list()` -- returns a `CompResult` dataclass
- `pokequant.signals.dip_detector.latest_signal()` -- returns a `SignalResult` dataclass
- `pokequant.ev.calculator.calculate_box_ev()` -- returns a `BoxEVResult` dataclass
- `pokequant.bulk.optimizer.analyze_bulk_lot()` -- returns a `LiquidationResult` dataclass
- `cmd_flip` in `analyze.py` -- can be extracted into a standalone function that returns a dict

The scraper (`pokequant/scraper.py`) is also importable: `fetch_sales(card_name, days=14, use_cache=True)` returns a list of sale dicts ready for the comp/signal functions.

**One new addition needed:** a thin `holo_api.py` facade that wraps scraper + analysis into single-call functions like `price_check(card_name) -> dict` and `buy_sell_signal(card_name) -> dict`. This keeps the bot code clean and the core logic testable.

---

## 4. Implementation Sketch

```python
"""holo_bot.py -- Telegram bot wiring for Holo (35 lines of bot glue)"""
import json, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, InlineQueryHandler, ContextTypes

from pokequant.scraper import fetch_sales
from pokequant.comps.generator import generate_comp_from_list

TOKEN = "YOUR_BOT_TOKEN"  # Set via env var in production

async def price_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    card_name = " ".join(ctx.args) if ctx.args else None
    if not card_name:
        await update.message.reply_text("Usage: /price Charizard V")
        return
    sales = fetch_sales(card_name=card_name, days=14, use_cache=True)
    if not sales or (isinstance(sales, dict) and "error" in sales):
        await update.message.reply_text(f"No market data for '{card_name}'.")
        return
    comp = generate_comp_from_list(sales, card_id="tg", card_name=card_name)
    trend = "Rising" if comp.cmc_vs_mean_pct > 1 else "Softening" if comp.cmc_vs_mean_pct < -1 else "Stable"
    msg = (
        f"*{card_name}*\n"
        f"CMC: ${comp.cmc:.2f} ({trend} {comp.cmc_vs_mean_pct:+.1f}%)\n"
        f"Confidence: {comp.confidence} | Volatility: {comp.volatility_score}\n"
        f"Based on {comp.sales_used} sales ({comp.oldest_sale_date.date()} - {comp.newest_sale_date.date()})"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def inline_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if len(query) < 3:
        return
    sales = fetch_sales(card_name=query, days=14, use_cache=True)
    if not sales or (isinstance(sales, dict) and "error" in sales):
        return
    comp = generate_comp_from_list(sales, card_id="tg", card_name=query)
    result = InlineQueryResultArticle(
        id="1", title=f"{query}: ${comp.cmc:.2f}",
        input_message_content=InputTextMessageContent(
            f"{query} -- CMC ${comp.cmc:.2f} ({comp.confidence} confidence, {comp.sales_used} sales)"
        ),
    )
    await update.inline_query.answer([result], cache_time=300)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("price", price_check))
app.add_handler(InlineQueryHandler(inline_price))
app.run_polling()
```

This is ~45 lines. Adding `/signal`, `/ev`, `/bulk`, and `/flip` commands follows the same pattern -- import the module function, parse the Telegram args, format the result as a Markdown message.

---

## 5. Cost Analysis

### Telegram Bot on Railway

| Scale | Hosting | Telegram API | Total |
|-------|---------|-------------|-------|
| **1 active user** | Free ($5/mo credit covers it) | Free forever | **$0/month** |
| **10 active users** | Free ($5/mo credit still sufficient -- bot idles between queries) | Free forever | **$0/month** |
| **50+ active users** | ~$5-7/mo (exceeds free credit; Hobby plan at $5/mo) | Free forever | **~$5/month** |

Railway's free tier includes $5 of usage credits per month. A polling-mode Telegram bot with SQLite uses minimal CPU (~0.1 vCPU) and ~80-120 MB RAM at idle. At 10 users making ~50 queries/day total, you stay well under the free tier. Telegram's Bot API is [free and unlimited](https://core.telegram.org/bots) with no per-message charges.

Alternative free hosts: [Fly.io](https://community.fly.io/t/trying-to-launch-a-python-telegram-bot-through-fly-io/18210) offers a free allowance of 3 shared VMs; [Render](https://render.com) has a free tier but sleeps after 15 minutes of inactivity (bad for a bot that needs instant response).

### Streamlit (runner-up) on Community Cloud

| Scale | Hosting | API Calls | Total |
|-------|---------|-----------|-------|
| **1 active user** | Free (Community Cloud) | Free (PriceCharting + pokemontcg.io) | **$0/month** |
| **10 active users** | Free (but may hit resource limits / sleep issues) | Free | **$0/month** |
| **50+ active users** | Need Streamlit Teams at $250/mo or self-host on Railway/Fly | Free | **$0-250/month** |

The Streamlit free tier is genuinely free for small scale but has a hard ceiling: 3 apps, public repos only, and the app sleeps when unused. For a trade show scenario where you need instant response, the cold-start delay is a real problem that Telegram polling avoids entirely.

---

## Summary

**Ship a Telegram bot.** It is the only option that is simultaneously phone-native, zero-setup for the end user, shareable via inline queries, free to host, and writable in pure Python without touching HTML/CSS/JS. The Holo codebase already produces clean JSON from importable Python functions -- the bot is just a 50-line async wrapper that formats those results as Telegram messages.
