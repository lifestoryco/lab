'use client'

import { useState } from 'react'

type PermissionPhase = 'prompt' | 'waiting' | 'denied'

interface AionPermissionProps {
  onGranted: () => void
}

export default function AionPermission({ onGranted }: AionPermissionProps) {
  const [phase, setPhase] = useState<PermissionPhase>('prompt')

  async function requestCamera() {
    setPhase('waiting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' },
        audio: false,
      })
      stream.getTracks().forEach(t => t.stop())
      onGranted()
    } catch {
      setPhase('denied')
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: '#050505',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        animation: 'aion-fade-in 1200ms ease forwards',
        overflow: 'hidden',
      }}
    >
      {/* Animated concentric rings background */}
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
        {[1, 2, 3, 4, 5].map(i => (
          <div
            key={i}
            style={{
              position: 'absolute',
              width: `${i * 140}px`,
              height: `${i * 140}px`,
              borderRadius: '50%',
              border: `1px solid rgba(201,169,98,${0.06 - i * 0.008})`,
              animation: `aion-breathe ${6 + i * 1.5}s ease-in-out infinite ${i * 0.8}s`,
            }}
          />
        ))}
      </div>

      {/* Greek meander border — top */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
        background: 'linear-gradient(90deg, transparent 0%, rgba(201,169,98,0.3) 20%, rgba(201,169,98,0.5) 50%, rgba(201,169,98,0.3) 80%, transparent 100%)',
      }} />
      {/* Greek meander border — bottom */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: '2px',
        background: 'linear-gradient(90deg, transparent 0%, rgba(201,169,98,0.3) 20%, rgba(201,169,98,0.5) 50%, rgba(201,169,98,0.3) 80%, transparent 100%)',
      }} />

      {phase === 'prompt' && (
        <div style={{
          textAlign: 'center',
          maxWidth: '440px',
          padding: '0 32px',
          position: 'relative',
          zIndex: 2,
          animation: 'aion-fade-up 1000ms ease forwards',
        }}>
          {/* Decorative line above */}
          <div style={{
            width: '60px', height: '1px', margin: '0 auto 28px',
            background: 'linear-gradient(90deg, transparent, rgba(201,169,98,0.6), transparent)',
          }} />

          {/* Greek title */}
          <div style={{
            fontSize: 'clamp(10px, 2.5vw, 13px)',
            letterSpacing: '0.5em',
            color: 'rgba(201,169,98,0.5)',
            marginBottom: '12px',
            fontFamily: 'monospace',
          }}>
            AI&Omega;N
          </div>

          <h1 style={{
            fontSize: 'clamp(36px, 8vw, 64px)',
            fontWeight: 200,
            color: '#E8DCC8',
            marginBottom: '6px',
            letterSpacing: '0.35em',
            lineHeight: 1,
          }}>
            AION
          </h1>

          <div style={{
            fontSize: 'clamp(11px, 2.5vw, 14px)',
            letterSpacing: '0.25em',
            color: 'rgba(201,169,98,0.7)',
            marginBottom: '40px',
            fontWeight: 300,
          }}>
            TEMPORAL MIRROR
          </div>

          {/* Philosophical copy */}
          <p style={{
            fontSize: 'clamp(13px, 2.8vw, 15px)',
            color: 'rgba(232,220,200,0.7)',
            lineHeight: 1.8,
            marginBottom: '12px',
            fontWeight: 300,
            letterSpacing: '0.02em',
          }}>
            The eternal now. Past and present, woven into light.
          </p>

          <p style={{
            fontSize: 'clamp(11px, 2.2vw, 12px)',
            color: 'rgba(232,220,200,0.35)',
            lineHeight: 1.7,
            marginBottom: '48px',
            fontWeight: 300,
            letterSpacing: '0.03em',
            fontStyle: 'italic',
            maxWidth: '340px',
            margin: '0 auto 48px',
          }}>
            What was, is. What is, passes. Between being and non-being,
            your reflection holds the shape of time itself.
          </p>

          {/* Decorative meander pattern */}
          <div style={{
            display: 'flex', justifyContent: 'center', gap: '3px', marginBottom: '36px', opacity: 0.25,
          }}>
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} style={{
                width: '12px', height: '12px',
                border: '1px solid rgba(201,169,98,0.8)',
                borderRadius: i % 2 === 0 ? '0' : '50%',
              }} />
            ))}
          </div>

          {/* Camera button */}
          <button
            onClick={requestCamera}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '12px',
              padding: '16px 40px',
              fontSize: '13px',
              fontWeight: 400,
              letterSpacing: '0.3em',
              color: 'rgba(201,169,98,0.9)',
              backgroundColor: 'rgba(201,169,98,0.06)',
              border: '1px solid rgba(201,169,98,0.25)',
              borderRadius: '2px',
              cursor: 'pointer',
              transition: 'all 0.4s ease',
              textTransform: 'uppercase',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.backgroundColor = 'rgba(201,169,98,0.12)'
              e.currentTarget.style.borderColor = 'rgba(201,169,98,0.5)'
              e.currentTarget.style.transform = 'scale(1.02)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.backgroundColor = 'rgba(201,169,98,0.06)'
              e.currentTarget.style.borderColor = 'rgba(201,169,98,0.25)'
              e.currentTarget.style.transform = 'scale(1)'
            }}
            onFocus={e => {
              e.currentTarget.style.backgroundColor = 'rgba(201,169,98,0.12)'
              e.currentTarget.style.borderColor = 'rgba(201,169,98,0.5)'
            }}
            onBlur={e => {
              e.currentTarget.style.backgroundColor = 'rgba(201,169,98,0.06)'
              e.currentTarget.style.borderColor = 'rgba(201,169,98,0.25)'
            }}
          >
            <EyeIcon />
            Begin
          </button>

          {/* Privacy note */}
          <p style={{
            fontSize: '10px',
            color: 'rgba(232,220,200,0.2)',
            marginTop: '24px',
            letterSpacing: '0.15em',
          }}>
            CAMERA ONLY &middot; NOTHING RECORDED &middot; NOTHING SENT
          </p>
        </div>
      )}

      {phase === 'waiting' && (
        <div style={{ position: 'relative', width: '120px', height: '120px' }}>
          {[0, 1, 2].map(i => (
            <div
              key={i}
              style={{
                position: 'absolute',
                inset: `${i * 8}px`,
                borderRadius: '50%',
                border: '1px solid rgba(201,169,98,0.3)',
                animation: `aion-pulse-ring 2.5s ease-in-out infinite ${i * 0.6}s`,
              }}
            />
          ))}
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '10px',
            letterSpacing: '0.3em',
            color: 'rgba(201,169,98,0.5)',
          }}>
            OPENING
          </div>
        </div>
      )}

      {phase === 'denied' && (
        <div style={{ textAlign: 'center', maxWidth: '340px', padding: '0 24px', position: 'relative', zIndex: 2 }}>
          <p style={{
            fontSize: '16px',
            fontWeight: 300,
            color: 'rgba(232,220,200,0.6)',
            lineHeight: 1.7,
            marginBottom: '32px',
            letterSpacing: '0.04em',
          }}>
            Aion requires sight to reveal time.
          </p>
          <button
            onClick={() => setPhase('prompt')}
            style={{
              padding: '12px 32px',
              fontSize: '12px',
              letterSpacing: '0.2em',
              color: 'rgba(201,169,98,0.7)',
              backgroundColor: 'transparent',
              border: '1px solid rgba(201,169,98,0.2)',
              borderRadius: '2px',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(201,169,98,0.5)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(201,169,98,0.2)' }}
          >
            TRY AGAIN
          </button>
        </div>
      )}

      <style>{`
        @keyframes aion-fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes aion-fade-up {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes aion-pulse-ring {
          0% { transform: scale(1); opacity: 0.6; }
          100% { transform: scale(1.6); opacity: 0; }
        }
        @keyframes aion-breathe {
          0%, 100% { transform: scale(1); opacity: 0.4; }
          50% { transform: scale(1.08); opacity: 0.8; }
        }
      `}</style>
    </div>
  )
}

function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}
