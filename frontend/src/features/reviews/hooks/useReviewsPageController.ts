import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';

import { useMySubmissionsQuery, usePendingReviewsQuery } from '@/hooks/useReviewQueries';
import { queryKeys } from '@/lib/queryKeys';
import { extractApiErrorMessage, useToast } from '@/lib/toast';
import type { ReviewRequest, ReviewStatus } from '@/types';

import type { ReviewsTabType } from '../constants';
import { clearReviewProgress } from '../reviewProgress';
import { reviewsUseCases, type ReviewDecisionInput } from '../useCases/reviewsUseCases';

export function useReviewsPageController() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<ReviewsTabType>('pending');
  const [selectedReview, setSelectedReview] = useState<ReviewRequest | null>(null);
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | ''>('');
  const documentFilterParam = searchParams.get('document_id');
  const parsedDocumentFilterId =
    documentFilterParam && Number.isInteger(Number(documentFilterParam))
      ? Number(documentFilterParam)
      : null;
  const documentFilterId = parsedDocumentFilterId && parsedDocumentFilterId > 0
    ? parsedDocumentFilterId
    : null;

  const pendingQuery = usePendingReviewsQuery(documentFilterId ?? undefined, activeTab === 'pending');
  const submissionsQuery = useMySubmissionsQuery(
    statusFilter,
    documentFilterId ?? undefined,
    activeTab === 'my-submissions',
  );
  const { data: pendingData, isLoading: pendingLoading } = pendingQuery;
  const { data: submissionsData, isLoading: submissionsLoading } = submissionsQuery;

  const approveMutation = useMutation({
    mutationFn: ({ reviewId, decision }: { reviewId: number; decision: ReviewDecisionInput }) =>
      reviewsUseCases.approveReview(reviewId, decision),
    onSuccess: (_result, variables) => {
      clearReviewProgress(variables.reviewId);
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all });
      setSelectedReview(null);
    },
    onError: (error: unknown) => {
      toast.error('Failed to approve review', extractApiErrorMessage(error, 'Please try again.'));
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ reviewId, decision }: { reviewId: number; decision: ReviewDecisionInput }) =>
      reviewsUseCases.rejectReview(reviewId, decision),
    onSuccess: (_result, variables) => {
      clearReviewProgress(variables.reviewId);
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all });
      setSelectedReview(null);
    },
    onError: (error: unknown) => {
      toast.error('Failed to reject review', extractApiErrorMessage(error, 'Please try again.'));
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (reviewId: number) => reviewsUseCases.cancelReview(reviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reviews.all });
    },
    onError: (error: unknown) => {
      toast.error('Failed to cancel review', extractApiErrorMessage(error, 'Please try again.'));
    },
  });

  const currentQuery = activeTab === 'pending' ? pendingQuery : submissionsQuery;
  const reviews = activeTab === 'pending' ? pendingData?.items : submissionsData?.items;
  const isLoading = activeTab === 'pending' ? pendingLoading : submissionsLoading;
  const total = activeTab === 'pending' ? pendingData?.total : submissionsData?.total;

  const handleCancelReview = (reviewId: number) => {
    if (confirm('Are you sure you want to cancel this submission?')) {
      cancelMutation.mutate(reviewId);
    }
  };

  const closeSelectedReview = () => setSelectedReview(null);
  const openSelectedReview = (review: ReviewRequest) => setSelectedReview(review);

  const approveSelectedReview = (decision: ReviewDecisionInput) => {
    if (!selectedReview) {
      return;
    }
    approveMutation.mutate({ reviewId: selectedReview.id, decision });
  };

  const rejectSelectedReview = (decision: ReviewDecisionInput) => {
    if (!selectedReview) {
      return;
    }
    rejectMutation.mutate({ reviewId: selectedReview.id, decision });
  };

  const clearDocumentFilter = () => {
    const next = new URLSearchParams(searchParams);
    next.delete('document_id');
    setSearchParams(next, { replace: true });
  };

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
    isError: currentQuery.isError,
    refetchCurrent: currentQuery.refetch,
    total,
    cancelMutation,
    handleCancelReview,
    approveSelectedReview,
    rejectSelectedReview,
    dialogLoading: approveMutation.isPending || rejectMutation.isPending,
    documentFilterId,
    clearDocumentFilter,
  };
}
