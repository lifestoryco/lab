// Single source of truth for COIN UI constants. Mirrors authoritative values
// from coin/careerops/{pipeline,score}.py + coin/config.py. Changes here MUST
// be paired with changes there — a future refactor should auto-generate this
// file from a Python introspection script. For now the comments are the
// drift guard. If you change a value, grep the Python side and update too.

import type { RoleStatus } from './types'

/** Mirror of pipeline.py::TERMINAL_STATUSES. Roles in these states are
 *  excluded from "active" counts and from the dashboard top_roles query. */
export const TERMINAL_STATUSES = new Set<RoleStatus>([
  'offer', 'rejected', 'withdrawn', 'no_apply', 'closed',
])

/** Mirror of config.py::SCORE_GRADE_THRESHOLDS — ordered descending floors. */
export const GRADE_THRESHOLDS: ReadonlyArray<readonly [string, number]> = [
  ['A', 85],
  ['B', 70],
  ['C', 55],
  ['D', 40],
]

/** Letter grade for a 0–100 fit score. Mirror of careerops.score.grade_for_score. */
export function gradeForScore(score: number | null | undefined): string {
  if (score == null) return 'F'
  for (const [letter, floor] of GRADE_THRESHOLDS) {
    if (score >= floor) return letter
  }
  return 'F'
}

/** Mirror of stories.VALID_LANES + score.LANE_NORTH_STARS keys. */
export const LANES = [
  'mid-market-tpm',
  'enterprise-sales-engineer',
  'iot-solutions-architect',
  'revenue-ops-operator',
] as const

export type Lane = typeof LANES[number]

export const LANE_COLORS: Record<string, string> = {
  'mid-market-tpm': '#3b82f6',
  'enterprise-sales-engineer': '#22c55e',
  'iot-solutions-architect': '#a855f7',
  'revenue-ops-operator': '#f59e0b',
}

export const GRADE_COLORS: Record<string, string> = {
  A: '#22c55e',
  B: '#86efac',
  C: '#facc15',
  D: '#f97316',
  F: '#ef4444',
}

/** Mirror of config.py::MIN_BASE_SALARY / MIN_TOTAL_COMP defaults. The header
 *  pill renders this band as a quick reminder of Sean's floor. */
export const COMP_FLOOR_LABEL = '$130K–$230K'

/** Stale-applied cutoff (days). Mirror of pipeline.dashboard() and server.ts
 *  fetchDashboard's stale_applications query. */
export const STALE_DAYS = 14

/** Top-N for the dashboard top_roles list. Mirror of server.ts hard-coded LIMIT. */
export const DASHBOARD_TOP_N = 15

/** Only HTTP(S) URLs are renderable as anchors — JD scrapers occasionally pick
 *  up `javascript:` or relative paths; those are dropped client-side. */
export function safeUrl(u: string | null | undefined): string | null {
  if (!u) return null
  return /^https?:\/\//i.test(u) ? u : null
}
