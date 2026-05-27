import type { ComponentType } from 'react';
import { AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';

import type { ReviewRequest, ReviewStatus } from '@/types';

import { getPendingReviewWorkflowStatus, type PendingReviewWorkflowStatus } from './reviewProgress';

export type ReviewsTabType = 'pending' | 'my-submissions';
export type ReviewDisplayStatus = ReviewStatus | PendingReviewWorkflowStatus | 'pending_editor';

export const reviewStatusConfig: Record<
  ReviewDisplayStatus,
  { label: string; icon: ComponentType<{ className?: string }>; className: string }
> = {
  new: {
    label: 'New',
    icon: Clock,
    className: 'bg-blue-100 text-blue-700',
  },
  in_progress: {
    label: 'In Progress',
    icon: AlertCircle,
    className: 'bg-amber-100 text-amber-700',
  },
  pending_editor: {
    label: 'Pending editor',
    icon: AlertCircle,
    className: 'bg-violet-100 text-violet-700',
  },
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
    label: 'Sent back for changes',
    icon: XCircle,
    className: 'bg-rose-100 text-rose-700',
  },
  cancelled: {
    label: 'Cancelled',
    icon: AlertCircle,
    className: 'bg-slate-100 text-slate-700',
  },
};

export function getReviewDisplayStatus(
  review: Pick<ReviewRequest, 'id' | 'status'>,
  activeTab: ReviewsTabType
): ReviewDisplayStatus {
  if (activeTab === 'pending' && review.status === 'pending') {
    return getPendingReviewWorkflowStatus(review.id);
  }

  if (activeTab === 'my-submissions' && review.status === 'rejected') {
    return 'pending_editor';
  }

  return review.status;
}
