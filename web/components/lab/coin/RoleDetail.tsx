'use client'
import { useState } from 'react'
import { X, ExternalLink, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import type { Role, ScoreBreakdown } from './types'
import { ScoreChart } from './ScoreChart'

interface Props {
  role: Role
  onClose: () => void
  onTrack: (status: string, note?: string) => void
  onTailor: () => void
  onNote: (text: string) => void
}

export function RoleDetail({ role, onClose, onTrack, onTailor, onNote }: Props) {
  const [jdOpen, setJdOpen] = useState(false)
  const [noteText, setNoteText] = useState('')
  const [tailorQueued, setTailorQueued] = useState(false)
  const [applyConfirm, setApplyConfirm] = useState(false)

  const parsed: ScoreBreakdown | null = (() => {
    if (!role.jd_parsed) return null
    try { return JSON.parse(role.jd_parsed) } catch { return null }
  })()

  const handleTailor = () => {
    onTailor()
    setTailorQueued(true)
  }

  const handleApply = () => {
    if (!applyConfirm) { setApplyConfirm(true); return }
    onTrack('applied')
    setApplyConfirm(false)
  }

  const stage = role.score_stage2 != null ? 'S2' : 'S1'

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-zinc-950 border border-zinc-800 rounded-t-2xl sm:rounded-2xl w-full sm:max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start gap-3 p-4 border-b border-zinc-800">
          <div className="flex-1 min-w-0">
            <div className="text-white font-semibold text-lg leading-tight">{role.title}</div>
            <div className="text-zinc-400 text-sm">{role.company} · {role.location ?? 'Remote'}</div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${stage === 'S2' ? 'text-cyan-400 bg-cyan-950' : 'text-zinc-500 bg-zinc-900'}`}>
              [{stage}]
            </span>
            {role.url && (
              <a href={role.url} target="_blank" rel="noreferrer" className="text-zinc-400 hover:text-white">
                <ExternalLink size={16} />
              </a>
            )}
            <button onClick={onClose} className="text-zinc-400 hover:text-white">
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="overflow-y-auto flex-1 p-4 space-y-4">
          {/* Score breakdown */}
          {parsed && (
            <section>
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Score Breakdown</div>
              <ScoreChart breakdown={parsed} />
            </section>
          )}

          {/* JD collapsible */}
          {role.jd_raw && (
            <section>
              <button
                onClick={() => setJdOpen(v => !v)}
                className="flex items-center gap-1 text-xs text-zinc-400 hover:text-white"
              >
                <FileText size={12} />
                {jdOpen ? 'Hide JD' : 'Show JD'}
                {jdOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
              {jdOpen && (
                <pre className="mt-2 text-xs text-zinc-400 bg-zinc-900 rounded p-3 overflow-x-auto whitespace-pre-wrap max-h-48">
                  {role.jd_raw}
                </pre>
              )}
            </section>
          )}

          {/* PDF preview */}
          <section>
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Resume PDF</div>
            <iframe
              src={`/api/coin/role/${role.id}/pdf`}
              className="w-full h-64 rounded border border-zinc-800 bg-zinc-900"
              title="Resume PDF"
            />
          </section>

          {/* Notes */}
          <section>
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Notes</div>
            {role.notes && (
              <pre className="text-xs text-zinc-400 bg-zinc-900 rounded p-3 whitespace-pre-wrap mb-2 max-h-32 overflow-y-auto">
                {role.notes}
              </pre>
            )}
            <div className="flex gap-2">
              <input
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
                placeholder="Append a note…"
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-1.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
              />
              <button
                onClick={() => { if (noteText.trim()) { onNote(noteText.trim()); setNoteText('') } }}
                className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded text-sm text-white transition-colors"
              >
                Append
              </button>
            </div>
          </section>
        </div>

        {/* Sticky action bar */}
        <div className="flex gap-2 p-4 border-t border-zinc-800">
          <button
            onClick={handleTailor}
            disabled={tailorQueued}
            className="flex-1 py-2 rounded-lg text-sm font-medium bg-violet-900/50 hover:bg-violet-900 text-violet-300 disabled:opacity-50 transition-colors"
          >
            {tailorQueued ? 'Queued ✓' : 'Tailor'}
          </button>
          {role.url && (
            <a
              href={role.url}
              target="_blank"
              rel="noreferrer"
              className="flex-1 py-2 rounded-lg text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-white text-center transition-colors"
            >
              Open in ATS
            </a>
          )}
          <button
            onClick={handleApply}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${applyConfirm ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : 'bg-zinc-800 hover:bg-zinc-700 text-white'}`}
          >
            {applyConfirm ? 'Confirm apply?' : 'Mark Applied'}
          </button>
        </div>
      </div>
    </div>
  )
}
