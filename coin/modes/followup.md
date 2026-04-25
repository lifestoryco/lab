# Mode: followup

Find applications that are stale (submitted but no recruiter response) and either flag them for action or draft a follow-up message.

## Input

- (none) — sweep all `applied` roles older than the cadence threshold
- `--id <role_id>` — focus on one role
- `--days <n>` — override default cadence (default: 7 days for first follow-up, 14 for second)

## Step 1 — Identify stale applications

```python
.venv/bin/python -c "
import sys, sqlite3
from datetime import datetime, timedelta
sys.path.insert(0, '.')
conn = sqlite3.connect('data/db/pipeline.db')
conn.row_factory = sqlite3.Row
cutoff = (datetime.now() - timedelta(days=7)).isoformat()
rows = conn.execute('''
    SELECT id, company, title, location, updated_at, notes
    FROM roles
    WHERE status='applied' AND updated_at < ?
    ORDER BY updated_at ASC
''', (cutoff,)).fetchall()
for r in rows:
    days = (datetime.now() - datetime.fromisoformat(r['updated_at'])).days
    print(f\"{r['id']:4d}  {days:3d}d  {r['company']:25s}  {r['title'][:50]}\")
"
```

## Step 2 — Categorize each stale role

| Days since `applied` | Category | Recommendation |
|---|---|---|
| 7–10 | **First follow-up window** | Draft a polite check-in email or LinkedIn DM to the recruiter / hiring manager |
| 11–20 | **Second follow-up window** | Draft a value-add reply: "I saw <relevant news about company>, here's how my <proof point> connects" |
| 21+ | **Likely silent reject** | Mark `closed` with note "no response after 21d"; recommend running `/coin patterns` to look for systemic issues |

## Step 3 — Draft outreach (when requested)

For each role Sean wants to follow up on:

1. Read the role's `jd_raw` and `notes` (any contact name captured during apply?)
2. Read `data/resumes/generated/<id:04d>_*.json` — pull the `cover_letter_hook` for tone and the `top_bullets[0]` for the primary proof point
3. Draft a 3-4 sentence message:
   - Sentence 1: Reference the application date and role title (specific, not "checking in")
   - Sentence 2: Add ONE new proof point or relevant context not in the original application
   - Sentence 3: Soft ask — "Would you have 15 minutes to discuss the role?" or "Happy to provide more context if helpful"
   - Sentence 4 (optional): Short closer with availability
4. Surface the draft to Sean for review. **Never auto-send.** Sean copies + sends from his own inbox or LinkedIn.

## Step 4 — Update notes

After Sean confirms a follow-up was sent, update the role's notes:
```python
.venv/bin/python -c "
import sqlite3
sqlite3.connect('data/db/pipeline.db').execute(
    'UPDATE roles SET notes=COALESCE(notes,\"\") || ? WHERE id=?',
    (f'\\nfollowup-{date}: sent', role_id)
).connection.commit()
"
```

## Step 5 — Recommend close-outs

For roles in the 21+ window with no response, ask Sean:
> "Role <id> at <company> — applied <X> days ago, no response. Mark closed? (yes/no)"

If yes, transition: `update_status(role_id, 'closed', note='no_response_after_21d')`. Useful pattern data for `/coin patterns`.

## Hard rules

- Never auto-send a follow-up. Drafts only. Sean controls outbound.
- Never close a role without explicit confirmation.
- Never follow up on a role in `out_of_band` (it shouldn't have been applied in the first place — if it was, that's a separate conversation).

## Notes

- Default cadence (7d / 14d / 21d) follows industry norm for senior IC / Director roles. Adjust per company size — small startups often respond inside 5d; large corps frequently take 21d+ to even acknowledge receipt.
- If the role's `notes` field captured a recruiter name from the apply step (rare but ideal), address them by name in the draft. Otherwise, "Hi <Company> hiring team," is fine.
- Reference: santifer/career-ops `modes/followup.md` for the cadence rationale and message structure.
