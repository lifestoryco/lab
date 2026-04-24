import type { Metadata } from 'next'
import SignalPage from '@/components/lab/signal/SignalPage'

export const metadata: Metadata = {
  title: 'Signal — Sean\'s Lab',
  description: 'Build worlds that play themselves.',
  openGraph: {
    title: 'SIGNAL',
    description: 'Build worlds that play themselves.',
    images: [{ url: '/api/og/signal', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'SIGNAL',
    description: 'Build worlds that play themselves.',
    images: ['/api/og/signal'],
  },
}

export default function SignalRoute() {
  return <SignalPage />
}
