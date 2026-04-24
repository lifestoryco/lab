# Mode: url (one-off role ingestion)

Sean pasted a URL instead of running discover. Ingest that single role
into the pipeline, score it, and route to tailor.

## Input

- A single URL (LinkedIn, Indeed, or direct company job page)

## Steps

1. **Ask which archetype** this targets. Don't guess silently — the URL
   may fit multiple. Offer the five with one-line North Stars.

2. **Ingest the URL.** Use a short Python one-liner via Bash:

   ```bash
   .venv/bin/python -c "
   import sys; sys.path.insert(0,'.')
   from careerops.pipeline import upsert_role, init_db
   from careerops.scraper import fetch_jd
   init_db()
   jd = fetch_jd('<URL>')
   role_id = upsert_role({
       'url': '<URL>',
       'title': None,
       'company': None,
       'location': None,
       'remote': 0,
       'lane': '<lane>',
       'source': 'manual',
       'jd_raw': jd,
   })
   print('ingested role id:', role_id, 'jd chars:', len(jd))
   "
   ```

3. **Route to `score` mode** for the newly-created role ID.
   (score mode parses JD, updates fit score, then back to the user.)

4. **From there, standard flow**: tailor → track.

## Guardrail

If Sean pastes a URL for a role he clearly shouldn't pursue (obvious
mismatch, below comp floor, junior title), say so *before* ingesting.
He can override with "ingest anyway."
