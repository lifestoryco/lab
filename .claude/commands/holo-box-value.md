> **Important:** Run these commands with Claude Code opened from the `holo/` project directory (the folder containing `CLAUDE.md`). All paths are relative to that root.

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
Run: `.venv/bin/python pokequant/analyze.py ev --set '[SET NAME]' --retail [RETAIL]`
(Single-quote the set name. If it contains a literal `'`, escape it as `'\''`.)

Capture stdout as `RESULT_JSON`.

If RESULT_JSON contains `"error"`:
- Extract the error message and tell the user in plain English.
- Suggest checking the set name spelling (e.g. "Obsidian Flames" not "obsidian flames").
- Stop here.

**Step 3 — Display the result**

Use: set, ev, retail, delta, delta_pct, rec, top_card, top_card_value, tiers_analyzed, cards_sampled, sources.

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

  [2-3 sentences:
   - For "Rip": which pull(s) make it worth it and roughly how often you'd hit them
   - For "Borderline": what would need to change to make it EV-positive
   - For "Hold": how much the market would need to move before it's worth ripping]

  How we got here:
  · EV = Σ (pull_rate × avg_card_value) × packs_per_box, across top [tiers_analyzed] rarity tiers
  · Pull rates from official set data: SIR=1/36 packs · IR=1/18 · UR=1/6 · Double Rare=1/4
  · Card values = live TCGPlayer market prices pulled from [cards_sampled] cards in the set
  · Best pull: [top_card] averaging $[top_card_value] — this tier drives the EV number
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Top [tiers_analyzed] rarity tiers · [cards_sampled] cards sampled
  Sources: [for each entry in RESULT_JSON.sources, render as "[label] ([count] cards)" hyperlinked to the url, separated by " · "]
```
