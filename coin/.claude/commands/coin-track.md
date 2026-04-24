---
description: View and update the application pipeline. Shows all tracked roles, their status, and compensation data in a Bloomberg-style dashboard.
---

# /coin-track [--status STATUS] [--update ROLE_ID STATUS]

**Usage:**
- `/coin-track` — full pipeline dashboard
- `/coin-track --status applied` — filter by status
- `/coin-track --update 42 interviewing` — update role #42 status

**Statuses:** `discovered` → `resume_generated` → `applied` → `screening` → `interviewing` → `offer` → `closed`

---

## Steps

### View mode (default)
```bash
.venv/bin/python -c "
from careerops.pipeline import dashboard
print(dashboard())
"
```

### Update mode (`--update ROLE_ID STATUS`)
```bash
.venv/bin/python -c "
from careerops.pipeline import update_status
update_status($ROLE_ID, '$STATUS')
print('Updated #$ROLE_ID → $STATUS')
"
```

---

## Output format (view mode)

```
═══════════════════════════════════════════════
  Coin Pipeline — {date}
  Active: {n} | Applied: {n} | Offers: {n}
═══════════════════════════════════════════════

ACTIVE ROLES
─────────────────────────────────────────────
ID  Status           Company              Title                    Comp
42  resume_generated Stripe               Senior TPM — Payments    $220K–$280K + RSU
38  applied          Snowflake            Technical Sales Engineer  $200K–$260K + RSU
29  screening        Databricks           Group PM — AI Platform   $240K–$320K + RSU

OFFERS / CLOSED
─────────────────────────────────────────────
{any offers or closed roles}

COMPENSATION SUMMARY
─────────────────────────────────────────────
Avg base (active):  ${avg}K
Highest comp seen:  ${max}K + RSU @ {company}
Roles above $200K:  {n}

─────────────────────────────────────────────
/coin-apply {id} | /coin-track --update {id} {status}
```
