import type { ComponentType } from 'react'
import { AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react'

import type { ReviewStatus } from '@/types'

export type ReviewsTabType = 'pending' | 'my-submissions'

export const reviewStatusConfig: Record<
  ReviewStatus,
  { label: string; icon: ComponentType<{ className?: string }>; className: string }
> = {
  pending: {
    label: 'Pending',
    icon: Clock,
    className: 'bg-amber-100 text-amber-700',
  },
  approved: {
    label: 'Approved',
    icon: CheckCircle,
    className: 'bg-emerald-100 text-emerald-700',
  },
  rejected: {
    label: 'Rejected',
    icon: XCircle,
    className: 'bg-rose-100 text-rose-700',
  },
  cancelled: {
    label: 'Cancelled',
    icon: AlertCircle,
    className: 'bg-slate-100 text-slate-700',
  },
}
