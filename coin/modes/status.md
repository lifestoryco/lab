# Mode: status

Show the pipeline dashboard — the daily-ritual reward surface.

## Input

- None, or optional `--lane <archetype>` filter.

## Steps

1. **Run the Rich dashboard** — this is your primary output:

   ```bash
   .venv/bin/python scripts/dashboard.py
   ```

   The dashboard prints:
   - Header: total roles, active comp floor, last-7-days comp floor
   - Status tallies across the state machine
   - Top-20 active roles (not in terminal status) sorted by fit score

2. **Narrate in one paragraph** — this is the SaaS-psych reward layer.
   Call out:
   - Biggest fit-score mover in the last 7 days (if any)
   - Any roles past the 14-day `applied` mark with no `responded` update
     (probably ghosted — suggest `no_apply` or follow-up)
   - Any `offer` or `interviewing` states — flag with 🏆/🔥

3. **Suggest a next action** based on pipeline health:
   - If < 5 active roles: "run /coin to discover more"
   - If > 3 at `scored` with fit ≥ 75: "prioritize tailoring the top 3"
   - If > 7 days since last `discover`: "time for a fresh sweep"
   - If 0 at `applied` in last 14d: "momentum low — commit to 1 today"

## Example narration

> Coin pipeline is carrying 23 active roles with a combined comp floor of
> $5.2M. Last 7 days added $1.1M in floor — mostly from two staff TPM
> postings at Acme and Globex. Your two highest-fit untailored roles are
> #42 (Staff TPM, Acme, fit 88) and #57 (Principal PM, Globex, fit 84) —
> both ghosted me on comp so I scored them conservative. Three roles have
> been at `applied` for 14+ days with no `responded` — consider marking
> `no_apply` to keep the board clean.
>
> Recommend: tailor #42 next.
