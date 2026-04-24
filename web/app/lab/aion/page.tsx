import type { Metadata } from 'next'
import AionExperience from '@/components/lab/aion/AionExperience'

export const metadata: Metadata = {
  title: 'Aion — Sean\'s Lab',
  description: 'Every moment you\'ve ever been is still here, superimposed.',
}

export default function AionRoute() {
  return <AionExperience />
}
