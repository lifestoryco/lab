'use client'

// Shown when WebGL init fails or the R3F Canvas throws mid-run.

export default function SceneFallback() {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: '#000',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 32,
        textAlign: 'center',
      }}
    >
      <div>
        <p
          style={{
            fontFamily: '"Cormorant Garamond", Georgia, serif',
            fontSize: 'clamp(1.2rem, 3vw, 1.8rem)',
            color: '#fff',
            letterSpacing: '0.18em',
            margin: 0,
          }}
        >
          SIGNAL
        </p>
        <p
          style={{
            fontFamily: '"Cormorant Garamond", Georgia, serif',
            fontStyle: 'italic',
            fontSize: 14,
            color: '#888',
            marginTop: 16,
            letterSpacing: '0.1em',
          }}
        >
          requires a modern browser with WebGL.
        </p>
      </div>
    </div>
  )
}
