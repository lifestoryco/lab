'use client'

import { useState, useEffect } from 'react'

export default function AionPulseHint() {
  const [visible, setVisible] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    // Show after 4 seconds
    const showTimer = setTimeout(() => setVisible(true), 4000)
    // Hide after 10 seconds total (6 seconds visible)
    const hideTimer = setTimeout(() => {
      setVisible(false)
      setDismissed(true)
    }, 10000)

    return () => {
      clearTimeout(showTimer)
      clearTimeout(hideTimer)
    }
  }, [])

  if (dismissed || !visible) return null

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 25,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        animation: 'aion-hint-fade 6s ease forwards',
      }}
    >
      {/* Expanding rings */}
      <div style={{ position: 'relative', width: '80px', height: '80px', marginBottom: '20px' }}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: '1px solid rgba(167,139,250,0.5)',
            animation: 'aion-hint-ring 2.5s ease-out infinite',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: '1px solid rgba(167,139,250,0.3)',
            animation: 'aion-hint-ring 2.5s ease-out infinite 1s',
          }}
        />
      </div>

      <p
        style={{
          fontSize: '10px',
          letterSpacing: '0.2em',
          color: 'rgba(148,163,184,0.9)',
          textTransform: 'uppercase',
          fontFamily: 'monospace',
          backgroundColor: 'rgba(5,5,5,0.3)',
          padding: '6px 14px',
          borderRadius: '4px',
        }}
      >
        TOUCH TO COLLAPSE TIME
      </p>

      <style>{`
        @keyframes aion-hint-ring {
          0% { transform: scale(1); opacity: 0.6; }
          100% { transform: scale(2.5); opacity: 0; }
        }
        @keyframes aion-hint-fade {
          0% { opacity: 0; }
          10% { opacity: 1; }
          85% { opacity: 1; }
          100% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}
