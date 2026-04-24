'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { useAionEngine, DEFAULT_CONTROLS, type AionControls } from './useAionEngine'
import AionPermission from './AionPermission'
import AionControlsPanel from './AionControls'
import AionAbout from './AionAbout'
import AionPulseHint from './AionPulseHint'
import AionNavBack from './AionNavBack'

type Phase = 'permission' | 'live'

// DEFAULT_CONTROLS imported from useAionEngine

export default function AionExperience() {
  const [phase, setPhase] = useState<Phase>('permission')
  const [controls, setControls] = useState<AionControls>(DEFAULT_CONTROLS)
  const [aboutOpen, setAboutOpen] = useState(false)

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const touchStartRef = useRef<{ x: number; y: number } | null>(null)

  const shouldStart = phase === 'live'
  const { videoReady, collapse } = useAionEngine(canvasRef, controls, shouldStart)

  // Resize canvas to fill viewport
  useEffect(() => {
    function resize() {
      const canvas = canvasRef.current
      if (!canvas) return
      // Render at reduced resolution for performance (pixel loop is O(W*H))
      const maxDim = 480
      const vw = window.innerWidth
      const vh = window.innerHeight
      const aspect = vw / vh
      let w: number, h: number
      if (vw > vh) {
        w = Math.min(maxDim, vw)
        h = Math.round(w / aspect)
      } else {
        h = Math.min(maxDim, vh)
        w = Math.round(h * aspect)
      }
      canvas.width = w
      canvas.height = h
      canvas.style.width = '100vw'
      canvas.style.height = '100vh'
    }

    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  // Touch/click handlers for collapse
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0]
    touchStartRef.current = { x: touch.clientX, y: touch.clientY }
  }, [])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (!touchStartRef.current) return
    const touch = e.changedTouches[0]
    const deltaY = Math.abs(touch.clientY - touchStartRef.current.y)
    const deltaX = Math.abs(touch.clientX - touchStartRef.current.x)

    if (deltaY < 12 && deltaX < 12) {
      collapse()
    }
    touchStartRef.current = null
  }, [collapse])

  const handleClick = useCallback(() => {
    collapse()
  }, [collapse])

  // Keyboard shortcuts
  useEffect(() => {
    if (phase !== 'live') return

    function handleKey(e: KeyboardEvent) {
      switch (e.key) {
        case ' ':
        case 'Enter':
          e.preventDefault()
          collapse()
          break
        case 'ArrowUp':
          e.preventDefault()
          setControls(c => ({ ...c, ringCount: Math.min(32, c.ringCount + 1) }))
          break
        case 'ArrowDown':
          e.preventDefault()
          setControls(c => ({ ...c, ringCount: Math.max(4, c.ringCount - 1) }))
          break
        case 'k':
        case 'K':
          setControls(c => {
            const cycle = [0, 3, 6, 12]
            const next = cycle[(cycle.indexOf(c.kaleidoscope) + 1) % cycle.length]
            return { ...c, kaleidoscope: next }
          })
          break
        case 'm':
        case 'M':
          setControls(c => ({
            ...c,
            moireIntensity: c.moireIntensity > 0.01 ? 0 : 0.4,
          }))
          break
        case 'i':
        case 'I':
          setControls(c => ({ ...c, invert: !c.invert }))
          break
      }
    }

    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [phase, collapse])

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: '#000',
        overflow: 'hidden',
        cursor: videoReady ? 'crosshair' : 'default',
        touchAction: 'none',
      }}
    >
      {/* Canvas — always mounted for sizing */}
      <canvas
        ref={canvasRef}
        onClick={videoReady ? handleClick : undefined}
        onTouchStart={videoReady ? handleTouchStart : undefined}
        onTouchEnd={videoReady ? handleTouchEnd : undefined}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          opacity: videoReady ? 1 : 0,
          transition: 'opacity 1.2s cubic-bezier(0.33, 1, 0.68, 1)',
        }}
      />

      {/* Permission screen */}
      {phase === 'permission' && (
        <AionPermission onGranted={() => setPhase('live')} />
      )}

      {/* UI overlays — only when video is actually rendering */}
      {videoReady && (
        <>
          <AionNavBack />

          {/* Info button */}
          <button
            onClick={() => setAboutOpen(true)}
            aria-label="About Aion"
            style={{
              position: 'fixed',
              top: 'max(20px, env(safe-area-inset-top, 20px))',
              right: '20px',
              zIndex: 30,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              opacity: 0.2,
              transition: 'opacity 0.3s ease',
              padding: '8px',
              color: '#fff',
            }}
            onMouseEnter={e => { e.currentTarget.style.opacity = '0.7' }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '0.2' }}
            onFocus={e => { e.currentTarget.style.opacity = '0.7' }}
            onBlur={e => { e.currentTarget.style.opacity = '0.2' }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="8.5" stroke="currentColor" strokeWidth="1.2" />
              <path d="M10 9v5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <circle cx="10" cy="6.5" r="0.8" fill="currentColor" />
            </svg>
          </button>

          <AionPulseHint />
          <AionControlsPanel controls={controls} onChange={setControls} />
          <AionAbout open={aboutOpen} onClose={() => setAboutOpen(false)} />
        </>
      )}
    </div>
  )
}
