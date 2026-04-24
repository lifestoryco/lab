import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { decodeShareState, MAX_HASH_CHARS } from '@/components/lab/signal/utils/shareState'
import ResultScreen from '@/components/lab/signal/ui/ResultScreen'

interface Props {
  params: { hash: string }
}

function safeHash(h: string): string | null {
  if (typeof h !== 'string' || h.length === 0) return null
  if (h.length > MAX_HASH_CHARS) return null
  return h
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const safe = safeHash(params.hash)
  const state = safe ? decodeShareState(safe) : null
  const title = state?.completed ? 'SIGNAL — You heard it.' : 'SIGNAL'
  const description = state
    ? `${state.blocks.length} blocks, ${state.totalChains} chains.`
    : 'Build worlds that play themselves.'
  const ogUrl = safe
    ? `/api/og/signal?h=${encodeURIComponent(safe)}`
    : '/api/og/signal'

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      images: [{ url: ogUrl, width: 1200, height: 630 }],
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [ogUrl],
    },
  }
}

export default function SharedSignalPage({ params }: Props) {
  const safe = safeHash(params.hash)
  if (!safe) notFound()
  const state = decodeShareState(safe)
  if (!state) notFound()
  return (
    <div style={{ backgroundColor: '#000', minHeight: '100vh' }}>
      <ResultScreen state={state} mode="viewer" />
    </div>
  )
}
