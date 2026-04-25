'use client'

import { useState, useEffect } from 'react'
import { useGameStore } from '../engine/useGameStore'
import { specialForWorld } from '../cage/specials'

// Per-world special-item button — appears bottom-left when a charge is available
// in cage mode on worlds 2-5. Tap fires the world's unique ability.
export default function SpecialButton() {
  const gamePhase = useGameStore(s => s.gamePhase)
  const mode      = useGameStore(s => s.mode)
  const worldIndex = useGameStore(s => s.worldIndex)
  const charges   = useGameStore(s => s.specialChargesRemaining)
  const firedAt   = useGameStore(s => s.lastSpecialFiredAt)
  const useSpecial = useGameStore(s => s.useSpecial)

  const [flash, setFlash] = useState(false)

  const meta = specialForWorld(worldIndex)

  // Flash on actual activation — keyed off lastSpecialFiredAt so world
  // transitions (which also drop charges to 0 transiently) don't trigger
  // a phantom flash.
  useEffect(() => {
    if (firedAt === null) return
    setFlash(true)
    const t = setTimeout(() => setFlash(false), 600)
    return () => clearTimeout(t)
  }, [firedAt])

  // Keyboard shortcut — Space or 'X' fires the special when available.
  useEffect(() => {
    if (gamePhase !== 'playing' || mode !== 'cage' || !meta || charges <= 0) return
    const onKey = (e: KeyboardEvent) => {
      if (e.code === 'Space' || e.key === 'x' || e.key === 'X') {
        e.preventDefault()
        useSpecial()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [gamePhase, mode, meta, charges, useSpecial])

  if (gamePhase !== 'playing') return null
  if (mode !== 'cage') return null
  if (!meta) return null

  const enabled = charges > 0
  const accent = meta.accent

  return (
    <div
      style={{
        position: 'fixed',
        // Lift above InstrumentSelector (which sits bottom-centre at ~16-48px)
        // so the two controls don't overlap on narrow portrait screens.
        bottom: 'clamp(96px, 14vh, 140px)',
        left: 'clamp(16px, 3vw, 36px)',
        zIndex: 11,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 4,
        pointerEvents: 'auto',
      }}
    >
      <button
        onClick={useSpecial}
        disabled={!enabled}
        aria-label={`${meta.name} — ${meta.hint}`}
        title={meta.hint}
        style={{
          width: 56,
          height: 56,
          borderRadius: '50%',
          background: enabled ? `radial-gradient(circle at 35% 30%, ${accent}33, #0d0d0d 70%)` : '#0a0a0a',
          border: enabled ? `1.5px solid ${accent}` : '1px solid rgba(255,255,255,0.22)',
          color: enabled ? accent : '#6a6a6a',
          fontFamily: '"Cormorant Garamond", Georgia, serif',
          fontSize: 28,
          lineHeight: '56px',
          cursor: enabled ? 'pointer' : 'default',
          padding: 0,
          textAlign: 'center',
          transition: 'opacity 0.4s ease, transform 0.2s ease, box-shadow 0.4s ease',
          opacity: enabled ? 1 : 0.45,
          boxShadow: flash
            ? `0 0 48px ${accent}, 0 0 16px ${accent}aa`
            : enabled
              ? `0 0 18px ${accent}55`
              : 'none',
          transform: flash ? 'scale(1.18)' : 'scale(1)',
          WebkitTapHighlightColor: 'transparent',
          touchAction: 'manipulation',
          userSelect: 'none',
        }}
      >
        {meta.glyph}
      </button>
      <span
        aria-hidden="true"
        style={{
          fontFamily: '"Cormorant Garamond", Georgia, serif',
          fontStyle: 'italic',
          fontSize: 11,
          color: enabled ? '#aaaaaa' : '#555555',
          letterSpacing: '0.12em',
          opacity: 0.85,
          pointerEvents: 'none',
          whiteSpace: 'nowrap',
          transition: 'color 0.4s ease',
        }}
      >
        {meta.name}
      </span>
    </div>
  )
}
