import type { Metadata } from 'next'

const title = "AION — Every moment you've ever been is still here"
const description = "Every moment you've ever been is still here, superimposed. A radial-time webcam piece by Sean Ivins."

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: 'https://www.handoffpack.com/lab/aion' },
  openGraph: {
    title,
    description,
    url: 'https://www.handoffpack.com/lab/aion',
    siteName: "Sean Ivins' Lab",
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title,
    description,
  },
}

export default function AionLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
