'use client'
import { useEffect, useRef, useState } from 'react'
import { X, ExternalLink, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import type { Role, ScoreBreakdown } from './types'
import { ScoreChart } from './ScoreChart'
import { safeUrl } from './constants'

interface Props {
  role: Role
  onClose: () => void
  onTrack: (status: string, note?: string) => void
  onTailor: () => void
  onNote: (text: string) => void
}

const APPLY_CONFIRM_TTL_MS = 4500
const JD_PARSE_MAX = 65_536  // cap JSON.parse on user-controlled blob

export function RoleDetail({ role, onClose, onTrack, onTailor, onNote }: Props) {
  const [jdOpen, setJdOpen] = useState(false)
  const [noteText, setNoteText] = useState('')
  const [tailorQueued, setTailorQueued] = useState(false)
  const [applyConfirm, setApplyConfirm] = useState(false)

  const closeBtnRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const applyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const url = safeUrl(role.url)

  const parsed: ScoreBreakdown | null = (() => {
    if (!role.jd_parsed) return null
    if (role.jd_parsed.length > JD_PARSE_MAX) return null
    try { return JSON.parse(role.jd_parsed) } catch { return null }
  })()

  // Modal accessibility: focus close button on mount, close on Escape,
  // basic focus loop (Tab/Shift+Tab from edges wraps within dialog).
  useEffect(() => {
    closeBtnRef.current?.focus()
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key === 'Tab' && dialogRef.current) {
        const focusables = dialogRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input, textarea, select, [tabindex]:not([tabindex="-1"])'
        )
        if (focusables.length === 0) return
        const first = focusables[0]
        const last = focusables[focusables.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  // Auto-revert applyConfirm so it doesn't sit pending forever (user wanders
  // away → returns days later → next click is an unintended apply).
  useEffect(() => {
    if (applyConfirm) {
      applyTimerRef.current = setTimeout(() => setApplyConfirm(false), APPLY_CONFIRM_TTL_MS)
      return () => {
        if (applyTimerRef.current) clearTimeout(applyTimerRef.current)
      }
    }
  }, [applyConfirm])

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
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Role detail: ${role.title} at ${role.company}`}
        onClick={e => e.stopPropagation()}
        className="bg-zinc-950 border border-zinc-800 rounded-t-2xl sm:rounded-2xl w-full sm:max-w-2xl max-h-[90vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-start gap-3 p-4 border-b border-zinc-800">
          <div className="flex-1 min-w-0">
            <div className="text-white font-semibold text-lg leading-tight">{role.title}</div>
            <div className="text-zinc-400 text-sm">{role.company} · {role.location ?? 'Remote'}</div>
          </div>
          <div className="flex items-center gap-2">
            <span
              aria-label={`Score stage ${stage}`}
              className={`text-xs font-mono px-1.5 py-0.5 rounded ${stage === 'S2' ? 'text-cyan-400 bg-cyan-950' : 'text-zinc-500 bg-zinc-900'}`}
            >
              [{stage}]
            </span>
            {url && (
              <a
                href={url}
                target="_blank"
                rel="noreferrer"
                aria-label="Open job posting in a new tab"
                title="Open job posting"
                className="text-zinc-400 hover:text-white p-2 -m-2"
              >
                <ExternalLink size={16} aria-hidden="true" />
              </a>
            )}
            <button
              ref={closeBtnRef}
              onClick={onClose}
              aria-label="Close role detail"
              className="text-zinc-400 hover:text-white p-2 -m-2"
            >
              <X size={20} aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="overflow-y-auto flex-1 p-4 space-y-4">
          {/* Score breakdown */}
          {parsed && (
            <section>
              <div className="text-xs text-zinc-400 uppercase tracking-wider mb-2">Score Breakdown</div>
              <ScoreChart breakdown={parsed} />
            </section>
          )}

          {/* JD collapsible */}
          {role.jd_raw && (
            <section>
              <button
                onClick={() => setJdOpen(v => !v)}
                aria-expanded={jdOpen}
                aria-controls="role-jd"
                className="flex items-center gap-1 text-xs text-zinc-400 hover:text-white min-h-[28px]"
              >
                <FileText size={12} aria-hidden="true" />
                {jdOpen ? 'Hide JD' : 'Show JD'}
                {jdOpen ? <ChevronUp size={12} aria-hidden="true" /> : <ChevronDown size={12} aria-hidden="true" />}
              </button>
              {jdOpen && (
                <pre id="role-jd" className="mt-2 text-xs text-zinc-400 bg-zinc-900 rounded p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-48">
                  {role.jd_raw}
                </pre>
              )}
            </section>
          )}

          {/* PDF preview */}
          <section>
            <div className="text-xs text-zinc-400 uppercase tracking-wider mb-2">Resume PDF</div>
            <iframe
              src={`/api/coin/role/${role.id}/pdf`}
              className="w-full h-64 rounded border border-zinc-800 bg-zinc-900"
              title={`Tailored resume PDF for ${role.title}`}
              loading="lazy"
              sandbox="allow-same-origin"
              referrerPolicy="no-referrer"
            />
          </section>

          {/* Notes */}
          <section>
            <label htmlFor="role-note-input" className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Notes</label>
            {role.notes && (
              <pre className="text-xs text-zinc-400 bg-zinc-900 rounded p-3 whitespace-pre-wrap break-words mb-2 max-h-32 overflow-y-auto">
                {role.notes}
              </pre>
            )}
            <div className="flex gap-2">
              <input
                id="role-note-input"
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
                placeholder="Append a note…"
                aria-label="Append a note"
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
              />
              <button
                onClick={() => { if (noteText.trim()) { onNote(noteText.trim()); setNoteText('') } }}
                disabled={!noteText.trim()}
                className="px-3 py-2 bg-zinc-800 hover:bg-zinc-700 rounded text-sm text-white transition-colors disabled:opacity-50"
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
            className="flex-1 min-h-[44px] py-2 rounded-lg text-sm font-medium bg-violet-900/50 hover:bg-violet-900 text-violet-200 disabled:opacity-50 transition-colors"
          >
            {tailorQueued ? 'Queued ✓' : 'Tailor'}
          </button>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="flex-1 min-h-[44px] flex items-center justify-center py-2 rounded-lg text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-white text-center transition-colors"
            >
              Open in ATS
            </a>
          )}
          <button
            onClick={handleApply}
            aria-pressed={applyConfirm}
            className={`flex-1 min-h-[44px] py-2 rounded-lg text-sm font-medium transition-colors ${applyConfirm ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : 'bg-zinc-800 hover:bg-zinc-700 text-white'}`}
          >
            {applyConfirm ? 'Confirm apply?' : 'Mark Applied'}
          </button>
        </div>
      </div>
    </div>
  )
}
