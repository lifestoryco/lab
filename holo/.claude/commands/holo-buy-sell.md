> **Important:** Run these commands with Claude Code opened from the `holo/` project directory (the folder containing `CLAUDE.md`). All paths are relative to that root.

Get a Buy / Sell / Hold trading signal for a Pokémon card.

The card name is: $ARGUMENTS

**Step 1 — Fetch sales data**
Run: `.venv/bin/python pokequant/scraper.py --card '$ARGUMENTS' --days 30`
(Single-quote the card name. If $ARGUMENTS contains a literal `'`, escape it as `'\''`.)

Capture the full stdout as `SALES_JSON`.

If `SALES_JSON` contains `"error"` or is an empty array:
- Tell the user: "I couldn't find recent sales data for '$ARGUMENTS'. Check the spelling — try the exact name as it appears on PriceCharting.com (e.g. 'Charizard V', 'Umbreon VMAX', 'Pikachu ex')."
- Stop here.

**Step 2 — Run signal analysis**
Run: `.venv/bin/python pokequant/analyze.py signal --data 'SALES_JSON' --card-name '$ARGUMENTS'`
(Single-quote the card name. If $ARGUMENTS contains a literal `'`, escape it as `'\''`.)

Capture stdout as `RESULT_JSON`. Parse it.

If `RESULT_JSON` contains `"signal": "UNKNOWN"` or `"error"`:
- Tell the user: "Not enough sales data to generate a reliable signal for this card. It may be illiquid — try again in a few days."
- Stop here.

**Step 3 — Display the result**

Use these values from RESULT_JSON: signal, price, sma30, dip_pct, vol_surge_pct, as_of.

Choose the signal emoji:
- "STRONG BUY" → 🟢
- "BUY" → 🟡  
- "HOLD" → ⚪
- "SELL" → 🟠
- "STRONG SELL" → 🔴

Format the dip_pct line:
- Negative dip_pct → "X% below trend (potential dip)"
- Positive dip_pct → "X% above trend (elevated)"

Format the volume line:
- vol_surge_pct > 20 → "+X% surge (buyers loading up)"
- vol_surge_pct between -10 and 20 → "Normal"
- vol_surge_pct < -10 → "X% below average (quiet market)"

Output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [CARD NAME IN CAPS]
  Signal: [EMOJI] [SIGNAL]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Price today:    $[price]
  30-day average: $[sma30]
  Trend:          [dip_pct line]
  Volume:         [volume line]

  ► [Write 2-3 sentences in plain English:
     What does this signal mean for a trader?
     What specific action should they consider?
     Give a suggested entry price range for BUY signals,
     or a suggested exit range for SELL signals.
     Be direct — no hedging, no "it depends".]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Source: PriceCharting · [sales_count] sales · 30 days · [as_of]
```
