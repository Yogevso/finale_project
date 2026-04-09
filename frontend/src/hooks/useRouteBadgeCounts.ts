import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { useChatUnreadCount } from '@/features/chat/useChatUnreadCount'
import { api } from '@/lib/api'
import type { UserRole } from '@/types'

const REVIEW_BADGE_ROLES: UserRole[] = ['system_admin', 'admin', 'manager', 'editor']
const FEEDBACK_BADGE_ROLES: UserRole[] = ['system_admin', 'admin', 'manager']
const SUPPORT_BADGE_ROLES: UserRole[] = ['system_admin', 'admin', 'manager']

export function useRouteBadgeCounts(role: UserRole | null) {
  const isCustomer = role === 'customer'
  const chatUnreadCount = useChatUnreadCount(isCustomer ? 'portal' : 'internal')
  const canSeeReviews = role !== null && REVIEW_BADGE_ROLES.includes(role)
  const canSeeFeedback = role !== null && FEEDBACK_BADGE_ROLES.includes(role)
  const canSeeSupport = role !== null && SUPPORT_BADGE_ROLES.includes(role)

  const { data: pendingReviews } = useQuery({
    queryKey: ['nav-badges', 'reviews', role],
    queryFn: () => api.getPendingReviews({ page: 1, per_page: 1 }),
    enabled: canSeeReviews,
    refetchInterval: 30000,
    staleTime: 10000,
  })

  const { data: feedbackStats } = useQuery({
    queryKey: ['nav-badges', 'feedback', role],
    queryFn: () => api.getManagementFeedbackStats(),
    enabled: canSeeFeedback,
    refetchInterval: 30000,
    staleTime: 10000,
  })

  const { data: supportSummary } = useQuery({
    queryKey: ['nav-badges', 'support', role],
    queryFn: () => api.getSupportTicketSummary(),
    enabled: canSeeSupport,
    refetchInterval: 30000,
    staleTime: 10000,
  })

  const badges = useMemo<Record<string, number>>(() => {
    const next: Record<string, number> = {}
    if (isCustomer) {
      next['/portal/chat'] = chatUnreadCount
      return next
    }

    next['/chat'] = chatUnreadCount
    next['/reviews'] = pendingReviews?.total ?? 0
    next['/admin/feedback'] = feedbackStats?.pending ?? 0
    next['/support'] = supportSummary?.nav_badge_count ?? 0
    return next
  }, [chatUnreadCount, feedbackStats?.pending, isCustomer, pendingReviews?.total, supportSummary?.nav_badge_count])

  return {
    badges,
    getBadgeCount: (path: string) => badges[path] ?? 0,
    supportSummary: supportSummary ?? null,
  }
}
