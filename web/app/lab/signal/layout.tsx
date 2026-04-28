import type { Metadata } from 'next'
import { Cormorant_Garamond } from 'next/font/google'

const title = 'SIGNAL — Build worlds that play themselves'
const description = 'Generative isometric soundscapes — build worlds that play themselves. An interactive piece by Sean Ivins.'

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: 'https://www.handoffpack.com/lab/signal' },
  openGraph: {
    title,
    description,
    url: 'https://www.handoffpack.com/lab/signal',
    siteName: "Sean Ivins' Lab",
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title,
    description,
  },
}


const cormorant = Cormorant_Garamond({
  subsets: ['latin'],
  weight: ['300', '400', '600'],
  style: ['normal', 'italic'],
  display: 'swap',
  variable: '--font-cormorant',
})

export default function SignalLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <div className={cormorant.variable}>{children}</div>
}
