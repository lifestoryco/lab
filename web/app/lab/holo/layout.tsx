import type { Metadata } from 'next'
import { Fraunces, Inter_Tight, JetBrains_Mono } from 'next/font/google'

const title = 'HOLO — Pokémon TCG price intelligence'
const description = 'Live comps, market signals, and flip-profit math for Pokémon TCG sealed product. Built by Sean Ivins.'

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: 'https://www.handoffpack.com/lab/holo' },
  openGraph: {
    title,
    description,
    url: 'https://www.handoffpack.com/lab/holo',
    siteName: "Sean Ivins' Lab",
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title,
    description,
  },
}


/**
 * Fraunces — editorial serif with a real voice. Variable font with opsz
 * (9-144), SOFT, and WONK axes. We use it for the HOLO wordmark, section
 * headings, and small-caps labels. Replaces the retro Press Start 2P +
 * Orbitron combo, which read as "vibe-coded" and amateurish for a serious
 * price-intelligence tool.
 */
const fraunces = Fraunces({
  subsets: ['latin'],
  weight: 'variable',
  style: ['normal', 'italic'],
  axes: ['SOFT', 'WONK', 'opsz'],
  variable: '--font-display',
  display: 'swap',
})

/**
 * Inter Tight — tighter default tracking than regular Inter, which suits
 * dense data/labels UIs. Covers body copy, labels, tab text, stats.
 */
const interTight = Inter_Tight({
  subsets: ['latin'],
  weight: 'variable',
  variable: '--font-body',
  display: 'swap',
})

/**
 * JetBrains Mono — prices, deltas, stat numerics. Tabular figures matter
 * when the whole UI is alignment-sensitive.
 */
const jetBrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: 'variable',
  variable: '--font-mono',
  display: 'swap',
})

export default function HoloLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div
      className={`${fraunces.variable} ${interTight.variable} ${jetBrainsMono.variable}`}
      style={{
        // Semantic aliases kept for backwards compatibility with the many
        // inline `var(--font-orbitron)` / `var(--font-press-start)` /
        // `var(--font-space)` references scattered through HoloPage.tsx.
        // Display refs now resolve to Fraunces; body to Inter Tight.
        '--holo-accent': '#fbbf24',
        '--font-orbitron': 'var(--font-display)',
        '--font-press-start': 'var(--font-display)',
        '--font-space': 'var(--font-body)',
      } as React.CSSProperties}
    >
      {children}
    </div>
  )
}
