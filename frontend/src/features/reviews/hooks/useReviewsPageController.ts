import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { useMySubmissionsQuery, usePendingReviewsQuery } from '@/hooks/useReviewQueries'
import { queryKeys } from '@/lib/queryKeys'
import type { ReviewRequest, ReviewStatus } from '@/types'

import type { ReviewsTabType } from '../constants'
import { reviewsUseCases } from '../useCases/reviewsUseCases'

export function useReviewsPageController() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<ReviewsTabType>('pending')
  const [selectedReview, setSelectedReview] = useState<ReviewRequest | null>(null)
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | ''>('')

  const { data: pendingData, isLoading: pendingLoading } = usePendingReviewsQuery(
    activeTab === 'pending',
  )
  const { data: submissionsData, isLoading: submissionsLoading } = useMySubmissionsQuery(
    statusFilter,
    activeTab === 'my-submissions',
  )

  const approveMutation = useMutation({
    mutationFn: ({ reviewId, comments }: { reviewId: number; comments?: string }) =>
      reviewsUseCases.approveReview(reviewId, comments),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all })
      setSelectedReview(null)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ reviewId, comments }: { reviewId: number; comments: string }) =>
      reviewsUseCases.rejectReview(reviewId, comments),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all })
      setSelectedReview(null)
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (reviewId: number) => reviewsUseCases.cancelReview(reviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all })
    },
  })

  const reviews = activeTab === 'pending' ? pendingData?.items : submissionsData?.items
  const isLoading = activeTab === 'pending' ? pendingLoading : submissionsLoading
  const total = activeTab === 'pending' ? pendingData?.total : submissionsData?.total

  const handleCancelReview = (reviewId: number) => {
    if (confirm('Are you sure you want to cancel this submission?')) {
      cancelMutation.mutate(reviewId)
    }
  }

  const closeSelectedReview = () => setSelectedReview(null)
  const openSelectedReview = (review: ReviewRequest) => setSelectedReview(review)

  const approveSelectedReview = (comments?: string) => {
    if (!selectedReview) {
      return
    }
    approveMutation.mutate({ reviewId: selectedReview.id, comments })
  }

  const rejectSelectedReview = (comments: string) => {
    if (!selectedReview) {
      return
    }
    rejectMutation.mutate({ reviewId: selectedReview.id, comments })
  }

  return {
    activeTab,
    setActiveTab,
    selectedReview,
    openSelectedReview,
    closeSelectedReview,
    statusFilter,
    setStatusFilter,
    pendingData,
    reviews,
    isLoading,
    total,
    cancelMutation,
    handleCancelReview,
    approveSelectedReview,
    rejectSelectedReview,
    dialogLoading: approveMutation.isPending || rejectMutation.isPending,
  }
}
