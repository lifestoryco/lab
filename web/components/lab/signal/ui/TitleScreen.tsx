'use client'

import { useState, useEffect } from 'react'
import { useGameStore } from '../engine/useGameStore'

interface TitleScreenProps {
  visible: boolean
  worldName?: string
  worldSubtitle?: string
}

export default function TitleScreen({ visible, worldName, worldSubtitle }: TitleScreenProps) {
  // Phase 0: hidden → Phase 1: scan line → Phase 2: letters + subtitle
  const [scanVisible, setScanVisible] = useState(false)
  const [lettersVisible, setLettersVisible] = useState(false)

  const mode       = useGameStore(s => s.mode)
  const setMode    = useGameStore(s => s.setMode)
  const worldIndex = useGameStore(s => s.worldIndex)

  useEffect(() => {
    if (visible) {
      // Scan line fires first — like a radio transmission being received
      const t1 = setTimeout(() => setScanVisible(true), 200)
      // Letters materialize after the scan completes
      const t2 = setTimeout(() => setLettersVisible(true), 650)
      return () => { clearTimeout(t1); clearTimeout(t2) }
    } else {
      setScanVisible(false)
      setLettersVisible(false)
    }
  }, [visible])

  if (!visible) return null

  const title = 'SIGNAL'
  const letters = title.split('')

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 20,
        pointerEvents: 'none',
        transition: 'none',
      }}
    >
      {/* Radar scan line — sweeps across the screen before the title appears */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: '50%',
          left: '8%',
          right: '8%',
          height: '1px',
          background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.18) 40%, rgba(255,255,255,0.28) 50%, rgba(255,255,255,0.18) 60%, transparent 100%)',
          transform: scanVisible ? 'scaleX(1)' : 'scaleX(0)',
          transformOrigin: 'left center',
          transition: 'transform 0.38s cubic-bezier(0.4, 0, 0.2, 1)',
          opacity: lettersVisible ? 0 : 1,
        }}
      />

      {/* Title with letter-stagger animation */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          marginTop: '8vh',
        }}
      >
        {letters.map((letter, i) => (
          <span
            key={i}
            style={{
              fontFamily: '"Cormorant Garamond", Georgia, serif',
              fontSize: 'clamp(2.5rem, 6vw, 5rem)',
              fontWeight: 300,
              letterSpacing: '0.2em',
              color: '#ffffff',
              opacity: lettersVisible ? 1 : 0,
              transform: lettersVisible
                ? 'translateY(0)'
                : 'translateY(20px)',
              transition: `opacity 0.6s ease ${i * 0.06}s, transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${i * 0.06}s`,
            }}
          >
            {letter}
          </span>
        ))}
      </div>

      {/* Subtitle — #999 passes WCAG AA (6.3:1 on black) */}
      <p
        style={{
          fontFamily: '"Cormorant Garamond", Georgia, serif',
          fontStyle: 'italic',
          fontSize: 'clamp(0.8rem, 2vw, 1.1rem)',
          color: '#999999',
          marginTop: 16,
          opacity: lettersVisible ? 1 : 0,
          transition: `opacity 0.8s ease 0.5s`,
          letterSpacing: '0.15em',
        }}
      >
        {worldSubtitle || 'Begin by placing a single sound.'}
      </p>

      {/* Mode indicator — Cage is the default. A single pill label shows
          the current mode so the player knows what tapping will start.
          Appears only on world 0 (the root title). */}
      {worldIndex === 0 && (
        <div
          style={{
            marginTop: 24,
            opacity: lettersVisible ? 1 : 0,
            transition: 'opacity 1s ease 0.8s',
            pointerEvents: 'none',
          }}
        >
          <span
            style={{
              display: 'inline-block',
              padding: '4px 14px',
              borderRadius: 999,
              border: '1px solid rgba(255,255,255,0.22)',
              fontFamily: '"Cormorant Garamond", Georgia, serif',
              fontSize: 11,
              letterSpacing: '0.24em',
              color: '#cccccc',
              textTransform: 'uppercase',
            }}
          >
            {mode === 'zen' ? 'Free Play' : 'Cage · Level 1-1'}
          </span>
        </div>
      )}

      {/* World name (between-world transitions) — #888 passes WCAG AA (5.74:1) */}
      {worldName && worldName !== 'The Signal' && (
        <p
          style={{
            fontFamily: '"Cormorant Garamond", Georgia, serif',
            fontSize: 14,
            color: '#888888',
            marginTop: 8,
            opacity: lettersVisible ? 1 : 0,
            transition: `opacity 0.8s ease 0.7s`,
            letterSpacing: '0.1em',
          }}
        >
          {worldName}
        </p>
      )}

      {/* Sound warning */}
      <div
        style={{
          position: 'absolute',
          bottom: 'clamp(32px, 6vh, 64px)',
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
          opacity: lettersVisible ? 1 : 0,
          transition: 'opacity 1.2s ease 1s',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          {/* Speaker icon — decorative, meaning conveyed by adjacent text */}
          <svg
            aria-hidden="true"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#888"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          </svg>
          {/* #888 passes WCAG AA (5.74:1 on black) */}
          <span
            style={{
              fontFamily: '"Cormorant Garamond", Georgia, serif',
              fontSize: 13,
              color: '#888888',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
            }}
          >
            Wear headphones
          </span>
        </div>
        <span
          style={{
            fontFamily: '"Cormorant Garamond", Georgia, serif',
            fontStyle: 'italic',
            fontSize: 12,
            color: '#888888',
            letterSpacing: '0.08em',
          }}
        >
          Trust exactly what you hear.
        </span>
      </div>

      {/* Free Play switch — small italic link at the bottom. Cage is the
          default path; Free Play is the "or make music your own way" escape. */}
      {worldIndex === 0 && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            setMode(mode === 'zen' ? 'cage' : 'zen')
          }}
          onPointerDown={(e) => e.stopPropagation()}
          aria-label={mode === 'zen' ? 'Switch to Cage mode' : 'Switch to Free Play mode'}
          style={{
            position: 'absolute',
            bottom: 12,
            right: 16,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '8px 12px',
            minHeight: 44,
            fontFamily: '"Cormorant Garamond", Georgia, serif',
            fontStyle: 'italic',
            fontSize: 12,
            color: '#666',
            letterSpacing: '0.1em',
            pointerEvents: lettersVisible ? 'auto' : 'none',
            opacity: lettersVisible ? 0.85 : 0,
            transition: 'opacity 1s ease 1s, color 0.3s',
            WebkitTapHighlightColor: 'transparent',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = '#bbb' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#666' }}
        >
          {mode === 'zen' ? 'or play the puzzle →' : 'or free-play →'}
        </button>
      )}
    </div>
  )
}
