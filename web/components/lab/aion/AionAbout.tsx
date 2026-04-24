'use client'

import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import Link from 'next/link'

interface AionAboutProps {
  open: boolean
  onClose: () => void
}

export default function AionAbout({ open, onClose }: AionAboutProps) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])

  if (!open || !mounted) return null

  return createPortal(
    <div
      onClick={onClose}
      role="presentation"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.82)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        zIndex: 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        animation: 'aion-fade-in 300ms ease forwards',
        cursor: 'pointer',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-labelledby="aion-about-title"
        aria-modal="true"
        style={{
          maxWidth: '420px',
          textAlign: 'center',
          cursor: 'default',
        }}
      >
        <h2
          id="aion-about-title"
          style={{
            fontSize: 'clamp(28px, 5vw, 36px)',
            fontWeight: 300,
            color: '#e2e2e2',
            letterSpacing: '0.15em',
            marginBottom: '24px',
          }}
        >
          AION
        </h2>

        <p
          style={{
            fontSize: '15px',
            fontWeight: 300,
            color: '#94A3B8',
            lineHeight: 1.8,
            marginBottom: '12px',
            fontStyle: 'italic',
          }}
        >
          In Greek myth, Aion is cyclical time — the kind that breathes and returns.
          Not the arrow of Kronos, but the wheel.
        </p>

        <p
          style={{
            fontSize: '14px',
            fontWeight: 300,
            color: '#64748B',
            lineHeight: 1.7,
            marginBottom: '36px',
          }}
        >
          Your face is the center. The rings behind you are memory.
          Move, and watch time ripple outward.
          Touch the screen to collapse it all back to now.
        </p>

        <div style={{ marginBottom: '28px' }}>
          <Link
            href="/lab"
            style={{
              fontSize: '12px',
              letterSpacing: '0.12em',
              color: '#64748B',
              textDecoration: 'none',
              padding: '8px 20px',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '8px',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'rgba(124,58,237,0.3)'
              e.currentTarget.style.color = '#A78BFA'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'
              e.currentTarget.style.color = '#64748B'
            }}
            onFocus={e => {
              e.currentTarget.style.borderColor = 'rgba(124,58,237,0.3)'
              e.currentTarget.style.color = '#A78BFA'
            }}
            onBlur={e => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'
              e.currentTarget.style.color = '#64748B'
            }}
          >
            BACK TO LAB
          </Link>
        </div>

        <p style={{ fontSize: '11px', letterSpacing: '0.12em', color: 'rgba(71,85,105,0.7)' }}>
          Made by Sean Ivins
        </p>

        <p style={{ fontSize: '11px', color: 'rgba(71,85,105,0.4)', marginTop: '20px' }}>
          Tap anywhere to close
        </p>
      </div>

      <style>{`
        @keyframes aion-fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>,
    document.body,
  )
}
