'use client'

// End-of-session / view-only result composition. Used by:
//   · SignalPage during 'gameover' / 'complete' phases (live session)
//   · app/lab/signal/s/[hash] (viewer mode — someone clicked a shared link)

import { useMemo, useState, useCallback, useEffect, useRef } from 'react'
import { BIOMES } from '../worlds/biomeConfigs'
import { GRID_COLS, GRID_ROWS } from '../utils/isoMath'
import { encodeShareState, type SharedSessionState } from '../utils/shareState'
import { track } from '../utils/analytics'

const SERIF = '"Cormorant Garamond", Georgia, serif'

export interface ResultScreenProps {
  state: SharedSessionState
  mode: 'live' | 'viewer'
  onPlayAgain?: () => void
}

function headlineFor(state: SharedSessionState): string {
  if (state.completed && state.mode === 'cage') return 'You caged it.'
  if (state.completed)                           return 'You made it.'
  const biomeName = BIOMES[state.finalWorld]?.name ?? 'The Signal'
  return `You reached ${biomeName}.`
}

function subLineFor(state: SharedSessionState): string {
  if (state.completed) return 'Appreciate your life.'
  if (state.mode === 'cage') return 'It reached the edge.'
  return 'The shape failed to close.'
}

function statsLineFor(state: SharedSessionState): string {
  const cleared = state.cageLevelsCleared ?? 0
  let cagedCount = 0
  for (let i = 0; i < 5; i++) if (cleared & (1 << i)) cagedCount++
  if (state.mode === 'cage') {
    return `${cagedCount}/5 caged · ${state.blocks.length} blocks · mode: cage`
  }
  return `${state.blocks.length} blocks · ${state.totalChains} chains · mode: ${state.mode}`
}

// Canvas-like composition using pure DOM for portability / OG parity.
export default function ResultScreen({ state, mode, onPlayAgain }: ResultScreenProps) {
  const rootRef = useRef<HTMLDivElement | null>(null)
  const [fadeIn, setFadeIn] = useState(false)
  const [shareFeedback, setShareFeedback] = useState<string | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setFadeIn(true), mode === 'live' ? 800 : 40)
    return () => clearTimeout(t)
  }, [mode])

  // Viewer-mode: fire the shared-URL-opened event on mount
  useEffect(() => {
    if (mode !== 'viewer') return
    track('signal_shared_url_opened', { mode: state.mode, completed: state.completed })
  }, [mode, state.mode, state.completed])

  const hash = useMemo(() => encodeShareState(state), [state])
  const shareUrl = useMemo(() => {
    if (typeof window === 'undefined') return ''
    const origin = window.location.origin
    return `${origin}/lab/signal/s/${hash}`
  }, [hash])

  const handleShare = useCallback(async () => {
    const text = headlineFor(state) + ' — SIGNAL'
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nav = typeof navigator !== 'undefined' ? (navigator as any) : null
    try {
      if (nav?.share) {
        await nav.share({ title: 'SIGNAL', text, url: shareUrl })
        setShareFeedback('shared')
        track('signal_result_shared', { share_method: 'native' })
      } else if (nav?.clipboard?.writeText) {
        await nav.clipboard.writeText(shareUrl)
        setShareFeedback('copied')
        track('signal_result_shared', { share_method: 'copy' })
      } else {
        setShareFeedback('copy: ' + shareUrl)
      }
    } catch {
      try {
        if (nav?.clipboard?.writeText) {
          await nav.clipboard.writeText(shareUrl)
          setShareFeedback('copied')
        }
      } catch {
        setShareFeedback('link ready')
      }
    }
    setTimeout(() => setShareFeedback(null), 2500)
  }, [state, shareUrl])

  // Group blocks by biome for rendering grid snapshot
  const blocksByBiome = useMemo(() => {
    const map = new Map<number, Array<{ col: number; row: number }>>()
    for (const b of state.blocks) {
      if (!map.has(b.biome)) map.set(b.biome, [])
      map.get(b.biome)!.push({ col: b.col, row: b.row })
    }
    return map
  }, [state.blocks])

  return (
    <div
      ref={rootRef}
      style={{
        position: mode === 'live' ? 'fixed' : 'relative',
        inset: mode === 'live' ? 0 : undefined,
        minHeight: mode === 'viewer' ? '100vh' : undefined,
        width: '100%',
        backgroundColor: '#000000',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: mode === 'live' ? 30 : 1,
        opacity: fadeIn ? 1 : 0,
        transition: 'opacity 1.4s ease',
        padding: '56px 24px',
        boxSizing: 'border-box',
        textAlign: 'center',
      }}
    >
      {/* Biome strip — 5 dots showing which biomes were cleared */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 24 }}>
        {BIOMES.map((b, i) => {
          const cleared = (state.biomeClearBits & (1 << i)) !== 0
          const accent = b.palette.hasAccent ? b.palette.bright : '#cccccc'
          return (
            <span
              key={b.slug}
              aria-label={`${b.name}${cleared ? ' — cleared' : ''}`}
              style={{
                display: 'inline-block',
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: cleared ? accent : 'transparent',
                border: `1px solid ${cleared ? accent : 'rgba(255,255,255,0.25)'}`,
              }}
            />
          )
        })}
      </div>

      {/* Headline */}
      <h1
        style={{
          fontFamily: SERIF,
          fontWeight: 300,
          fontSize: 'clamp(1.8rem, 5vw, 3rem)',
          letterSpacing: '0.2em',
          color: '#ffffff',
          margin: 0,
        }}
      >
        {headlineFor(state)}
      </h1>

      {/* Subline */}
      <p
        style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(0.9rem, 2vw, 1.15rem)',
          letterSpacing: '0.12em',
          color: '#999999',
          marginTop: 12,
          marginBottom: 32,
        }}
      >
        {subLineFor(state)}
      </p>

      {/* Grid snapshot — SVG top-down of all blocks tinted by biome accent */}
      <svg
        aria-hidden="true"
        viewBox={`0 0 ${GRID_COLS} ${GRID_ROWS}`}
        width="min(360px, 78vw)"
        height="min(360px, 78vw)"
        style={{ marginBottom: 24, border: '1px solid rgba(255,255,255,0.08)' }}
      >
        {/* Checkerboard background */}
        {Array.from({ length: GRID_COLS }, (_, c) =>
          Array.from({ length: GRID_ROWS }, (_, r) => (
            <rect
              key={`${c},${r}`}
              x={c}
              y={r}
              width={1}
              height={1}
              fill={(c + r) % 2 === 0 ? '#0d0d0d' : '#080808'}
            />
          )),
        ).flat()}
        {/* Blocks — painted in biome order so later biomes sit on top */}
        {[...blocksByBiome.entries()].map(([biomeIdx, cells]) => {
          const biome = BIOMES[biomeIdx]
          const fill = biome?.palette.hasAccent ? biome.palette.bright : '#cccccc'
          return cells.map((c, i) => (
            <rect
              key={`${biomeIdx}-${i}`}
              x={c.col + 0.1}
              y={c.row + 0.1}
              width={0.8}
              height={0.8}
              fill={fill}
              fillOpacity={0.85}
            />
          ))
        })}
      </svg>

      {/* Stats — minimal */}
      <p
        style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 12,
          color: '#666',
          letterSpacing: '0.12em',
          marginBottom: 28,
        }}
      >
        {statsLineFor(state)}
      </p>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
        <button
          onClick={handleShare}
          style={buttonStyle}
          onMouseEnter={(e) => { e.currentTarget.style.color = '#ffffff' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#cccccc' }}
        >
          Share
        </button>
        {mode === 'live' && onPlayAgain && (
          <button
            onClick={onPlayAgain}
            style={buttonStyle}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#ffffff' }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#cccccc' }}
          >
            Listen again
          </button>
        )}
        {mode === 'viewer' && (
          <a
            href="/lab/signal"
            style={{ ...buttonStyle, textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
          >
            Play your own
          </a>
        )}
      </div>

      {shareFeedback && (
        <p style={{ fontFamily: SERIF, fontStyle: 'italic', fontSize: 12, color: '#888', marginTop: 16 }}>
          {shareFeedback}
        </p>
      )}
    </div>
  )
}

const buttonStyle: React.CSSProperties = {
  fontFamily: SERIF,
  fontStyle: 'italic',
  fontSize: 14,
  color: '#cccccc',
  background: 'none',
  border: '1px solid rgba(255,255,255,0.2)',
  padding: '12px 24px',
  minHeight: 44,
  borderRadius: 2,
  cursor: 'pointer',
  letterSpacing: '0.1em',
  transition: 'color 0.2s',
}
