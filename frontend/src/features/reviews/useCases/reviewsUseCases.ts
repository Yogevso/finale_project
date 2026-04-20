import { api } from '@/lib/api'
import type { ReviewFeedback, ReviewRequest, ReviewSectionComment } from '@/types'

export type ReviewsUseCasesClient = Pick<typeof api, 'approveReview' | 'rejectReview' | 'cancelReview'>

export interface ReviewDecisionInput {
  comments?: string
  generalComment?: string
  sectionComments?: ReviewSectionComment[]
}

function buildReviewFeedback(input: ReviewDecisionInput): ReviewFeedback | undefined {
  const generalComment = (input.generalComment || '').trim()
  const sectionComments = (input.sectionComments || []).filter(
    (section) => (section.comment || '').trim().length > 0,
  )

  if (!generalComment && sectionComments.length === 0) {
    return undefined
  }

  return {
    general_comment: generalComment || undefined,
    section_comments: sectionComments.map((section) => ({
      title: section.title,
      comment: section.comment.trim(),
      anchor_id: section.anchor_id,
      severity: section.severity || 'medium',
      action_item_assignee: section.action_item_assignee,
    })),
  }
}

export function createReviewsUseCases(client: ReviewsUseCasesClient = api) {
  return {
    approveReview(reviewId: number, input: ReviewDecisionInput = {}): Promise<ReviewRequest> {
      return client.approveReview(reviewId, {
        comments: input.comments,
        review_feedback: buildReviewFeedback(input),
      })
    },

    rejectReview(reviewId: number, input: ReviewDecisionInput): Promise<ReviewRequest> {
      return client.rejectReview(reviewId, {
        comments: input.comments,
        review_feedback: buildReviewFeedback(input),
      })
    },

    cancelReview(reviewId: number): Promise<ReviewRequest> {
      return client.cancelReview(reviewId)
    },
  }
}

export const reviewsUseCases = createReviewsUseCases()
