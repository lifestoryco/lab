'use client'
// Architecture reference: /lab/holo (web/app/lab/holo/page.tsx + HoloPage.tsx).
// Read path: better-sqlite3 via server.ts for SSR; /api/coin/* for client refreshes.
// Mutation path: POST /api/coin/role/[id]/{track,tailor,notes} → careerops.web_cli subprocess.
// This split keeps Python as the single source of truth for state-machine validation.

import { useEffect, useState } from 'react'
import { Briefcase, Target, FileText, Users, DollarSign, BookOpen, RefreshCw } from 'lucide-react'
import { useCoinStore } from './store'
import { Kanban } from './Kanban'
import { DiscoverFeed } from './DiscoverFeed'
import { NetworkView } from './NetworkView'
import { OfertasView } from './OfertasView'
import { StoriesView } from './StoriesView'
import type { DashboardData, Role } from './types'

type Tab = 'pipeline' | 'discover' | 'roles' | 'network' | 'ofertas' | 'stories'

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'pipeline', label: 'Pipeline',  icon: <Briefcase size={15} /> },
  { id: 'discover', label: 'Discover',  icon: <Target size={15} /> },
  { id: 'roles',    label: 'Roles',     icon: <FileText size={15} /> },
  { id: 'network',  label: 'Network',   icon: <Users size={15} /> },
  { id: 'ofertas',  label: 'Ofertas',   icon: <DollarSign size={15} /> },
  { id: 'stories',  label: 'Stories',   icon: <BookOpen size={15} /> },
]

function gradeForRole(role: Role): string {
  const s = role.fit_score ?? 0
  if (s >= 85) return 'A'; if (s >= 70) return 'B'; if (s >= 55) return 'C'
  if (s >= 40) return 'D'; return 'F'
}

interface Props { initialData: DashboardData | null }

export function CoinPage({ initialData }: Props) {
  const { activeTab, setTab } = useCoinStore()
  const [dashboard, setDashboard] = useState<DashboardData | null>(initialData)
  const [allRoles, setAllRoles] = useState<Role[]>(initialData?.top_roles ?? [])
  const [refreshing, setRefreshing] = useState(false)

  const loadDashboard = () => {
    setRefreshing(true)
    Promise.all([
      fetch('/api/coin/dashboard').then(r => r.json()),
      fetch('/api/coin/roles?limit=200').then(r => r.json()),
    ]).then(([dash, roles]) => {
      setDashboard(dash)
      setAllRoles((roles as Role[]).map(r => ({ ...r, fit_grade: gradeForRole(r) })))
    }).catch(console.error).finally(() => setRefreshing(false))
  }

  useEffect(() => {
    // Always load full list on mount even if SSR provided partial data
    fetch('/api/coin/roles?limit=200').then(r => r.json()).then((roles: Role[]) => {
      setAllRoles(roles.map(r => ({ ...r, fit_grade: gradeForRole(r) })))
    }).catch(console.error)
  }, [])

  const mutate = async (endpoint: string, body?: object) => {
    try {
      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body ?? {}),
      })
      loadDashboard()
    } catch (e) {
      console.error('mutation failed:', e)
    }
  }

  const onTrack = (id: number, status: string, note?: string) =>
    mutate(`/api/coin/role/${id}/track`, { status, note })
  const onTailor = (id: number) =>
    mutate(`/api/coin/role/${id}/tailor`)
  const onNote = (id: number, text: string) =>
    mutate(`/api/coin/role/${id}/notes`, { text })

  const counts = dashboard?.pipeline_counts ?? {}
  const active = Object.entries(counts)
    .filter(([s]) => !['offer','rejected','withdrawn','no_apply','closed'].includes(s))
    .reduce((sum, [, n]) => sum + n, 0)

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <div className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <div>
            <div className="text-sm font-bold tracking-wider text-white font-mono">COIN</div>
            <div className="text-xs text-zinc-500">Career Ops</div>
          </div>

          <div className="flex gap-2 ml-4">
            <span className="text-xs px-2 py-1 rounded-full bg-zinc-900 text-zinc-300">
              {active} active
            </span>
            <span className="text-xs px-2 py-1 rounded-full bg-emerald-950 text-emerald-400">
              $130K–$230K
            </span>
          </div>

          <button
            onClick={loadDashboard}
            disabled={refreshing}
            className="ml-auto text-zinc-500 hover:text-white transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Tab strip */}
        <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-violet-500 text-violet-400'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'pipeline' && (
          <Kanban roles={allRoles} onTrack={onTrack} onTailor={onTailor} onNote={onNote} />
        )}
        {activeTab === 'discover' && (
          <DiscoverFeed onTrack={onTrack} onTailor={onTailor} onNote={onNote} />
        )}
        {activeTab === 'roles' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {allRoles.map(r => (
              <div key={r.id} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-sm">
                <div className="font-medium text-white truncate">{r.title}</div>
                <div className="text-zinc-400 text-xs">{r.company} · {r.status}</div>
                {r.fit_score && (
                  <div className="text-xs font-mono text-zinc-300 mt-1">{r.fit_score.toFixed(1)} ({gradeForRole(r)})</div>
                )}
              </div>
            ))}
          </div>
        )}
        {activeTab === 'network'  && <NetworkView />}
        {activeTab === 'ofertas'  && <OfertasView />}
        {activeTab === 'stories'  && <StoriesView />}
      </div>
    </div>
  )
}
