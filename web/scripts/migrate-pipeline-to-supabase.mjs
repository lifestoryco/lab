#!/usr/bin/env node
// One-shot migrator: pipeline.db → Supabase.
//
// Usage:
//   USER_ID=<auth.users.id> SUPABASE_URL=… SUPABASE_SERVICE_ROLE_KEY=… \
//     node web/scripts/migrate-pipeline-to-supabase.mjs path/to/pipeline.db
//
// Or with .env.local present:
//   USER_ID=<…> node web/scripts/migrate-pipeline-to-supabase.mjs
//
// Idempotent: roles are upserted on (user_id, url). Re-running is safe and
// will pick up any newly-added rows in the SQLite source. role_events are
// NOT replayed — historical state changes are lost on first migration; only
// the current snapshot transfers.
//
// Run AFTER the target user has signed in once (so auth.users has their id).

import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { createClient } from '@supabase/supabase-js'

const require = createRequire(import.meta.url)
const Database = require('better-sqlite3')

// --- env --------------------------------------------------------------------

function loadEnvLocal() {
  const envPath = path.resolve(process.cwd(), '.env.local')
  if (!fs.existsSync(envPath)) return
  for (const line of fs.readFileSync(envPath, 'utf-8').split('\n')) {
    const m = /^([A-Z_][A-Z0-9_]*)=(.*)$/.exec(line.trim())
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^['"]|['"]$/g, '')
  }
}
loadEnvLocal()

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY
const USER_ID = process.env.USER_ID
const DB_PATH = process.argv[2] || process.env.COIN_DB_PATH ||
  path.resolve(process.cwd(), '../coin/data/db/pipeline.db')

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY')
  process.exit(1)
}
if (!USER_ID) {
  console.error('missing USER_ID — pass auth.users.id via env')
  process.exit(1)
}
if (!fs.existsSync(DB_PATH)) {
  console.error(`SQLite source not found: ${DB_PATH}`)
  process.exit(1)
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
})

const db = new Database(DB_PATH, { readonly: true })

// --- migrate roles ----------------------------------------------------------

function toIsoDate(v) {
  if (v == null) return null
  // SQLite stores either ISO datetime ('2026-04-28T10:39:00+00:00') or date ('2026-04-28').
  // Postgres timestamptz accepts both; pass through.
  return v
}

function toJsonb(v) {
  if (v == null) return null
  if (typeof v !== 'string') return v
  try { return JSON.parse(v) }
  catch { return { _raw: v } }              // preserve unparseable strings without losing data
}

const roles = db.prepare('SELECT * FROM roles ORDER BY id ASC').all()
console.log(`source: ${roles.length} roles`)

const STATUSES = new Set([
  'discovered','scored','resume_generated','applied','responded',
  'contact','interviewing','offer','rejected','withdrawn','no_apply','closed',
])

function clampStatus(s) { return STATUSES.has(s) ? s : 'discovered' }

const batchSize = 100
let migrated = 0
let failed = 0
for (let i = 0; i < roles.length; i += batchSize) {
  const batch = roles.slice(i, i + batchSize).map(r => ({
    user_id:         USER_ID,
    url:             r.url,
    title:           r.title,
    company:         r.company,
    location:        r.location,
    remote:          !!r.remote,
    lane:            r.lane,
    comp_min:        r.comp_min,
    comp_max:        r.comp_max,
    comp_source:     r.comp_source,
    comp_currency:   r.comp_currency || 'USD',
    comp_confidence: r.comp_confidence,
    fit_score:       r.fit_score,
    score_stage1:    r.score_stage1,
    score_stage2:    r.score_stage2,
    score_stage:     r.score_stage ?? 1,
    jd_parsed_at:    toIsoDate(r.jd_parsed_at),
    status:          clampStatus(r.status || 'discovered'),
    source:          r.source,
    jd_raw:          r.jd_raw,
    jd_parsed:       toJsonb(r.jd_parsed),
    notes:           r.notes,
    posted_at:       r.posted_at,                     // date column
    discovered_at:   toIsoDate(r.discovered_at) || new Date().toISOString(),
    updated_at:      toIsoDate(r.updated_at) || new Date().toISOString(),
  }))
  const { error } = await supabase
    .from('roles')
    .upsert(batch, { onConflict: 'user_id,url' })
  if (error) {
    console.error(`  batch ${i}-${i + batch.length} FAILED:`, error.message)
    failed += batch.length
  } else {
    migrated += batch.length
    process.stdout.write(`  migrated ${migrated}/${roles.length}\r`)
  }
}
console.log(`\nroles: ${migrated} migrated, ${failed} failed`)

// --- migrate offers/connections/outreach if non-empty -----------------------

for (const table of ['offers', 'connections', 'outreach']) {
  const rows = db.prepare(`SELECT * FROM ${table}`).all()
  if (rows.length === 0) continue
  console.log(`source: ${rows.length} ${table}`)
  // Strip integer PKs (Postgres bigserial assigns its own); attach user_id.
  const stripped = rows.map(({ id, ...rest }) => ({ ...rest, user_id: USER_ID }))
  const { error } = await supabase.from(table).insert(stripped)
  if (error) console.error(`  ${table} FAILED:`, error.message)
  else console.log(`  ${table}: ${rows.length} inserted`)
}

db.close()
console.log('done.')
