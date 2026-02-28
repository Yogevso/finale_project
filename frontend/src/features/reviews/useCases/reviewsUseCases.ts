import { api } from '@/lib/api'
import type { ReviewRequest } from '@/types'

export type ReviewsUseCasesClient = Pick<typeof api, 'approveReview' | 'rejectReview' | 'cancelReview'>

export function createReviewsUseCases(client: ReviewsUseCasesClient = api) {
  return {
    approveReview(reviewId: number, comments?: string): Promise<ReviewRequest> {
      return client.approveReview(reviewId, { comments })
    },

    rejectReview(reviewId: number, comments: string): Promise<ReviewRequest> {
      return client.rejectReview(reviewId, { comments })
    },

    cancelReview(reviewId: number): Promise<ReviewRequest> {
      return client.cancelReview(reviewId)
    },
  }
}

export const reviewsUseCases = createReviewsUseCases()

