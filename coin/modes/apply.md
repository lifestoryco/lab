# Mode: apply

Browser-assisted ATS form pre-fill. Opens the role's apply URL, detects the ATS provider, fills every field it safely can from `data/resumes/base.py` PROFILE + the tailored JSON, then **stops at the Submit button** for Sean to review and click.

This mode never auto-submits and never auto-transitions a role to `applied` — those are real-world commitments that only Sean can make.

## Input

- `--id <role_id>` (required) — the role to apply to. Must have status `resume_generated` and a `_recruiter.pdf` artifact.

## Pre-conditions

Before doing anything, verify:

1. Role exists and has status >= `resume_generated`:
   ```bash
   .venv/bin/python scripts/print_role.py --id <id>
   ```
2. Recruiter PDF exists:
   ```bash
   ls data/resumes/generated/<id:04d>_*_recruiter.pdf
   ```
   If missing, refuse: *"No recruiter PDF for role <id>. Run `/coin pdf <id> --recruiter` first."*
3. Browser MCP tool is available (Claude in Chrome OR Claude Preview). Prefer Claude in Chrome — Preview has CSP restrictions on real ATS sites.

## Step 1 — ATS detection

Detect ATS from the role's `url` field:

| URL substring | ATS |
|---|---|
| `greenhouse.io`, `boards.greenhouse.io`, `job-boards.greenhouse.io` | `greenhouse` |
| `jobs.lever.co` | `lever` |
| `myworkdayjobs.com` (or `*.wd*.myworkdayjobs.com`) | `workday` |
| `ashbyhq.com` | `ashby` (best-effort, no reference) |
| `linkedin.com/jobs/view` | `linkedin` (Easy Apply — see Step 6) |
| anything else | `unknown` (see Step 4) |

After detection, load the corresponding section from `.claude/skills/coin/references/ats-patterns.md` into context.

## Step 2 — Open the apply URL

Use the browser MCP tool to navigate. Per-ATS specifics:

**Greenhouse:**
1. Navigate to the posting URL
2. Extract iframe tokens via `javascript_tool`:
   ```javascript
   const iframe = document.getElementById('grnhse_iframe');
   const url = new URL(iframe.src);
   JSON.stringify({
     boardToken: url.searchParams.get('for'),
     jobToken: url.searchParams.get('token')
   });
   ```
3. Build direct form URL: `https://job-boards.greenhouse.io/embed/job_app?for={boardToken}&token={jobToken}`
4. Navigate to that URL — now `read_page` and `form_input` work normally

**Lever:**
- Append `/apply` to the posting URL OR click "APPLY FOR THIS JOB"
- `read_page` and `form_input` work directly — most automation-friendly ATS

**Workday:**
- Append `/applyManually` to the apply URL (NOT `/autofillWithResume` — Workday's resume parser often misreads our PDF and creates duplicate work)
- If page requires sign-in (likely), STOP and tell Sean:
  > "Workday requires account creation/sign-in before form fields are accessible. Sign in manually, then say 'continue' and I'll resume."
- Wait for Sean's "continue" before proceeding

**Ashby / unknown:** Open URL and proceed to Step 4.

## Step 3 — Per-ATS field-fill flows

Fill in the documented order. For every field, follow the protocol in Step 5.

### Greenhouse field order

| # | Field | Source |
|---|---|---|
| 1 | First Name | `PROFILE.name.split()[0]` |
| 2 | Last Name | `PROFILE.name.split()[-1]` |
| 3 | Email | `PROFILE.email` (use `sean@lifestory.co` for job search, NOT employer email) |
| 4 | Phone | `PROFILE.phone` |
| 5 | Resume/CV (file upload) | `data/resumes/generated/<id:04d>_*_recruiter.pdf` |
| 6 | Cover Letter (file upload) | Upload `data/resumes/generated/<id:04d>_*_cover.pdf` if it exists; else skip. Produced by `/coin cover-letter <id>` or auto-pipeline. |
| 7 | Location (City) | `PROFILE.city` (city only, no state) |
| 8 | Country Code (dropdown) | "United States" |
| 9 | LinkedIn Profile | `PROFILE.linkedin` (full URL: `https://linkedin.com/in/seanivins`) |
| 10 | "How did you hear about us?" | **SKIP** — surface to checklist |
| 11 | EEO section | **SKIP** — surface to checklist |
| 12 | Work auth questions | **SKIP** — surface to checklist (legal claim, Sean answers) |
| 13 | Privacy policy checkbox | **SKIP** — surface to checklist |
| 14 | **STOP at Submit button** | NEVER auto-click |

### Lever field order

| # | Field | Source |
|---|---|---|
| 1 | Resume/CV (top of form) | `data/resumes/generated/<id:04d>_*_recruiter.pdf` |
| 2 | Full name | `PROFILE.name` |
| 3 | Pronouns checkboxes | **SKIP** — surface |
| 4 | Email | `PROFILE.email` |
| 5 | Phone | `PROFILE.phone` |
| 6 | Current location | `PROFILE.city` |
| 7 | Current company | `PROFILE.positions[0].company` (CA Engineering) |
| 8 | LinkedIn URL | `PROFILE.linkedin` |
| 9 | Twitter / GitHub / Portfolio | Fill if PROFILE has them; else surface as missing |
| 10 | Additional Information textarea | Paste the cover-letter JSON's `paragraphs.hook` (`data/resumes/generated/<id:04d>_*_cover.json`) if it exists; else fall back to tailored JSON's `cover_letter_hook`. Hook only — never paste the full letter. |
| 11 | Custom company sections | **SKIP** — surface |
| 12 | EEO survey | **SKIP** — surface |
| 13 | **STOP at Submit button** | NEVER auto-click |

### Workday field order (6-page wizard)

For each page, fill what you can per Step 5 protocol, then stop at "Save and Continue". Do NOT click Save and Continue automatically — show Sean what was filled and ask for confirmation before advancing the wizard.

**Page 1 — My Information:** name, address (`PROFILE.city`), phone, email, country
**Page 2 — My Experience:** Map `PROFILE.positions` to Workday's experience entries one-by-one; Sean reviews each
**Page 3 — Application Questions:** All manual (essays, custom questions)
**Page 4 — Voluntary Disclosures:** All manual (race, gender, veteran)
**Page 5 — Self Identify:** All manual (disability disclosure)
**Page 6 — Review:** Scroll, present complete summary, **STOP**

Note: Workday's `read_page` only returns viewport-visible elements. Scroll to discover all fields. Radio buttons are NOT returned by the interactive filter — use coordinate clicks via `javascript_tool`. Use the "Errors Found" box (clicking Save and Continue with empty fields) to discover all required fields on a page.

## Step 4 — Generic flow (unknown ATS)

If detection failed:
1. Navigate to the URL
2. Run `read_page` to snapshot the form
3. List every visible form field with its label
4. Ask Sean: *"This isn't a known ATS. Want me to fill standard fields where labels are obvious? (yes/no)"*
5. If yes: best-effort fill name, email, phone, LinkedIn, location, resume upload — using the same Step 5 protocol
6. If no: leave the page open and stop

Document any new ATS pattern in the role's `notes` field AND open a follow-up task to extend `references/ats-patterns.md`. Do not silently bake undocumented patterns into this mode.

## Step 5 — Pre-fill protocol

For every field the mode fills:

1. **Read first.** `read_page` or `find` to see if Sean already typed something. Never overwrite a non-empty field.
2. **Type or select.** Use `form_input` for text/dropdowns, `file_upload` for resumes.
3. **Snapshot after.** Re-read to verify the value stuck. Some Workday combo-boxes silently reject without errors.
4. **Log to manifest.** Track in an in-memory list: `{field, value, status: 'filled' | 'skipped' | 'failed'}`.

For every field the mode CAN'T fill (essays, conditional checkboxes, custom dropdowns), add to the manifest's `needs_sean` list with the field label and any visible options.

## Step 6 — LinkedIn Easy Apply (special case)

If ATS = `linkedin` AND URL is a LinkedIn job posting (`linkedin.com/jobs/view`):
- Easy Apply is a multi-page modal, not a real form
- Browser automation against LinkedIn is fragile and TOS-borderline
- Skip automation. Print:
  > "LinkedIn Easy Apply — modal-based, no browser automation supported. Open the posting in your browser and click 'Easy Apply' yourself. Resume PDF: `<path>`. After you submit, run `/coin track <id> applied`."
- Skip to Step 7 with empty manifest

## Step 7 — Final checklist + human gate

Print the session manifest in this exact format:

```
═══════════════════════════════════════════════════════════════
  Apply Session — Role <id>
  <company> — <title>
  ATS: <provider>  ·  PDF: <path/to/recruiter.pdf>
═══════════════════════════════════════════════════════════════

FILLED (n):
  ✓ First Name, Last Name
  ✓ Email
  ✓ Phone
  ✓ Resume/CV (uploaded)
  ✓ LinkedIn URL
  ✓ City
  ✓ Country (US)
  ...

NEEDS YOU (m):
  □ "How did you hear about us?" — pick a value (dropdown options: Indeed, LinkedIn, ...)
  □ Work auth: "Are you authorized to work in the US?" — pick yes/no
  □ EEO section (Race, Gender, Veteran, Disability) — pick or skip
  □ Privacy policy checkbox

NEXT STEP
  → Finish the m fields above in the browser
  → Click Submit (I will NOT click it for you)
  → Then: /coin track <id> applied
```

## Step 8 — Hard refusals (never automated)

The mode MUST refuse the following with a clear error:

| Refusal | Why |
|---|---|
| Auto-click Submit | Real-world commitment — only Sean submits |
| Fill "Yes I am a US citizen / authorized to work" | Legal claim — Sean answers personally |
| Fill EEO / disability / veteran questions | Personal disclosure — Sean's choice |
| Auto-create a Workday account | Prohibited per `references/ats-patterns.md`; TOS risk |
| Fill salary expectation fields | Negotiation matter — Sean answers strategically |
| Auto-transition role to `applied` after fill | Submit happens after fill; track happens after submit |

If Sean explicitly asks the mode to do any of these, refuse and explain. The refusals are non-negotiable.

## Step 9 — Notes for the executor

- File upload via browser automation is brittle. Use `file_upload` MCP tool when available; fall back to printing the PDF path and asking Sean to drag-drop.
- If a new field type appears that's not in the per-ATS table above, add it to `needs_sean` rather than guessing. Wrong autofill is worse than no autofill.
- Greenhouse's iframe restriction is the trickiest part — extract tokens, navigate to direct form URL, then fill. Verify by checking the URL bar after navigation.
- Workday's "Save and Continue" with empty required fields is a feature, not a bug — it surfaces all missing fields in one go. Use it deliberately to discover requirements.
- The applied gate (`/coin track <id> applied`) requires Sean's explicit "yes" per the SKILL.md hard rules. Even if Sean says "I submitted, mark it applied" right after this mode finishes, the mode itself does NOT call `track` — the user invokes that command separately.
