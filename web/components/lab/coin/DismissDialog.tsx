'use client'
// "Not a Fit" reason picker. Opens when a role is dropped into the "Not a Fit"
// column or dismissed from the role-detail dialog. Captures a structured reason
// code + optional custom text. Both land in role_events for the weekly
// improvement loop.

import { useEffect, useMemo, useRef, useState } from 'react'
import { X } from 'lucide-react'
import type { Role } from './types'

export interface DismissalReason {
  code: string
  label: string
  description: string | null
  sort_order: number
}

interface Props {
  role: Role
  reasons: DismissalReason[]
  onClose: () => void
  onSubmit: (reasonCode: string, reasonText: string | null, customText: string | null) => Promise<void> | void
}

const CUSTOM_CODE = '__custom__'

export function DismissDialog({ role, reasons, onClose, onSubmit }: Props) {
  const [selectedCode, setSelectedCode] = useState<string>('')
  const [customText, setCustomText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const firstButtonRef = useRef<HTMLButtonElement>(null)

  const sortedReasons = useMemo(
    () => [...reasons].sort((a, b) => a.sort_order - b.sort_order),
    [reasons]
  )

  useEffect(() => {
    firstButtonRef.current?.focus()
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.stopPropagation(); onClose() }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  const handleSubmit = async () => {
    if (!selectedCode) {
      setError('Pick a reason or use "Other".')
      return
    }
    if (selectedCode === CUSTOM_CODE && !customText.trim()) {
      setError('Add a custom reason or pick a preset.')
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const reasonCode = selectedCode === CUSTOM_CODE ? 'other' : selectedCode
      const reason = sortedReasons.find(r => r.code === selectedCode)
      const reasonText = reason?.label ?? null
      const trimmedCustom = customText.trim() || null
      await onSubmit(reasonCode, reasonText, trimmedCustom)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to dismiss')
      setSubmitting(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dismiss-title"
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        ref={dialogRef}
        className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-xl shadow-2xl flex flex-col"
      >
        <div className="flex items-start justify-between p-4 border-b border-zinc-800">
          <div className="min-w-0">
            <div id="dismiss-title" className="text-white font-semibold truncate">
              Dismiss {role.company}?
            </div>
            <div className="text-xs text-zinc-400 truncate">{role.title}</div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="text-zinc-400 hover:text-white p-1 -m-1"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="p-4 space-y-3">
          <div className="text-xs text-zinc-400">
            Why isn&apos;t this a fit? We&apos;ll log this so the weekly review can compare scoring against your real preferences.
          </div>
          <div className="space-y-1">
            {sortedReasons.map((r, i) => (
              <button
                key={r.code}
                ref={i === 0 ? firstButtonRef : undefined}
                onClick={() => setSelectedCode(r.code)}
                aria-pressed={selectedCode === r.code}
                className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                  selectedCode === r.code
                    ? 'bg-violet-900/40 border border-violet-700 text-white'
                    : 'bg-zinc-900 border border-transparent text-zinc-200 hover:bg-zinc-800'
                }`}
              >
                <div className="font-medium">{r.label}</div>
                {r.description && (
                  <div className="text-[11px] text-zinc-400 mt-0.5 leading-snug">{r.description}</div>
                )}
              </button>
            ))}
            <button
              onClick={() => setSelectedCode(CUSTOM_CODE)}
              aria-pressed={selectedCode === CUSTOM_CODE}
              className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                selectedCode === CUSTOM_CODE
                  ? 'bg-violet-900/40 border border-violet-700 text-white'
                  : 'bg-zinc-900 border border-transparent text-zinc-200 hover:bg-zinc-800'
              }`}
            >
              <div className="font-medium">Other (custom)</div>
              <div className="text-[11px] text-zinc-400 mt-0.5 leading-snug">Type your own reason below.</div>
            </button>
          </div>

          <div>
            <label htmlFor="dismiss-custom" className="text-[11px] text-zinc-500 uppercase tracking-wider">
              Notes {selectedCode === CUSTOM_CODE ? '(required)' : '(optional)'}
            </label>
            <textarea
              id="dismiss-custom"
              value={customText}
              onChange={e => setCustomText(e.target.value)}
              placeholder="e.g. base too low for the equity story; founder LinkedIn looks sketchy"
              rows={2}
              className="mt-1 w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/30"
            />
          </div>

          {error && <div className="text-xs text-red-400">{error}</div>}
        </div>

        <div className="flex gap-2 p-4 border-t border-zinc-800">
          <button
            onClick={onClose}
            className="flex-1 min-h-[40px] py-2 rounded-lg text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 min-h-[40px] py-2 rounded-lg text-sm font-medium bg-red-900/60 hover:bg-red-900 text-red-100 disabled:opacity-50 transition-colors"
          >
            {submitting ? 'Dismissing…' : 'Dismiss'}
          </button>
        </div>
      </div>
    </div>
  )
}
