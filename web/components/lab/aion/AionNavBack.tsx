'use client'

import Link from 'next/link'

export default function AionNavBack() {
  return (
    <Link
      href="/lab"
      style={{
        position: 'fixed',
        top: 'max(20px, env(safe-area-inset-top, 20px))',
        left: '20px',
        zIndex: 30,
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        fontSize: '11px',
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        color: '#fff',
        textDecoration: 'none',
        opacity: 0.45,
        transition: 'opacity 0.3s ease',
        fontFamily: 'monospace',
      }}
      onMouseEnter={e => { e.currentTarget.style.opacity = '0.8' }}
      onMouseLeave={e => { e.currentTarget.style.opacity = '0.45' }}
      onFocus={e => { e.currentTarget.style.opacity = '0.8' }}
      onBlur={e => { e.currentTarget.style.opacity = '0.45' }}
    >
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M7.5 2.5L4 6l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Lab
    </Link>
  )
}
