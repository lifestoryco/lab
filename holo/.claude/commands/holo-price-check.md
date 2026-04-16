> **Important:** Run these commands with Claude Code opened from the `holo/` project directory (the folder containing `CLAUDE.md`). All paths are relative to that root.

Get the current market price for a Pokémon card using exponential decay weighting (recent sales count more).

The card name is: $ARGUMENTS

**Step 1 — Fetch sales data**
Run: `.venv/bin/python pokequant/scraper.py --card '$ARGUMENTS' --days 14`
(Single-quote the card name. If $ARGUMENTS contains a literal `'`, escape it as `'\''`.)

Capture stdout as `SALES_JSON`.

If `SALES_JSON` contains `"error"` or is empty:
- Tell the user: "Couldn't find recent sales for '$ARGUMENTS'. Check the exact spelling on PriceCharting.com."
- Stop here.

**Step 2 — Run comp analysis**
Run: `.venv/bin/python pokequant/analyze.py comp --data 'SALES_JSON' --card-name '$ARGUMENTS'`
(Single-quote the card name. If $ARGUMENTS contains a literal `'`, escape it as `'\''`.)

Capture stdout as `RESULT_JSON`.

If RESULT_JSON contains `"error"` or `"cmc": null`:
- Tell the user: "Not enough sales data to generate a reliable price comp. This card may have low trading volume."
- Stop here.

**Step 3 — Display the result**

Use: cmc, mean, delta_pct, trend, confidence, volatility, stddev, sales_used, newest, oldest, insufficient_data_warning, sources.

If `insufficient_data_warning` is non-empty, display it prominently right below the confidence line:
```
  Confidence:       [confidence display]
  ⚠  [insufficient_data_warning]
```

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

  [1-2 sentences of context:
   - HIGH volatility: warn price is unstable, list toward lower end to move it
   - Rising trend: recent buyers paid more — can list above simple average
   - Softening trend: recent prices softer — list at comp price, not simple average
   - LOW volatility + stable: "This is a liquid, stable card. The comp is reliable."]

  How we got here:
  · Comp = exponential decay-weighted average — sales from today count ~3× more than
    sales from 7 days ago (decay λ=0.3), so the comp tracks recent market movement
  · Simple avg = unweighted mean of all [sales_used] sales ([newest] → [oldest])
  · Trend = comp vs. simple avg: positive means recent buyers paid more ([delta_pct]%)
  · Volatility = std dev $[stddev] / mean — reflects how much prices bounce around
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [newest] to [oldest] · [sales_used] sales
  Sources: [for each entry in RESULT_JSON.sources, render as "[label] ([count])" hyperlinked to the url if url is non-empty, separated by " · "]
```
