import 'server-only'
import { createSupabaseServerClient } from '@/lib/supabase/server'
import type { DashboardData, Role, Offer } from './types'
import type { Database } from './supabase-types'
import { DASHBOARD_TOP_N, STALE_DAYS, TERMINAL_STATUSES } from './constants'

type RoleStatusEnum = Database['public']['Enums']['role_status']
type RoleEventTypeEnum = Database['public']['Enums']['role_event_type']

// All reads are RLS-scoped to the current user. The Supabase server client
// reads the auth cookie automatically — no user_id parameter needed and no
// way for one user to leak data to another.
//
// The previous better-sqlite3 / committed pipeline.db snapshot has been
// retired. SSR + API routes both go through this module.

const TERMINAL_STATUS_LIST = Array.from(TERMINAL_STATUSES) as string[]

function emptyDashboard(): DashboardData {
  return {
    pipeline_counts: {},
    top_roles: [],
    stale_applications: [],
    updated_at: new Date(0).toISOString(),
  }
}

// Mirror Python's pipeline.get_role() COALESCE order: stage-2 first, then
// stage-1, then the legacy fit_score column. Postgres has no .order() option
// for COALESCE expressions in the supabase-js builder, so we sort client-side
// after fetch. Result sets are always small (<= 500 rows) so this is fine.
function rankScore(r: { score_stage2: number | null; score_stage1: number | null; fit_score: number | null }): number {
  return r.score_stage2 ?? r.score_stage1 ?? r.fit_score ?? -Infinity
}

// Map Supabase row → app Role type. The app's Role uses jd_parsed: string;
// DB stores jsonb. We re-stringify so existing client code that JSON.parses
// keeps working unchanged.
type DbRole = {
  id: number; user_id: string; url: string; title: string | null; company: string | null
  location: string | null; remote: boolean | null; lane: string | null
  comp_min: number | null; comp_max: number | null; comp_source: string | null
  comp_currency: string | null; comp_confidence: number | null
  fit_score: number | null; score_stage1: number | null; score_stage2: number | null
  score_stage: number | null; jd_parsed_at: string | null
  status: string; source: string | null; jd_raw: string | null
  jd_parsed: unknown; notes: string | null
  posted_at: string | null; discovered_at: string; updated_at: string
}

function rowToRole(r: DbRole): Role {
  return {
    id: r.id,
    company: r.company ?? '',
    title: r.title ?? '',
    location: r.location,
    url: r.url,
    source: r.source,
    lane: r.lane ?? '',
    status: r.status as Role['status'],
    fit_score: r.fit_score,
    fit_grade: null,                                  // computed client-side via gradeForScore
    score_stage1: r.score_stage1,
    score_stage2: r.score_stage2,
    comp_min: r.comp_min,
    comp_max: r.comp_max,
    comp_source: r.comp_source,
    posted_at: r.posted_at,
    discovered_at: r.discovered_at,
    jd_raw: r.jd_raw,
    jd_parsed: r.jd_parsed == null ? null : JSON.stringify(r.jd_parsed),
    notes: r.notes,
  }
}

export async function fetchDashboard(): Promise<DashboardData> {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return emptyDashboard()

  // Counts: cheap server-side aggregation via the pipeline_counts view.
  const { data: countsRows, error: countsErr } = await supabase
    .from('pipeline_counts')
    .select('status, n')
  if (countsErr) {
    console.error('[coin/server] pipeline_counts:', countsErr.message)
    return emptyDashboard()
  }
  const pipeline_counts: Record<string, number> = {}
  for (const row of countsRows ?? []) {
    if (row.status) pipeline_counts[row.status] = row.n ?? 0
  }

  // Top roles (active, ranked by authoritative score). Fetch with a generous
  // top-N then sort/slice client-side because Postgres can't ORDER BY COALESCE
  // through supabase-js's builder.
  const { data: activeRows, error: activeErr } = await supabase
    .from('roles')
    .select('*')
    .not('status', 'in', `(${TERMINAL_STATUS_LIST.map(s => `"${s}"`).join(',')})`)
    .limit(DASHBOARD_TOP_N * 4)
  if (activeErr) {
    console.error('[coin/server] active roles:', activeErr.message)
    return emptyDashboard()
  }
  const top_roles = (activeRows ?? [])
    .sort((a, b) => rankScore(b as DbRole) - rankScore(a as DbRole))
    .slice(0, DASHBOARD_TOP_N)
    .map(r => rowToRole(r as DbRole))

  // Stale applications: applied > STALE_DAYS ago.
  const stale_cutoff = new Date(Date.now() - STALE_DAYS * 86400_000).toISOString()
  const { data: staleRows } = await supabase
    .from('roles')
    .select('*')
    .eq('status', 'applied')
    .lt('updated_at', stale_cutoff)
    .order('updated_at', { ascending: true })
    .limit(10)
  const stale_applications = (staleRows ?? []).map(r => rowToRole(r as DbRole))

  return {
    pipeline_counts,
    top_roles,
    stale_applications,
    updated_at: new Date().toISOString(),
  }
}

export async function fetchRoles(filters: {
  status?: string; lane?: string; limit?: number
} = {}): Promise<Role[]> {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return []

  let q = supabase.from('roles').select('*')
  if (filters.status) q = q.eq('status', filters.status as RoleStatusEnum)
  if (filters.lane)   q = q.eq('lane',   filters.lane)
  // Fetch a buffer above limit because we sort client-side on COALESCE.
  const limit = filters.limit ?? 100
  q = q.limit(Math.min(limit * 2, 500))

  const { data, error } = await q
  if (error) {
    console.error('[coin/server] fetchRoles:', error.message)
    return []
  }
  return (data ?? [])
    .sort((a, b) => rankScore(b as DbRole) - rankScore(a as DbRole))
    .slice(0, limit)
    .map(r => rowToRole(r as DbRole))
}

export async function fetchRole(id: number): Promise<Role | null> {
  const supabase = await createSupabaseServerClient()
  const { data, error } = await supabase
    .from('roles')
    .select('*')
    .eq('id', id)
    .maybeSingle()
  if (error) {
    console.error('[coin/server] fetchRole:', error.message)
    return null
  }
  return data ? rowToRole(data as DbRole) : null
}

export async function fetchOffers(): Promise<Offer[]> {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return []

  const { data, error } = await supabase
    .from('offers')
    .select('*')
    .order('received_at', { ascending: false })
  if (error) {
    console.error('[coin/server] fetchOffers:', error.message)
    return []
  }
  return (data ?? []) as unknown as Offer[]
}

// Mutations are no longer 503'd — they go straight to Supabase via the
// per-request authed client. RLS enforces ownership.

export async function trackRoleStatus(
  roleId: number,
  newStatus: string,
  note?: string
): Promise<{ ok: true } | { ok: false; error: string }> {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { ok: false, error: 'Unauthorized' }

  // Read current status so we can record the from→to transition in the audit log.
  const { data: prev, error: prevErr } = await supabase
    .from('roles')
    .select('status, notes')
    .eq('id', roleId)
    .maybeSingle()
  if (prevErr || !prev) return { ok: false, error: 'Role not found' }

  const status = newStatus as RoleStatusEnum
  let nextNotes: string | null = null
  if (note) {
    const stamp = new Date().toISOString().slice(0, 10)
    const tag = `[${stamp} ${newStatus}]`
    const appended = `${tag} ${note}`
    nextNotes = prev.notes ? `${prev.notes}\n${appended}` : appended
  }
  const { error: updErr } = await supabase
    .from('roles')
    .update(nextNotes !== null ? { status, notes: nextNotes } : { status })
    .eq('id', roleId)
  if (updErr) return { ok: false, error: updErr.message }

  await supabase.from('role_events').insert({
    role_id: roleId,
    user_id: user.id,
    event_type: 'status_change' as RoleEventTypeEnum,
    payload: { from: prev.status, to: newStatus, note: note ?? null },
  })

  return { ok: true }
}

export async function dismissRole(
  roleId: number,
  reasonCode: string,
  reasonText?: string,
  customText?: string
): Promise<{ ok: true } | { ok: false; error: string }> {
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { ok: false, error: 'Unauthorized' }

  const { data: prev } = await supabase
    .from('roles')
    .select('status, notes')
    .eq('id', roleId)
    .maybeSingle()

  const stamp = new Date().toISOString().slice(0, 10)
  const noteFragments = [
    `[${stamp} no_apply]`,
    `[user_dismissed:${reasonCode}]`,
    customText ? customText : reasonText,
  ].filter(Boolean)
  const appended = noteFragments.join(' ')
  const newNotes = prev?.notes ? `${prev.notes}\n${appended}` : appended

  const { error: updErr } = await supabase
    .from('roles')
    .update({ status: 'no_apply' as RoleStatusEnum, notes: newNotes })
    .eq('id', roleId)
  if (updErr) return { ok: false, error: updErr.message }

  await supabase.from('role_events').insert({
    role_id: roleId,
    user_id: user.id,
    event_type: 'dismissed' as RoleEventTypeEnum,
    payload: {
      reason_code: reasonCode,
      reason_text: reasonText ?? null,
      custom_text: customText ?? null,
      from: prev?.status ?? null,
    },
  })

  return { ok: true }
}

export async function appendNote(
  roleId: number,
  text: string
): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!text.trim()) return { ok: false, error: 'Empty note' }
  const supabase = await createSupabaseServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { ok: false, error: 'Unauthorized' }

  const { data: prev } = await supabase
    .from('roles')
    .select('notes')
    .eq('id', roleId)
    .maybeSingle()

  const stamp = new Date().toISOString().slice(0, 10)
  const appended = `[${stamp} note] ${text.trim()}`
  const newNotes = prev?.notes ? `${prev.notes}\n${appended}` : appended

  const { error: updErr } = await supabase
    .from('roles')
    .update({ notes: newNotes })
    .eq('id', roleId)
  if (updErr) return { ok: false, error: updErr.message }

  await supabase.from('role_events').insert({
    role_id: roleId,
    user_id: user.id,
    event_type: 'note_added' as RoleEventTypeEnum,
    payload: { text: text.trim() },
  })

  return { ok: true }
}

export async function fetchDismissalReasons() {
  const supabase = await createSupabaseServerClient()
  const { data, error } = await supabase
    .from('dismissal_reasons')
    .select('code, label, description, sort_order')
    .order('sort_order', { ascending: true })
  if (error) {
    console.error('[coin/server] dismissal_reasons:', error.message)
    return []
  }
  return data ?? []
}
