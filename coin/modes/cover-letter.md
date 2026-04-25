# Coin Mode — `cover-letter` (standalone cover letter generation)

> Load `modes/_shared.md` first.

**Purpose:** Generate a 3-paragraph cover letter (hook → proof → fit) and
render a standalone PDF. Distinct from `modes/tailor.md` so resume + cover
letter can each have the right voice (resume = past-tense bullet; letter =
present-tense narrative).

Port of the `proficiently` skill collection's cover-letter pattern.

---

## Hard refusals (read first)

| Refusal | Why |
|---|---|
| Generating a cover letter without a tailored resume JSON in place | Stories must match resume — sequence enforced |
| Citing a metric not in `data/resumes/base.py` PROFILE.positions | Truthfulness gate (`_shared.md` Operating Principle #3) |
| Claiming Cox/TitanX/Safeguard outcomes as Sean's direct employment | Truthfulness gate — Sean was Hydrant's PM/COO on those |
| Writing "I am writing to apply for..." style filler | Burns the first sentence of attention |
| Exceeding 280 words across hook + proof + fit | ATS reviewers skim — long letters hurt |
| Auto-attaching to an apply session without `audit_passes: true` in JSON | Hard gate — render refuses unless audit passes |
| Claiming a CS / engineering degree | Sean has BA History + MBA WGU + PMP, not CS |

---

## Step 1 — Load context

Pull these into working memory before drafting:

```bash
.venv/bin/python scripts/print_role.py --id <id>     # role + parsed JD + fit
ls data/resumes/generated/<id:04d>_*.json            # tailored resume must exist
```

Also load:
- `data/resumes/base.py` PROFILE (positions, education, skills)
- `config/profile.yml` for the archetype's voice + North Star pitch
- The tailored resume JSON's `stories_used` (we MUST match this list)

If no tailored resume JSON exists for the role, STOP — print:

> *"Cover letter requires a tailored resume first. Run `/coin tailor <id>` then re-run `/coin cover-letter <id>`."*

---

## Step 2 — Truthfulness gate (mandatory before drafting)

Re-read `_shared.md` Operating Principle #3. Specifically check:

- Cox / TitanX / Safeguard outcomes → Sean was Hydrant's PM/COO/lead, not the client's employee
- No "Fortune 500" / "seven-figure" / "world-class" without a verifiable named account
- No CS / engineering degree
- Every metric must trace to `PROFILE.positions[*].achievements`

If any of the planned proof points violate these gates, swap them for verified ones BEFORE writing prose.

---

## Step 3 — Draft 3 paragraphs

### Hook (≤ 80 words)

Lead with the archetype's North Star pitch (from `config/profile.yml`),
immediately tied to the JD's stated initiative.

**Bad opener (refused):** *"I am writing to apply for the Senior TPM role at <Company>..."*

**Good shape:**
> *"<Company> is scaling <stated initiative from JD §1>. That's the problem I solved at Hydrant — <one specific outcome with metric from PROFILE>. I'm a TPM by trade, MBA by training, PMP by certification — and I'd rather build <archetype-relevant thing> than manage status decks."*

### Proof (≤ 130 words)

Pick the SAME 2 lead stories already in the tailored resume JSON's
`stories_used`. Re-narrate in present-tense narrative voice (NOT bullet voice).

Each story must:
1. Open with the named engagement (Cox True Local Labs / Utah Broadband / TitanX) AND Sean's actual role on it (Hydrant PM / Enterprise AM / fractional COO — never claim direct employment at the named client when Sean wasn't)
2. Land on the metric (already verified in PROFILE)
3. Bridge to the JD's stated requirement explicitly — cite a JD keyword by name

### Fit (≤ 70 words)

Two sentences:

1. **Locations / remote match** — drawn from JD's location field + `config/profile.yml` `target_locations`.
2. **Honest gap acknowledgment** — name the strongest gap and how Sean closes it. Example: *"I don't have a CS degree; I close that with PMP rigor and 15 years of wireless / IoT delivery from Utah Broadband and CA Engineering."* Honesty is differentiating.

### Word budget

Hard cap: **280 words total** across hook + proof + fit. If draft goes over, cut the proof paragraph first.

---

## Step 4 — Persist as JSON

Write to `data/resumes/generated/<id:04d>_<lane>_<date>_cover.json`:

```json
{
  "role_id": 137,
  "company": "Filevine",
  "title": "Senior Solutions Engineer",
  "lane": "enterprise-sales-engineer",
  "recipient_name": null,
  "today": "2026-04-25",
  "paragraphs": {
    "hook": "...",
    "proof": "...",
    "fit": "..."
  },
  "stories_used": ["utah_broadband_acquisition", "cox_true_local_labs"],
  "jd_keywords_cited": ["enterprise SaaS", "IoT integration", "pre-sales"],
  "word_count": 247,
  "audit_passes": false,
  "generated_at": "2026-04-25T..."
}
```

**Parity checks before write:**

- `stories_used` MUST be a subset of the tailored resume JSON's `stories_used` (load that JSON, compare). If not, STOP.
- `jd_keywords_cited` MUST each appear as substrings of the parsed JD's keyword list. If any don't, STOP.
- `word_count` MUST be ≤ 280. If not, redraft.

`audit_passes: false` until Step 5 confirms.

---

## Step 5 — Audit hand-off

Run a stripped-down audit pass on the cover JSON. Reuse `modes/audit.md`'s
five CRITICAL truthfulness checks (numbering matches audit.md exactly —
skip Checks 6–9 which are orthogonality / domain-overreach / lane-specific
and don't apply to a single-page letter):

1. **Check 1 — Education truthfulness** — no CS / engineering degree claims; BA History + MBA WGU + PMP only
2. **Check 2 — Pedigree non-claim** — no Fortune 500 / seven-figure / world-class qualifiers without a verifiable named account
3. **Check 3 — Cox/TitanX/Safeguard attribution** — frame as Hydrant engagements (PM/COO/lead), not Sean-as-direct-employee
4. **Check 4 — Vague-flex qualifiers** — no "spearheaded multi-billion", "hypergrowth", "mission-critical" without a real anchor; verbs stay honest
5. **Check 5 — Metric provenance** — every numeric claim traces to a PROFILE.positions[*].achievements line

If all pass, set `audit_passes: true` in the JSON and rewrite the file.
If any fail, print the failures, leave `audit_passes: false`, and STOP — do NOT proceed to render.

---

## Step 6 — Render PDF

```bash
.venv/bin/python scripts/render_cover_letter.py --role-id <id>
```

The renderer enforces `audit_passes: true` — it will refuse to render otherwise.

Confirm output PDF size > 4KB (sanity check).

---

## Step 7 — Output summary

```
═══════════════════════════════════════════════
  Cover Letter — Role <id>
  <company> · <title>
═══════════════════════════════════════════════

Stories used (parity with resume): cox_true_local_labs, utah_broadband_acquisition
JD keywords cited: enterprise SaaS, IoT integration, pre-sales
Audit: ✅ 5/5 truthfulness checks pass
Length: 247 words / 280 max

Files:
  → data/resumes/generated/<id:04d>_<lane>_<date>_cover.json
  → data/resumes/generated/<id:04d>_<lane>_<date>_cover.pdf

NEXT
  → Review the PDF
  → Edit the JSON if needed → re-render: scripts/render_cover_letter.py --role-id <id>
  → Then: /coin apply <id>   (cover letter will auto-attach if available)
```

---

## Auto-pipeline integration

`modes/auto-pipeline.md` Step 6 (Render) calls `cover-letter <id>` AFTER the
audit-on-resume passes, BEFORE reporting. If cover-letter audit fails, the
auto-pipeline still ships the resume PDFs (cover letter is an enhancement,
not a blocker).

## Apply mode integration

`modes/apply.md`:
- **Greenhouse field 6 (Cover Letter file upload)** — uses the cover PDF if it
  exists at the conventional path. (Field 5 is Resume/CV; field 6 is the
  cover slot.)
- **Lever field 10 (Additional Information textarea)** — pastes the
  `paragraphs.hook` value (NOT the whole letter — the textarea is a hook
  field; the cover PDF goes via field 1's resume slot if Lever exposes a
  separate cover upload).

---

## Reference

| File | Purpose |
|---|---|
| `data/cover_letter_template.html` | Jinja2 template with autoescape |
| `scripts/render_cover_letter.py` | Renderer; refuses on `audit_passes: false` |
| `config.COVER_TEMPLATE_PATH` | Template path (mirrors RECRUITER_TEMPLATE_PATH) |
