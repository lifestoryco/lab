import type { Metadata } from 'next'

const title = 'THE SHRINE — An archive of the awakened'
const description = 'One ensō, twenty masters, 1,800 years. A meditative archive of awakened teachers by Sean Ivins.'

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: 'https://www.handoffpack.com/lab/shrine' },
  openGraph: {
    title,
    description,
    url: 'https://www.handoffpack.com/lab/shrine',
    siteName: "Sean Ivins' Lab",
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title,
    description,
  },
}

export default function ShrineLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
