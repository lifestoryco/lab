> **Important:** Run these commands with Claude Code opened from the `holo/` project directory (the folder containing `CLAUDE.md`). All paths are relative to that root.

Analyze your bulk card inventory and tell you whether it's worth shipping to a bulk buyer yet.

Arguments: $ARGUMENTS

**Step 1 — Collect inventory counts**

If $ARGUMENTS contains numbers (e.g. "500 commons 200 uncommons"), parse them out.

Otherwise, if $ARGUMENTS is empty or unclear, ask the user:
"How many bulk cards do you have? Tell me your counts (approximate is fine):
- Commons
- Uncommons  
- Reverse Holos
- Holo Rares
- Ultra Rares (ex, V, VMAX, etc.)"

Wait for their reply and parse the numbers from their response. Be flexible — "about 500 commons" counts as 500.

**Step 2 — Run bulk analysis**
Build the command with the counts you collected. Only include flags for card types that have a count > 0.

Run: `.venv/bin/python pokequant/analyze.py bulk --commons [N] --uncommons [N] --rev-holos [N] --holo-rares [N] --ultra-rares [N]`

Capture stdout as `RESULT_JSON`.

If RESULT_JSON contains `"error"`: tell the user what went wrong in plain English.

**Step 3 — Display the result**

Use: net, gross, shipping, cards, weight_lbs, liquidate, threshold, deficit, breakdown.

Output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BULK LOT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Cards:         [cards] total
  Gross payout:  $[gross]
  Shipping:     -$[shipping]  ([weight_lbs] lbs · USPS Media Mail)
  Net profit:    $[net]

  Breakdown by type:
  [for each entry in breakdown: "  · [type]: [count] cards × $[rate] = $[subtotal]"]
```

**If liquidate = true:**
```
  ► SHIP IT ✅
  Your lot clears the $[threshold] profit threshold.
```
Then add: recommend a specific bulk buyer (e.g. Card Market, eBay bulk listing, or local game store) and remind them to weigh the package before printing a label.

**If liquidate = false:**
```
  ► Not yet — keep accumulating.
  You're $[deficit] short of the $[threshold] threshold.
```
Then tell them: "To close the gap, you'd need approximately X more commons" (calculate: deficit / 0.01 payout rate per common). Give a concrete next milestone.

Always add at the end:
```
  How we got here:
  · Gross = count × buylist rate per tier (see breakdown above)
  · Buylist rates: Common $0.01 · Uncommon $0.02 · Rev Holo $0.05 · Holo Rare $0.10 · Ultra Rare $0.50
  · Shipping = ([weight_lbs] lbs × $0.50/lb) + $2.00 packaging = $[shipping] (USPS Media Mail estimate)
  · Threshold = $[threshold] net profit minimum — below this, the effort isn't worth it
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Sources: Buylist rates based on TCGPlayer/CFB bulk averages · Shipping: USPS Media Mail calculator
```
