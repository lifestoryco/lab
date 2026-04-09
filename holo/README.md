# Holo 🃏

A Pokémon TCG quantitative trading terminal that runs inside **Claude Code**.

Ask it anything: *"Should I buy Charizard V right now?"* — it fetches real market data, runs the math, and gives you a plain-English verdict with exact numbers. No spreadsheets, no API keys, no manual data entry.

---

## Commands

| Command | What it does |
|---------|--------------|
| `/holo-buy-sell Charizard V` | Buy/Sell/Hold signal — 30-day trend + volume analysis |
| `/holo-price-check Umbreon VMAX` | What is this card actually worth right now |
| `/holo-box-value Obsidian Flames 149.99` | Is this sealed box worth ripping? |
| `/holo-flip "Charizard V" 4.50 pack` | Exact profit after platform fees + shipping |
| `/holo-bulk-sell` | Should you ship your bulk cards yet? |
| `/holo should I buy Charizard V?` | Ask anything in plain English |

---

## Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CHARIZARD V
  Signal: 🟢 STRONG BUY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Price today:    $36.50
  30-day average: $42.40
  Dip:            -13.9% below trend
  Volume:         +22% surge (buyers loading up)

  ► This card is temporarily depressed. Volume
    says buyers are accumulating — classic rebound
    setup. Target entry: $35–37.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Source: PriceCharting · 28 sales · 30 days
```

---

## Hey KSqueeze — Like and Subscribe Smash that notification bell skrt skrt

Just follow the four steps below and you'll have a live Pokémon card trading terminal running inside Claude Code in under five minutes.

**Open Claude Code and paste this entire message — word for word:**

---

> Hey Claude! My friend built me a Pokémon TCG trading assistant called Holo and I want to get it set up. Please follow these steps exactly:
>
> **Step 1 — Clone the repo**
> Run: `git clone https://github.com/lifestoryco/lab.git ~/Documents/lab`
>
> **Step 2 — Move into the project folder**
> Run: `cd ~/Documents/lab/holo`
>
> **Step 3 — Run the setup command**
> Run: `/holo-setup`
>
> This will automatically check your Python version, install everything needed, and confirm the live data connection is working. Tell me what it says when it's done.
>
> **Step 4 — Run your first trade check**
> Once setup is confirmed, run: `/holo-buy-sell Charizard V`
>
> That's it — you're in. From here you can check any card, any set, anytime.

---

> **Note for Claude Code:** After cloning, open the `~/Documents/lab/holo/` directory in Claude Code.
> The slash commands (`/holo-*`) appear automatically — they live in `.claude/commands/`.
> The file `CLAUDE.md` in this directory gives Claude full context on the system before you type anything.

---

## How It Works

Holo is built in two layers:

**Python layer** (deterministic math):
- Fetches real sold listings from PriceCharting.com (no API key needed)
- Runs IQR outlier filtering, 7/30-day SMA, exponential decay comp weighting
- Calculates sealed box EV using live pokemontcg.io data
- Outputs compact JSON (~150 bytes) to stdout

**Claude layer** (intelligence + UX):
- Reads the JSON and translates it into plain English
- Handles natural language input (`/holo should I buy...`)
- Adds context, narrative, and actionable recommendations
- Renders the Bloomberg-style terminal output

```
/holo-buy-sell Charizard V
        │
        ├── scraper.py fetches 30 days of PriceCharting data
        │   └── SQLite cache: second call is instant (24h TTL)
        │
        ├── analyze.py runs IQR filter → SMA-7/SMA-30 → volume surge check
        │   └── outputs: {"signal":"STRONG BUY","price":36.50,"dip_pct":-13.9,...}
        │
        └── Claude formats the verdict card + writes the plain-English "►" line
```

---

## Requirements

- Python 3.11+
- Claude Code (free or Pro)
- Internet connection (for live price data)
- No API keys, no accounts, no paid subscriptions

Dependencies installed automatically by `/holo-setup`:
`pandas` · `numpy` · `requests` · `beautifulsoup4` · `python-dateutil`

---

## Project Structure

```
holo/
├── CLAUDE.md                    ← Auto-read by Claude Code (context + command map)
├── config.py                    ← All tunable thresholds
├── requirements.txt
├── pokequant/
│   ├── scraper.py               ← Live data + SQLite cache
│   ├── analyze.py               ← Math dispatcher (signal/ev/bulk/comp/flip)
│   ├── signals/dip_detector.py  ← SMA + volume signal engine
│   ├── ev/calculator.py         ← Sealed box EV
│   ├── comps/generator.py       ← Decay-weighted comp + volatility
│   ├── bulk/optimizer.py        ← Bulk liquidation optimizer
│   └── ingestion/normalizer.py  ← IQR outlier filtering
└── .claude/commands/
    ├── holo.md                  ← /holo (natural language)
    ├── holo-buy-sell.md         ← /holo-buy-sell
    ├── holo-price-check.md      ← /holo-price-check
    ├── holo-box-value.md        ← /holo-box-value
    ├── holo-flip.md             ← /holo-flip
    ├── holo-bulk-sell.md        ← /holo-bulk-sell
    └── holo-setup.md            ← /holo-setup
```

---

## Data Sources

| Source | Used For | Auth Required |
|--------|----------|---------------|
| PriceCharting.com | Historical sold listings (signal, comp, flip) | None |
| pokemontcg.io | Card database + market prices (box EV) | None |

---

Built with Claude Code · [@lifestoryco](https://github.com/lifestoryco)
