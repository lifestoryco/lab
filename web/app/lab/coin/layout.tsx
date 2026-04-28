import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Coin — Career Ops',
  description: 'Sean Ivins career pipeline — discover, score, tailor, track.',
}

export default function CoinLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
