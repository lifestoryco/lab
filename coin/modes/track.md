# Mode: track

Transition a role's status in the pipeline. This is the state-machine
front door.

## Input

Natural-language or structured:

- `track 42 applied` → role 42 → `applied`
- `track 42 applied "submitted via greenhouse, portal id x39"`
- `track 42 interviewing`
- `track 42 offer "$220K base + $80K RSU/yr"`
- `track 42 rejected`
- `track 42 no_apply "comp below floor, $150K posted"`

## Steps

1. **Resolve the role.** If the user gave an ID, use it. If they
   gave "the Stripe TPM one" or similar, run:

   ```bash
   .venv/bin/python scripts/print_role.py --status scored --limit 30
   ```

   and match by company/title. If ambiguous, ask.

2. **Validate the transition.** Allowed transitions:
   - `scored → resume_generated → applied → responded → contact → interviewing → offer | rejected | withdrawn`
   - Any non-terminal state → `no_apply` or `withdrawn` (Sean can bail anytime)
   - Terminal states (`offer`, `rejected`, `withdrawn`, `no_apply`, `closed`)
     cannot transition back except `offer → closed`.

   If the transition is illegal, tell Sean why and confirm before proceeding.

3. **For `applied`: require human-in-the-loop confirmation.**
   This is the gate from "candidate" to "applicant." Ask Sean:
   > "Confirm you've submitted the application for <company> · <title>
   > (role <id>)? [y/n]"

   Only proceed on explicit `y` / `yes`. Never auto-apply.

4. **Run the update:**

   ```bash
   .venv/bin/python scripts/update_role.py --id <id> --status <status> [--note "<note>"]
   ```

5. **Celebrate transitions** (per SaaS Psych verdict). Brief visual reward:
   - `applied` → 🎯 "role applied — good luck"
   - `responded` → 📬 "recruiter responded — momentum"
   - `contact` → 📞 "phone screen scheduled"
   - `interviewing` → 🔥 "loop in progress"
   - `offer` → 🏆 "offer in hand — now negotiate"

6. **Prompt next action:**
   - After `applied` → offer to run `/coin` for more discovery
   - After `responded`/`contact` → offer to generate interview prep
     (Phase 2 — not built yet, but note it)
   - After `offer` → recommend `/alpha-squad` on the offer terms

## Multi-role

If Sean says "mark all `scored` older than 14 days as `no_apply`", you may
batch-transition after a single confirm. Never batch-apply.
