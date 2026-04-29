'use client'
// Column taxonomy adapted from santifer/career-ops dashboard (MIT license).
// Drag-and-drop: framer-motion Reorder for pointer; RoleDetail action bar is the
// keyboard-accessible alternative for status changes.

import { useEffect, useMemo, useRef, useState } from 'react'
import { Reorder } from 'framer-motion'
import type { Role, RoleStatus } from './types'
import { RoleCard } from './RoleCard'
import { RoleDetail } from './RoleDetail'
import { DismissDialog, type DismissalReason } from './DismissDialog'
import { useCoinUrlState } from './store'
import { gradeForScore } from './constants'

interface Column {
  id: string
  label: string
  statuses: RoleStatus[]
  color: string
  // If set, dropping a card here triggers an action instead of (or in addition
  // to) a status change.
  action?: 'queue_tailor' | 'reject_not_fit'
  hint?: string
}

const COLUMNS: Column[] = [
  { id: 'discovered',     label: 'Discovered',    statuses: ['discovered'],                         color: '#6366f1' },
  { id: 'scored',         label: 'Scored',        statuses: ['scored'],                             color: '#3b82f6' },
  { id: 'resume_builder', label: 'Resume Builder',statuses: [],                                      color: '#a78bfa',
    action: 'queue_tailor', hint: 'Drag a role here to enqueue a tailored resume build.' },
  { id: 'tailored',       label: 'Tailored',      statuses: ['resume_generated'],                   color: '#8b5cf6' },
  { id: 'applied',        label: 'Applied',       statuses: ['applied'],                            color: '#f59e0b' },
  { id: 'interviewing',   label: 'Interviewing',  statuses: ['responded','contact','interviewing'], color: '#10b981' },
  { id: 'offer',          label: 'Offer',         statuses: ['offer'],                              color: '#22c55e' },
  { id: 'not_a_fit',      label: 'Not a Fit',     statuses: ['no_apply'],                           color: '#71717a',
    action: 'reject_not_fit', hint: 'Drag here to dismiss. Logged for future scoring tuning.' },
]

const TOAST_TTL_MS = 2500

interface Props {
  roles: Role[]
  reasons: DismissalReason[]
  onTrack: (id: number, status: string, note?: string) => void
  onTailor: (id: number) => void
  onNote: (id: number, text: string) => void
  onDismiss: (id: number, reasonCode: string, reasonText: string | null, customText: string | null) => Promise<void> | void
}

export function Kanban({ roles, reasons, onTrack, onTailor, onNote, onDismiss }: Props) {
  // Selected-role lives in the URL (?role=ID) so the browser back button
  // closes the detail dialog instead of jumping back to the lab gallery.
  // Same hook is used by CoinPage.tsx — both tabs and Kanban share state.
  const { roleId: selectedId, setRoleId } = useCoinUrlState()
  const [dismissTarget, setDismissTarget] = useState<Role | null>(null)

  const enriched = useMemo(
    () => roles.map(r => ({ ...r, fit_grade: r.fit_grade ?? gradeForScore(r.fit_score) })),
    [roles]
  )

  const rolesByStatus = useMemo(() => {
    return (statuses: RoleStatus[]) =>
      enriched.filter(r => statuses.includes(r.status as RoleStatus))
  }, [enriched])

  // Default to the column with the most roles so mobile users don't land on an
  // empty "Discovered" pile when all action is in "Scored" or further along.
  const defaultColumnIndex = useMemo(() => {
    let bestIdx = 0
    let bestCount = -1
    COLUMNS.forEach((c, i) => {
      const n = rolesByStatus(c.statuses).length
      if (n > bestCount) { bestCount = n; bestIdx = i }
    })
    return bestIdx
  }, [rolesByStatus])

  const [activeColumnIndex, setActiveColumnIndex] = useState(defaultColumnIndex)
  const [hasUserPicked, setHasUserPicked] = useState(false)

  // Sync default → active when (a) user hasn't picked yet and roles arrive, OR
  // (b) the user-picked column just became empty (e.g. they moved its only card
  // to another column and now it's stranded). React-correct: do this in an
  // effect, not during render.
  useEffect(() => {
    const activeCount = rolesByStatus(COLUMNS[activeColumnIndex].statuses).length
    if (!hasUserPicked && activeColumnIndex !== defaultColumnIndex && roles.length > 0) {
      setActiveColumnIndex(defaultColumnIndex)
    } else if (hasUserPicked && activeCount === 0 && roles.length > 0) {
      setActiveColumnIndex(defaultColumnIndex)
      setHasUserPicked(false)
    }
  }, [defaultColumnIndex, hasUserPicked, activeColumnIndex, rolesByStatus, roles.length])

  // Cleanup-aware toast: tracking the timer ref prevents stacked timers from
  // racing each other and prevents setState-on-unmounted warnings.
  const [toast, setToast] = useState<string | null>(null)
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => () => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
  }, [])
  const flashToast = (msg: string) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    setToast(msg)
    toastTimerRef.current = setTimeout(() => setToast(null), TOAST_TTL_MS)
  }

  const handleDrop = (columnId: string, role: Role) => {
    const col = COLUMNS.find(c => c.id === columnId)
    if (!col) return
    if (col.action === 'queue_tailor') {
      onTailor(role.id)
      flashToast(`Queued tailor for ${role.company}`)
      return
    }
    if (col.action === 'reject_not_fit') {
      // Open the reason picker; the dialog calls onDismiss on submit, which
      // both updates status to no_apply and writes a structured role_event for
      // the weekly improvement loop.
      setDismissTarget(role)
      return
    }
    const targetStatus = col.statuses[0]
    if (!targetStatus) {
      flashToast('No-op: column has no target status')
      return
    }
    if (targetStatus !== role.status) onTrack(role.id, targetStatus)
  }

  return (
    <>
      {/* Desktop: horizontal scroll */}
      <div className="hidden sm:flex gap-3 overflow-x-auto pb-4 min-h-[60vh] snap-x">
        {COLUMNS.map(col => {
          const colRoles = rolesByStatus(col.statuses)
          const isActionCol = !!col.action
          return (
            <div key={col.id} className="flex-shrink-0 w-56 snap-start">
              <div className="flex items-center gap-2 mb-2">
                <div aria-hidden="true" className="w-2 h-2 rounded-full" style={{ backgroundColor: col.color }} />
                <span className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">{col.label}</span>
                <span className="ml-auto text-xs text-zinc-400 tabular-nums">{colRoles.length}</span>
              </div>
              <Reorder.Group
                axis="y"
                values={colRoles}
                onReorder={() => {}}
                className={`space-y-2 min-h-[120px] rounded-lg ${
                  isActionCol ? 'border border-dashed border-zinc-800 p-2' : ''
                }`}
              >
                {colRoles.map(role => (
                  <Reorder.Item
                    key={role.id}
                    value={role}
                    onDragEnd={() => handleDrop(col.id, role)}
                  >
                    <RoleCard role={role} onClick={() => setRoleId(role.id)} />
                  </Reorder.Item>
                ))}
                {isActionCol && colRoles.length === 0 && col.hint && (
                  <div className="text-[11px] text-zinc-400 italic px-1 pt-1 leading-snug">
                    {col.hint}
                  </div>
                )}
              </Reorder.Group>
            </div>
          )
        })}
      </div>

      {/* Mobile: single column with tab strip */}
      <div className="sm:hidden">
        <div role="tablist" aria-label="Pipeline column" className="flex overflow-x-auto gap-1 pb-2 mb-3">
          {COLUMNS.map((col, i) => {
            const isActive = i === activeColumnIndex
            return (
              <button
                key={col.id}
                role="tab"
                aria-selected={isActive}
                onClick={() => { setActiveColumnIndex(i); setHasUserPicked(true) }}
                className={`flex-shrink-0 min-h-[44px] px-4 py-2 rounded-full text-xs font-medium transition-colors border ${
                  isActive ? 'border-current text-white' : 'border-transparent text-zinc-300 bg-zinc-900'
                }`}
                style={isActive ? { backgroundColor: col.color + '33', color: col.color } : {}}
              >
                {col.label} ({rolesByStatus(col.statuses).length})
              </button>
            )
          })}
        </div>
        <div className="space-y-2">
          {rolesByStatus(COLUMNS[activeColumnIndex].statuses).map(role => (
            <RoleCard key={role.id} role={role} onClick={() => setRoleId(role.id)} />
          ))}
        </div>
      </div>

      {(() => {
        const selected = selectedId ? enriched.find(r => r.id === selectedId) ?? null : null
        if (!selected) return null
        return (
          <RoleDetail
            role={selected}
            onClose={() => setRoleId(null)}
            onTrack={(status, note) => { onTrack(selected.id, status, note); setRoleId(null) }}
            onTailor={() => onTailor(selected.id)}
            onNote={(text) => onNote(selected.id, text)}
          />
        )
      })()}

      {dismissTarget && (
        <DismissDialog
          role={dismissTarget}
          reasons={reasons}
          onClose={() => setDismissTarget(null)}
          onSubmit={async (code, text, custom) => {
            await onDismiss(dismissTarget.id, code, text, custom)
            flashToast(`Dismissed ${dismissTarget.company}`)
          }}
        />
      )}

      {toast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-full bg-zinc-900 border border-zinc-700 text-sm text-white shadow-xl pointer-events-none"
        >
          {toast}
        </div>
      )}
    </>
  )
}
