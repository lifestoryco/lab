import { Cormorant_Garamond } from 'next/font/google'

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
