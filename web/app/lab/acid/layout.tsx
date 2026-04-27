import type { Metadata } from 'next'

const title = 'ACID — 22 living formulas in ASCII light'
const description = '22 living formulas rendered in ASCII light. An interactive generative experiment by Sean Ivins.'

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: 'https://www.handoffpack.com/lab/acid' },
  openGraph: {
    title,
    description,
    url: 'https://www.handoffpack.com/lab/acid',
    siteName: "Sean Ivins' Lab",
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title,
    description,
  },
}

export default function AcidLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
