'use client'
// Column taxonomy adapted from santifer/career-ops dashboard (MIT license).
// Drag-and-drop: framer-motion Reorder. Mobile: tap → action sheet.

import { useState } from 'react'
import { Reorder } from 'framer-motion'
import type { Role, RoleStatus } from './types'
import { RoleCard } from './RoleCard'
import { RoleDetail } from './RoleDetail'

interface Column {
  id: string
  label: string
  statuses: RoleStatus[]
  color: string
}

const COLUMNS: Column[] = [
  { id: 'discovered',  label: 'Discovered',  statuses: ['discovered'],                     color: '#6366f1' },
  { id: 'scored',      label: 'Scored',       statuses: ['scored'],                         color: '#3b82f6' },
  { id: 'tailored',    label: 'Tailored',     statuses: ['resume_generated'],               color: '#8b5cf6' },
  { id: 'applied',     label: 'Applied',      statuses: ['applied'],                        color: '#f59e0b' },
  { id: 'interviewing',label: 'Interviewing', statuses: ['responded','contact','interviewing'], color: '#10b981' },
  { id: 'offer',       label: 'Offer',        statuses: ['offer'],                          color: '#22c55e' },
]

function gradeForRole(role: Role): string {
  const s = role.fit_score ?? 0
  if (s >= 85) return 'A'
  if (s >= 70) return 'B'
  if (s >= 55) return 'C'
  if (s >= 40) return 'D'
  return 'F'
}

interface Props {
  roles: Role[]
  onTrack: (id: number, status: string, note?: string) => void
  onTailor: (id: number) => void
  onNote: (id: number, text: string) => void
}

export function Kanban({ roles, onTrack, onTailor, onNote }: Props) {
  const [selected, setSelected] = useState<Role | null>(null)
  const [activeColumnIndex, setActiveColumnIndex] = useState(0)

  const rolesByStatus = (statuses: RoleStatus[]) =>
    roles.filter(r => statuses.includes(r.status as RoleStatus))
      .map(r => ({ ...r, fit_grade: gradeForRole(r) }))

  const handleDrop = (columnId: string, role: Role) => {
    const col = COLUMNS.find(c => c.id === columnId)
    if (!col) return
    const targetStatus = col.statuses[0]
    if (targetStatus !== role.status) onTrack(role.id, targetStatus)
  }

  return (
    <>
      {/* Desktop: horizontal scroll */}
      <div className="hidden sm:flex gap-3 overflow-x-auto pb-4 min-h-[60vh]">
        {COLUMNS.map(col => {
          const colRoles = rolesByStatus(col.statuses)
          return (
            <div key={col.id} className="flex-shrink-0 w-56">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: col.color }} />
                <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">{col.label}</span>
                <span className="ml-auto text-xs text-zinc-600">{colRoles.length}</span>
              </div>
              <Reorder.Group
                axis="y"
                values={colRoles}
                onReorder={() => {}}
                className="space-y-2"
              >
                {colRoles.map(role => (
                  <Reorder.Item
                    key={role.id}
                    value={role}
                    onDragEnd={() => handleDrop(col.id, role)}
                  >
                    <RoleCard role={role} onClick={() => setSelected(role)} />
                  </Reorder.Item>
                ))}
              </Reorder.Group>
            </div>
          )
        })}
      </div>

      {/* Mobile: single column with tab strip */}
      <div className="sm:hidden">
        <div className="flex overflow-x-auto gap-1 pb-2 mb-3">
          {COLUMNS.map((col, i) => (
            <button
              key={col.id}
              onClick={() => setActiveColumnIndex(i)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                i === activeColumnIndex ? 'text-white' : 'text-zinc-500 bg-zinc-900'
              }`}
              style={i === activeColumnIndex ? { backgroundColor: col.color + '33', color: col.color } : {}}
            >
              {col.label} ({rolesByStatus(col.statuses).length})
            </button>
          ))}
        </div>
        <div className="space-y-2">
          {rolesByStatus(COLUMNS[activeColumnIndex].statuses).map(role => (
            <RoleCard key={role.id} role={role} onClick={() => setSelected(role)} />
          ))}
        </div>
      </div>

      {selected && (
        <RoleDetail
          role={selected}
          onClose={() => setSelected(null)}
          onTrack={(status, note) => { onTrack(selected.id, status, note); setSelected(null) }}
          onTailor={() => onTailor(selected.id)}
          onNote={(text) => onNote(selected.id, text)}
        />
      )}
    </>
  )
}
