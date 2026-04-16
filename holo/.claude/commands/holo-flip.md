> **Important:** Run these commands with Claude Code opened from the `holo/` project directory (the folder containing `CLAUDE.md`). All paths are relative to that root.

Calculate your exact profit if you sell a card right now, after platform fees and shipping.

Arguments: $ARGUMENTS
Usage: /holo-flip [Card Name] [Cost Basis] [Method: single/pack/box]
Example: /holo-flip "Charizard V" 4.50 pack

**Step 1 — Parse the arguments**

From $ARGUMENTS, extract:
- Card name (quoted string, or everything before the number)
- Cost basis (a dollar amount — what they paid)
- Method (one of: single, pack, box)

If any argument is missing, ask the user:
"Quick questions before I run the numbers:
1. What's the card name?
2. How much did you pay for it? (Your cost)
3. How did you get it — as a single, in a pack, or out of a whole box?"

Wait for their response, then parse all three values before continuing.

**Step 2 — Run the flip analysis**
Run: `.venv/bin/python pokequant/analyze.py flip --card '[CARD NAME]' --cost [COST] --method [METHOD]`
(Single-quote the card name. If it contains a literal `'`, escape it as `'\''`.)

Capture stdout as `RESULT_JSON`.

If RESULT_JSON contains `"error"`:
- Tell the user in plain English what went wrong (bad card name, data unavailable, etc.)
- Stop here.

**Step 3 — Display the result**

Use these values from RESULT_JSON:
card, method_label, cmc, cost_basis, platform_fee, platform_fee_pct,
shipping_cost, shipping_type, net_revenue, profit, margin_pct,
verdict, verdict_emoji, method_note, comp_confidence, comp_sales_used,
insufficient_data_warning

Format the profit line:
- profit > 0 → "+$[profit] (+[margin_pct]% Margin)"
- profit ≤ 0 → "-$[abs(profit)] (LOSS)"

Output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [CARD NAME IN CAPS] — Flip Profit Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Acquired via:  [method_label]
  Current Comp:  $[cmc]
  Your Cost:    -$[cost_basis]
  Fees (13%):   -$[platform_fee]
  Shipping:     -$[shipping_cost] ([shipping_type])
  ─────────────────────────────────────
  Net Profit:    [profit line]

  ► VERDICT: [verdict_emoji] [verdict]
  [method_note — only show if non-empty, on its own line]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Comp: [comp_confidence] confidence · [comp_sales_used] sales · PriceCharting
  [If insufficient_data_warning is non-empty: "⚠  " + insufficient_data_warning]
```

**Step 4 — Add a plain-English action item (1-2 sentences)**

For 🟢 FLIP IT:
- Tell them how to list it (eBay vs TCGPlayer recommendation based on price point: TCGPlayer for <$50, eBay for >$50), and suggest listing at or just below the comp to move it fast.

For 🟡 HOLD:
- Tell them what the card would need to reach for the flip to be worth it (back-calculate: what comp price gives them 20%+ margin). Example: "This card needs to hit $X before selling makes sense."

For 🔴 DO NOT SELL:
- Tell them clearly: hold the card, and at what price the math turns profitable.
