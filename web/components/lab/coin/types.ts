export type RoleStatus =
  | 'discovered' | 'scored' | 'resume_generated' | 'applied'
  | 'responded' | 'contact' | 'interviewing' | 'offer'
  | 'rejected' | 'withdrawn' | 'closed' | 'no_apply'

export interface Role {
  id: number
  company: string
  title: string
  location: string | null
  url: string | null
  source: string | null
  lane: string
  status: RoleStatus
  fit_score: number | null
  fit_grade: string | null
  score_stage1?: number | null
  score_stage2?: number | null
  comp_min: number | null
  comp_max: number | null
  comp_source: string | null
  posted_at: string | null
  discovered_at: string
  jd_raw: string | null
  jd_parsed: string | null
  notes: string | null
}

export interface ScoreBreakdown {
  composite: number
  grade: string
  dimensions: Record<string, { weight: number; raw: number; contribution: number }>
}

export interface Outreach {
  id: number
  role_id: number | null
  recipient_name: string
  recipient_handle: string | null
  channel: string
  draft: string
  sent_at: string | null
  reply_at: string | null
}

export interface Connection {
  id: number
  full_name: string
  company: string | null
  title: string | null
  linkedin_url: string | null
}

export interface Offer {
  id: number
  company: string
  title: string
  base_salary: number
  annual_bonus_target_pct: number | null
  rsu_total_value: number | null
  rsu_vest_years: number | null
  signing_bonus: number | null
  status: string
  received_at: string | null
}

export interface Story {
  id: string
  lane: string
  headline: string
  context: string
  metric: string
  source_of_truth: string
}

export interface DashboardData {
  pipeline_counts: Record<string, number>
  top_roles: Role[]
  stale_applications: Role[]
  updated_at: string
}
