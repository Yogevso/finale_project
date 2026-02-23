import type {
  FeedbackDetailResponse,
  FeedbackListManagementResponse,
  FeedbackStatus,
  FeedbackType,
  ReviewAction,
  ReviewListResponse,
  ReviewRequest,
  ReviewSubmit,
} from '@/types'
import type { ApiHttpClient, Constructor } from './httpClient'

export const ReviewsApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async submitForReview(documentId: number, data: ReviewSubmit): Promise<ReviewRequest> {
      const { data: response } = await this.client.post<ReviewRequest>(
        `/reviews/documents/${documentId}/submit`,
        data,
      )
      return response
    }

    async getPendingReviews(params?: { page?: number; per_page?: number }): Promise<ReviewListResponse> {
      const { data } = await this.client.get<ReviewListResponse>('/reviews/pending', { params })
      return data
    }

    async getMySubmissions(params?: {
      page?: number
      per_page?: number
      status?: string
    }): Promise<ReviewListResponse> {
      const { data } = await this.client.get<ReviewListResponse>('/reviews/my-submissions', { params })
      return data
    }

    async getReview(reviewId: number): Promise<ReviewRequest> {
      const { data } = await this.client.get<ReviewRequest>(`/reviews/${reviewId}`)
      return data
    }

    async approveReview(reviewId: number, data: ReviewAction): Promise<ReviewRequest> {
      const { data: response } = await this.client.post<ReviewRequest>(`/reviews/${reviewId}/approve`, data)
      return response
    }

    async rejectReview(reviewId: number, data: { comments: string }): Promise<ReviewRequest> {
      const { data: response } = await this.client.post<ReviewRequest>(`/reviews/${reviewId}/reject`, data)
      return response
    }

    async cancelReview(reviewId: number): Promise<ReviewRequest> {
      const { data } = await this.client.post<ReviewRequest>(`/reviews/${reviewId}/cancel`)
      return data
    }

    async getDocumentReviewHistory(
      documentId: number,
      params?: { page?: number; per_page?: number },
    ): Promise<ReviewListResponse> {
      const { data } = await this.client.get<ReviewListResponse>(
        `/reviews/documents/${documentId}/history`,
        { params },
      )
      return data
    }

    async getAllFeedback(params?: {
      page?: number
      per_page?: number
      status?: FeedbackStatus
      type?: FeedbackType
      company_id?: number
      search?: string
    }): Promise<FeedbackListManagementResponse> {
      const { data } = await this.client.get<FeedbackListManagementResponse>('/feedback', { params })
      return data
    }

    async getFeedback(feedbackId: number): Promise<FeedbackDetailResponse> {
      const { data } = await this.client.get<FeedbackDetailResponse>(`/feedback/${feedbackId}`)
      return data
    }

    async respondToFeedback(feedbackId: number, response: string): Promise<FeedbackDetailResponse> {
      const { data } = await this.client.post<FeedbackDetailResponse>(
        `/feedback/${feedbackId}/respond`,
        { response },
      )
      return data
    }

    async updateFeedbackStatus(
      feedbackId: number,
      status: FeedbackStatus,
    ): Promise<FeedbackDetailResponse> {
      const { data } = await this.client.put<FeedbackDetailResponse>(`/feedback/${feedbackId}/status`, {
        status,
      })
      return data
    }

    async getManagementFeedbackStats(): Promise<{
      total: number
      pending: number
      responded: number
      closed: number
      by_type: Record<string, number>
    }> {
      const { data } = await this.client.get('/feedback/stats/summary')
      return data
    }
  }

