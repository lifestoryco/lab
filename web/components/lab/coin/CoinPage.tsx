'use client'
// Architecture reference: /lab/holo (web/app/lab/holo/page.tsx + HoloPage.tsx).
// Read path: better-sqlite3 via server.ts for SSR; /api/coin/* for client refreshes.
// Mutation path: POST /api/coin/role/[id]/{track,tailor,notes} → careerops.web_cli subprocess.
// This split keeps Python as the single source of truth for state-machine validation.
//
// See ./README.md for the full module overview, including the Vercel
// read-only-deploy contract and how the constants module ties Python ↔ TS.

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Briefcase, Target, FileText, Users, DollarSign, BookOpen, RefreshCw, LogOut } from 'lucide-react'
import { useCoinUrlState } from './store'
import { Kanban } from './Kanban'
import { DiscoverFeed } from './DiscoverFeed'
import { NetworkView } from './NetworkView'
import { OfertasView } from './OfertasView'
import { StoriesView } from './StoriesView'
import { RoleDetail } from './RoleDetail'
import { RoleCard } from './RoleCard'
import type { DismissalReason } from './DismissDialog'
import {
  COMP_FLOOR_LABEL,
  TERMINAL_STATUSES,
  gradeForScore,
} from './constants'
import type { DashboardData, Role, RoleStatus } from './types'

type Tab = 'pipeline' | 'discover' | 'roles' | 'network' | 'ofertas' | 'stories'

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'pipeline', label: 'Pipeline',  icon: <Briefcase size={15} aria-hidden="true" /> },
  { id: 'discover', label: 'Discover',  icon: <Target size={15} aria-hidden="true" /> },
  { id: 'roles',    label: 'Roles',     icon: <FileText size={15} aria-hidden="true" /> },
  { id: 'network',  label: 'Network',   icon: <Users size={15} aria-hidden="true" /> },
  { id: 'ofertas',  label: 'Ofertas',   icon: <DollarSign size={15} aria-hidden="true" /> },
  { id: 'stories',  label: 'Stories',   icon: <BookOpen size={15} aria-hidden="true" /> },
]

const ERROR_TOAST_TTL_MS = 7000

interface Props { initialData: DashboardData | null }

export function CoinPage({ initialData }: Props) {
  const router = useRouter()
  const { tab: activeTab, setTab, roleId: urlRoleId, setRoleId } = useCoinUrlState()
  const [dashboard, setDashboard] = useState<DashboardData | null>(initialData)
  const [allRoles, setAllRoles] = useState<Role[]>(
    (initialData?.top_roles ?? []).map(r => ({ ...r, fit_grade: gradeForScore(r.fit_score) }))
  )
  const [reasons, setReasons] = useState<DismissalReason[]>([])
  const [refreshing, setRefreshing] = useState(false)
  const [mutateError, setMutateError] = useState<string | null>(null)
  // selectedRole is derived from the URL (?role=ID). Pop the matching Role
  // from allRoles when ID changes; this keeps back/forward = open/close
  // without storing duplicate state.
  const selectedRole: Role | null = urlRoleId
    ? allRoles.find(r => r.id === urlRoleId) ?? null
    : null
  const setSelectedRole = (r: Role | null) => setRoleId(r?.id ?? null)

  const abortRef = useRef<AbortController | null>(null)
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadDashboard = () => {
    // Cancel any in-flight load so rapid mutations don't stomp each other.
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setRefreshing(true)
    Promise.all([
      fetch('/api/coin/dashboard', { signal: ac.signal }).then(r => r.json()),
      fetch('/api/coin/roles?limit=200', { signal: ac.signal }).then(r => r.json()),
    ]).then(([dash, roles]) => {
      if (ac.signal.aborted) return
      setDashboard(dash)
      const list = Array.isArray(roles) ? (roles as Role[]) : []
      setAllRoles(list.map(r => ({ ...r, fit_grade: gradeForScore(r.fit_score) })))
    }).catch(e => {
      if (e?.name !== 'AbortError') console.error('loadDashboard failed:', e)
    }).finally(() => {
      if (!ac.signal.aborted) setRefreshing(false)
    })
  }

  // Pull the dismissal reason vocabulary once on mount. Cheap and we want it
  // ready when the user drops something into "Not a Fit".
  useEffect(() => {
    fetch('/api/coin/dismissal-reasons')
      .then(r => r.ok ? r.json() : [])
      .then((rs: DismissalReason[]) => Array.isArray(rs) && setReasons(rs))
      .catch(() => {})
  }, [])

  useEffect(() => {
    // Skip the redundant fetch if SSR already supplied a dashboard. Otherwise
    // (read-only Vercel deploy w/o initialData, or first cold render) load now.
    if (!initialData) {
      loadDashboard()
    } else {
      // Always pull the full role list — initialData.top_roles is capped at 15.
      const ac = new AbortController()
      abortRef.current = ac
      fetch('/api/coin/roles?limit=200', { signal: ac.signal })
        .then(r => r.json())
        .then((roles: Role[]) => {
          if (ac.signal.aborted) return
          const list = Array.isArray(roles) ? roles : []
          setAllRoles(list.map(r => ({ ...r, fit_grade: gradeForScore(r.fit_score) })))
        })
        .catch(e => { if (e?.name !== 'AbortError') console.error(e) })
    }
    return () => abortRef.current?.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only
  }, [])

  // Auto-dismiss the error toast so transient blips don't clutter the screen.
  useEffect(() => {
    if (mutateError) {
      errorTimerRef.current = setTimeout(() => setMutateError(null), ERROR_TOAST_TTL_MS)
      return () => {
        if (errorTimerRef.current) clearTimeout(errorTimerRef.current)
      }
    }
  }, [mutateError])

  const mutate = async (endpoint: string, body?: object) => {
    setMutateError(null)
    try {
      const r = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body ?? {}),
      })
      if (!r.ok) {
        const detail = await r.json().catch(() => ({}))
        if (r.status === 503) {
          setMutateError(detail.error ?? 'This dashboard is read-only on the deployed site. Use the local Coin CLI for changes.')
        } else {
          setMutateError(detail.error ?? `Request failed (${r.status})`)
        }
        return
      }
      loadDashboard()
    } catch (e) {
      console.error('mutation failed:', e)
      setMutateError('Network error — please try again.')
    }
  }

  const onTrack = (id: number, status: string, note?: string) =>
    mutate(`/api/coin/role/${id}/track`, { status, note })
  const onTailor = (id: number) =>
    mutate(`/api/coin/role/${id}/tailor`)
  const onNote = (id: number, text: string) =>
    mutate(`/api/coin/role/${id}/notes`, { text })
  const onDismiss = async (id: number, reasonCode: string, reasonText: string | null, customText: string | null) => {
    await mutate(`/api/coin/role/${id}/dismiss`, {
      reason_code: reasonCode,
      reason_text: reasonText,
      custom_text: customText,
    })
  }

  const onLogout = async () => {
    await fetch('/api/coin/logout', { method: 'POST' })
    router.push('/lab/coin/login')
    router.refresh()
  }

  const counts = dashboard?.pipeline_counts ?? {}
  const active = Object.entries(counts)
    .filter(([s]) => !TERMINAL_STATUSES.has(s as RoleStatus))
    .reduce((sum, [, n]) => sum + n, 0)
  const dataLoaded = dashboard != null

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <div className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <div>
            <div className="text-sm font-bold tracking-wider text-white font-mono">COIN</div>
            <div className="text-xs text-zinc-400">Career Ops</div>
          </div>

          <div className="flex gap-2 ml-4">
            <span
              aria-label={dataLoaded ? `${active} active roles` : 'loading active count'}
              className="text-xs px-2 py-1 rounded-full bg-zinc-900 text-zinc-200 tabular-nums"
            >
              {dataLoaded ? `${active} active` : '… active'}
            </span>
            <span
              aria-label={`Compensation floor ${COMP_FLOOR_LABEL}`}
              className="text-xs px-2 py-1 rounded-full bg-emerald-950 text-emerald-400 font-mono tabular-nums"
            >
              {COMP_FLOOR_LABEL}
            </span>
          </div>

          <button
            onClick={loadDashboard}
            disabled={refreshing}
            aria-label={refreshing ? 'Refreshing dashboard' : 'Refresh dashboard'}
            className="ml-auto text-zinc-400 hover:text-white transition-colors disabled:opacity-50 p-2 -m-2"
            title="Refresh"
          >
            <RefreshCw size={16} aria-hidden="true" className={refreshing ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={onLogout}
            aria-label="Log out"
            title="Log out"
            className="text-zinc-400 hover:text-white transition-colors p-2 -m-2"
          >
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>

        {/* Tab strip */}
        <nav aria-label="COIN sections" className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setTab(tab.id)}
              aria-current={activeTab === tab.id ? 'page' : undefined}
              className={`flex items-center gap-1.5 px-3 py-2 min-h-[44px] text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-violet-500 text-violet-400'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'pipeline' && (
          <Kanban
            roles={allRoles}
            reasons={reasons}
            onTrack={onTrack}
            onTailor={onTailor}
            onNote={onNote}
            onDismiss={onDismiss}
          />
        )}
        {activeTab === 'discover' && (
          <DiscoverFeed onTrack={onTrack} onTailor={onTailor} onNote={onNote} />
        )}
        {activeTab === 'roles' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {allRoles.map(r => (
              <RoleCard key={r.id} role={r} onClick={() => setSelectedRole(r)} />
            ))}
          </div>
        )}
        {activeTab === 'network'  && <NetworkView />}
        {activeTab === 'ofertas'  && <OfertasView />}
        {activeTab === 'stories'  && <StoriesView />}
      </div>

      {selectedRole && (
        <RoleDetail
          role={selectedRole}
          onClose={() => setSelectedRole(null)}
          onTrack={(status, note) => { onTrack(selectedRole.id, status, note); setSelectedRole(null) }}
          onTailor={() => onTailor(selectedRole.id)}
          onNote={(text) => onNote(selectedRole.id, text)}
        />
      )}

      {mutateError && (
        <div
          role="alert"
          aria-live="assertive"
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 max-w-md px-4 py-3 rounded-lg bg-red-950/90 border border-red-800 text-sm text-red-100 shadow-xl"
        >
          <div className="flex items-start gap-3">
            <span className="flex-1 leading-snug">{mutateError}</span>
            <button
              onClick={() => setMutateError(null)}
              aria-label="Dismiss error"
              className="text-red-300 hover:text-white text-xs"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
