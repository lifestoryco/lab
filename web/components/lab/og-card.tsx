import type { ReactElement } from 'react'

export interface OGCardProps {
  name: string
  tagline: string
  url: string
  gradient: string
  accent: string
  badge?: string
}

export const OG_SIZE = { width: 1200, height: 630 }
export const OG_CONTENT_TYPE = 'image/png'

export function OGCard({ name, tagline, url, gradient, accent, badge = 'LAB' }: OGCardProps): ReactElement {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: 80,
        background: gradient,
        color: '#fff',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div
          style={{
            width: 14,
            height: 14,
            borderRadius: 7,
            background: accent,
            boxShadow: `0 0 24px ${accent}`,
            display: 'flex',
          }}
        />
        <div
          style={{
            letterSpacing: 6,
            fontSize: 22,
            color: 'rgba(255,255,255,0.7)',
            textTransform: 'uppercase',
            fontWeight: 600,
            display: 'flex',
          }}
        >
          handoffpack.com / {badge.toLowerCase()}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            fontSize: 156,
            fontWeight: 800,
            letterSpacing: -4,
            lineHeight: 1,
            marginBottom: 28,
            display: 'flex',
          }}
        >
          {name}
        </div>
        <div
          style={{
            fontSize: 38,
            fontWeight: 400,
            lineHeight: 1.2,
            color: 'rgba(255,255,255,0.88)',
            maxWidth: 980,
            display: 'flex',
          }}
        >
          {tagline}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div
          style={{
            fontSize: 24,
            color: 'rgba(255,255,255,0.6)',
            display: 'flex',
          }}
        >
          {url}
        </div>
        <div
          style={{
            fontSize: 22,
            fontStyle: 'italic',
            color: 'rgba(255,255,255,0.55)',
            display: 'flex',
          }}
        >
          Sean Ivins
        </div>
      </div>
    </div>
  )
}
