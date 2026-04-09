Calculate the Expected Value (EV) of a sealed Pokémon booster box.

Usage: /holo-box-value [Set Name] [retail price]
Example: /holo-box-value Obsidian Flames 149.99

The arguments are: $ARGUMENTS

**Step 1 — Parse the arguments**
The last token in $ARGUMENTS that looks like a number is the retail price.
Everything before it is the set name.

Examples:
- "Obsidian Flames 149.99" → set="Obsidian Flames", retail=149.99
- "Surging Sparks 159" → set="Surging Sparks", retail=159.00
- "151 89.99" → set="151", retail=89.99

If no price is found in $ARGUMENTS, ask: "What did you pay for the box?"
Wait for their answer before continuing.

**Step 2 — Run EV analysis**
Run: `cd /Users/tealizard/Documents/lab/holo && .venv/bin/python pokequant/analyze.py ev --set "[SET NAME]" --retail [RETAIL]`

Capture stdout as `RESULT_JSON`.

If RESULT_JSON contains `"error"`:
- Extract the error message and tell the user in plain English.
- Suggest checking the set name spelling (e.g. "Obsidian Flames" not "obsidian flames").
- Stop here.

**Step 3 — Display the result**

Use: set, ev, retail, delta, delta_pct, rec, top_card, top_card_value, tiers_analyzed.

Choose the recommendation color language:
- "Positive EV: Rip for Singles" → use enthusiastic language ("this box pays for itself")
- "Borderline: Context-Dependent" → use cautious language ("close call")
- "Negative EV: Hold Sealed" → use clear "hold" language

Output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [SET NAME IN CAPS] — Box Value
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Expected value: $[ev]
  You paid:       $[retail]
  Gap:            [delta > 0 ? "+$delta (you're up!)" : "-$delta ([delta_pct]% underwater)"]

  ► [rec]

  Best pull:  [top_card] @ ~$[top_card_value] avg
  Analysis:   Top [tiers_analyzed] rarity tiers · live prices via pokemontcg.io
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then add 2-3 sentences of plain-English context:
- For "Rip": which pull(s) make it worth it and roughly how often you'd hit them
- For "Borderline": what would need to change (price drop or card spike) to make it worth ripping  
- For "Hold": how much the market would need to move before it becomes EV-positive
