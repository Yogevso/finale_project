import type {
  FeedbackDetailResponse,
  FeedbackListManagementResponse,
  FeedbackStatus,
  FeedbackType,
  PreApprovePolicy,
  ReviewAction,
  ReviewListResponse,
  ReviewRequest,
  ReviewSubmit,
  User,
} from '@/types'
import {
  type FeedbackDetailResponseDto,
  type FeedbackListManagementResponseDto,
  type ManagementFeedbackStatsDto,
  type PreApprovePolicyDto,
  type ReviewActionDto,
  type ReviewListResponseDto,
  type ReviewRequestDto,
  type ReviewSubmitDto,
  mapFeedbackDetailResponseDto,
  mapFeedbackListManagementResponseDto,
  mapManagementFeedbackStatsDto,
  mapPreApprovePolicyDto,
  mapReviewListResponseDto,
  mapReviewRequestDto,
  toReviewActionDto,
  toReviewSubmitDto,
} from './dto'
import type { ApiClientBase, Constructor } from './httpClient'

export const ReviewsApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
    async submitForReview(documentId: number, data: ReviewSubmit): Promise<ReviewRequest> {
      const payload = toReviewSubmitDto(data)
      const { data: response } = await this.client.post<ReviewRequestDto>(
        `/reviews/documents/${documentId}/submit`,
        payload as ReviewSubmitDto,
      )
      return mapReviewRequestDto(response)
    }

    async getReviewerCandidates(documentId?: number): Promise<User[]> {
      const params = documentId !== undefined ? { document_id: documentId } : undefined
      const { data } = await this.client.get<User[]>('/reviews/reviewer-candidates', { params })
      return data
    }

    async getPendingReviews(params?: {
      page?: number
      per_page?: number
      document_id?: number
    }): Promise<ReviewListResponse> {
      const { data } = await this.client.get<ReviewListResponseDto>('/reviews/pending', { params })
      return mapReviewListResponseDto(data)
    }

    async getMySubmissions(params?: {
      page?: number
      per_page?: number
      status?: string
      document_id?: number
    }): Promise<ReviewListResponse> {
      const { data } = await this.client.get<ReviewListResponseDto>('/reviews/my-submissions', {
        params,
      })
      return mapReviewListResponseDto(data)
    }

    async getReview(reviewId: number): Promise<ReviewRequest> {
      const { data } = await this.client.get<ReviewRequestDto>(`/reviews/${reviewId}`)
      return mapReviewRequestDto(data)
    }

    async getPreApprovePolicy(reviewId: number): Promise<PreApprovePolicy> {
      const { data } = await this.client.get<PreApprovePolicyDto>(
        `/reviews/${reviewId}/approve/preflight`,
      )
      return mapPreApprovePolicyDto(data)
    }

    async approveReview(reviewId: number, data: ReviewAction): Promise<ReviewRequest> {
      const payload = toReviewActionDto(data)
      const { data: response } = await this.client.post<ReviewRequestDto>(
        `/reviews/${reviewId}/approve`,
        payload as ReviewActionDto,
      )
      return mapReviewRequestDto(response)
    }

    async rejectReview(reviewId: number, data: ReviewAction): Promise<ReviewRequest> {
      const payload = toReviewActionDto(data)
      const { data: response } = await this.client.post<ReviewRequestDto>(
        `/reviews/${reviewId}/reject`,
        payload as ReviewActionDto,
      )
      return mapReviewRequestDto(response)
    }

    async cancelReview(reviewId: number): Promise<ReviewRequest> {
      const { data } = await this.client.post<ReviewRequestDto>(`/reviews/${reviewId}/cancel`)
      return mapReviewRequestDto(data)
    }

    async getDocumentReviewHistory(
      documentId: number,
      params?: { page?: number; per_page?: number },
    ): Promise<ReviewListResponse> {
      const { data } = await this.client.get<ReviewListResponseDto>(
        `/reviews/documents/${documentId}/history`,
        { params },
      )
      return mapReviewListResponseDto(data)
    }

    async getAllFeedback(params?: {
      page?: number
      per_page?: number
      status?: FeedbackStatus
      type?: FeedbackType
      company_id?: number
      search?: string
    }): Promise<FeedbackListManagementResponse> {
      const { data } = await this.client.get<FeedbackListManagementResponseDto>('/feedback', {
        params,
      })
      return mapFeedbackListManagementResponseDto(data)
    }

    async getFeedback(feedbackId: number): Promise<FeedbackDetailResponse> {
      const { data } = await this.client.get<FeedbackDetailResponseDto>(`/feedback/${feedbackId}`)
      return mapFeedbackDetailResponseDto(data)
    }

    async respondToFeedback(feedbackId: number, response: string): Promise<FeedbackDetailResponse> {
      const { data } = await this.client.post<FeedbackDetailResponseDto>(
        `/feedback/${feedbackId}/respond`,
        { response },
      )
      return mapFeedbackDetailResponseDto(data)
    }

    async updateFeedbackStatus(
      feedbackId: number,
      status: FeedbackStatus,
    ): Promise<FeedbackDetailResponse> {
      const { data } = await this.client.put<FeedbackDetailResponseDto>(
        `/feedback/${feedbackId}/status`,
        {
          status,
        },
      )
      return mapFeedbackDetailResponseDto(data)
    }

    async getManagementFeedbackStats(): Promise<ManagementFeedbackStatsDto> {
      const { data } = await this.client.get<ManagementFeedbackStatsDto>('/feedback/stats/summary')
      return mapManagementFeedbackStatsDto(data)
    }
  }
