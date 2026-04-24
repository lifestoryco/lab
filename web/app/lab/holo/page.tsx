import type { Metadata } from 'next'
import HoloPage from '@/components/lab/holo/HoloPage'

export const metadata: Metadata = {
  title: 'HOLO — Pokémon TCG Price Intelligence',
  description: 'Real-time market comps, buy/sell signals, and flip profit for Pokémon cards.',
}

export default function HoloRoute() {
  return <HoloPage />
}
