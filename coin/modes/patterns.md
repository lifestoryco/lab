# Mode: patterns

Analyze rejection clusters and silent-reject patterns to find systemic issues in Sean's applications. Outputs a verdict on what to change before the next batch of tailoring.

## Input

- (none) — analyze all roles in `rejected` + 21d-stale `applied` state
- `--lane <name>` — focus on one lane
- `--since <YYYY-MM-DD>` — restrict to recent applications

## Step 1 — Pull the dataset

```python
.venv/bin/python -c "
import sys, sqlite3, json
from datetime import datetime, timedelta
sys.path.insert(0, '.')
conn = sqlite3.connect('data/db/pipeline.db')
conn.row_factory = sqlite3.Row
# Rejected + silent rejects (applied >21d, no movement)
cutoff = (datetime.now() - timedelta(days=21)).isoformat()
rows = conn.execute('''
    SELECT id, lane, company, title, location, fit_score, status, notes, jd_parsed
    FROM roles
    WHERE status='rejected' OR (status='applied' AND updated_at < ?)
    ORDER BY lane, fit_score DESC
''', (cutoff,)).fetchall()
print(f'Pattern dataset: {len(rows)} roles')
for r in rows[:30]:
    print(f\"  {r['id']:4d}  {r['lane']:28s}  {r['fit_score'] or 0:5.1f}  {r['status']:10s}  {r['company'][:25]:25s}  {r['title'][:40]}\")
"
```

## Step 2 — Cluster by lane × company-tier × fit-grade

Build a pivot:
- Rows: lane (mid-market-tpm, enterprise-sales-engineer, iot-solutions-architect, revenue-ops-operator)
- Columns: company tier (in-league mid-market, recognized brand, unknown small, FAANG-pedigree-filtered)
- Values: count of rejected / silent-rejected, plus mean fit_score

Look for hot spots:
- **Lane × tier with disproportionate rejection rate** → that combo is broken (maybe the lane positioning isn't landing for that tier of company)
- **High-fit-grade roles still getting rejected** → resume content is wrong even when the match looks right
- **All rejections in one lane** → that lane may be wrong-fit entirely (kill the lane)

## Step 3 — Read sample rejected JDs vs Sean's tailored JSONs

For each cluster of 3+ rejections:
1. Read 3 representative `jd_raw` entries
2. Read the corresponding tailored JSONs from `data/resumes/generated/`
3. Compare:
   - Did the JDs share a required skill that's NOT in `PROFILE.skills`?
   - Did the JDs share a seniority level (Staff, Principal) that triggered Sean's pedigree filter?
   - Did the tailored bullets repeat the same proof points (Cox, TitanX) and miss something the JDs were asking for?

## Step 4 — Output a pattern report

```
═══════════════════════════════════════════════════════════════
  PATTERN ANALYSIS — N rejected/silent roles
  Window: <since>  ·  Lanes: <filter or "all 4">
═══════════════════════════════════════════════════════════════

CLUSTERS (≥3 rejections):

  1. Lane: enterprise-sales-engineer × Tier: FAANG-pedigree
     Count: 5  ·  Mean fit: 70  ·  Status: 4 rejected, 1 silent
     Hypothesis: pedigree filter triggers despite high comp+skill match.
                 We should be marking these out_of_band more aggressively.
     Action: extend COMPANY_TIERS["tier4_pedigree_filter"] to include <X>

  2. Lane: mid-market-tpm × Tier: in-league
     Count: 4  ·  Mean fit: 78  ·  Status: 4 silent
     Hypothesis: bullets too generic — Cox/TitanX same in every JSON,
                 not enough JD-specific tailoring.
     Action: revisit tailor.md Step 5 voice rules; consider per-bullet
             JD-keyword density target.

SYSTEMIC SIGNALS:

  · 7 of 12 rejections come within 48h of apply → ATS auto-screen
    (likely keyword filter); strengthen skills_matched section.
  · Only 1 lane (revenue-ops-operator) has zero responses
    → consider deprioritizing that lane until we have a real proof
       point beyond the Utah Broadband acquisition narrative.

RECOMMENDATIONS (ranked by leverage):

  1. <action with file path>
  2. <action with file path>
  3. <action with file path>
```

## Step 5 — Suggested follow-up actions

End with concrete next steps:
- "Update `config.py` COMPANY_TIERS to add: <list>"
- "Edit `tailor.md` Step 5 to add: <rule>"
- "Run `/coin discover --lane <healthy lane>` to refill pipeline; defer `<weak lane>` until we have new proof"
- "Open `COIN-LANE-<weak>-RETIRE` task to consolidate"

## Hard rules

- Never propose changes to PROFILE.positions metrics based on rejection patterns — those are factual about Sean's history, not adjustable.
- Never recommend lying to fix a rejection cluster (e.g., "claim a CS degree because all rejections required one"). The truthfulness gates outweigh any pattern.
- Never auto-edit config.py / tailor.md / SKILL.md — surface recommendations only; Sean approves.

## Notes

- Reference: santifer/career-ops `modes/patterns.md` for the cluster taxonomy.
- Re-run after every batch of 10+ applications. More data = sharper hypotheses.
- Pair with `/coin status` to see overall pipeline health.
