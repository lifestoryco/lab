Get the current market price for a Pokémon card using exponential decay weighting (recent sales count more).

The card name is: $ARGUMENTS

**Step 1 — Fetch sales data**
Run: `cd /Users/tealizard/Documents/lab/holo && .venv/bin/python pokequant/scraper.py --card "$ARGUMENTS" --days 14`

Capture stdout as `SALES_JSON`.

If `SALES_JSON` contains `"error"` or is empty:
- Tell the user: "Couldn't find recent sales for '$ARGUMENTS'. Check the exact spelling on PriceCharting.com."
- Stop here.

**Step 2 — Run comp analysis**
Run: `cd /Users/tealizard/Documents/lab/holo && .venv/bin/python pokequant/analyze.py comp --data 'SALES_JSON' --card-name "$ARGUMENTS"`

Capture stdout as `RESULT_JSON`.

If RESULT_JSON contains `"error"` or `"cmc": null`:
- Tell the user: "Not enough sales data to generate a reliable price comp. This card may have low trading volume."
- Stop here.

**Step 3 — Display the result**

Use: cmc, mean, delta_pct, trend, confidence, volatility, stddev, sales_used, newest, oldest.

Volatility display:
- "LOW"    → "🟢 LOW (price is stable)"
- "MEDIUM" → "🟡 MEDIUM (some movement)"
- "HIGH"   → "🔴 HIGH (price is swinging)"

Confidence display:
- "HIGH"   → "HIGH ([sales_used] sales, [days] days)"
- "MEDIUM" → "MEDIUM ([sales_used] sales)"
- "LOW"    → "LOW (thin data — treat with caution)"

Output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [CARD NAME IN CAPS] — Price Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Comp (weighted):  $[cmc]  ← list here
  Simple average:   $[mean]
  Trend:            [trend]
  Volatility:       [volatility display]
  Confidence:       [confidence display]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [newest] to [oldest] · [sales_used] raw sales
```

Then add 1-2 sentences:
- If HIGH volatility: warn that the price is unstable and they should list toward the lower end of the range to move it
- If trend is Rising: note that recent buyers paid more — they can list above the simple average
- If trend is Softening: note that recent prices are softer — list at the comp price (not the simple average) to be competitive
- If LOW volatility + HOLD signal: "This is a liquid, stable card. The comp is reliable."
