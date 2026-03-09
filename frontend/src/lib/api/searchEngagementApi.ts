import type { MessageResponse, SavedSearch } from '@/types'
import {
  type BookmarkDto,
  type BookmarkStatusDto,
  type DocumentProgressDto,
  type EngagementStatsDto,
  type FeedbackStatsDto,
  type FeedbackSubmissionDto,
  type MessageResponseDto,
  type MyFeedbackDto,
  type ReadingProgressDto,
  type SavedSearchCreateDto,
  type SavedSearchDto,
  type SearchAutocompleteResponseDto,
  type SearchFacetsResponseDto,
  type SearchResponseDto,
  mapBookmarkStatusDto,
  mapBookmarksDto,
  mapDocumentProgressDto,
  mapEngagementStatsDto,
  mapFeedbackStatsDto,
  mapFeedbackSubmissionDto,
  mapMessageResponseDto,
  mapMyFeedbackDto,
  mapReadingProgressListDto,
  mapReadingProgressDto,
  mapSavedSearchDto,
  mapSavedSearchesDto,
  mapSearchAutocompleteResponseDto,
  mapSearchFacetsResponseDto,
  mapSearchResponseDto,
  toSavedSearchCreateDto,
} from './dto'
import type { ApiHttpClient, Constructor } from './httpClient'

export const SearchEngagementApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async search(
      query: string,
      options?: { category?: string; page?: number; pageSize?: number },
    ): Promise<SearchResponseDto> {
      const params = { q: query, ...options }
      const { data } = await this.client.get<SearchResponseDto>('/search', { params })
      return mapSearchResponseDto(data)
    }

    async getAutocomplete(query: string): Promise<SearchAutocompleteResponseDto> {
      const { data } = await this.client.get<SearchAutocompleteResponseDto>('/search/autocomplete', {
        params: { q: query },
      })
      return mapSearchAutocompleteResponseDto(data)
    }

    async getSearchFacets(): Promise<SearchFacetsResponseDto> {
      const { data } = await this.client.get<SearchFacetsResponseDto>('/search/facets')
      return mapSearchFacetsResponseDto(data)
    }

    async getSavedSearches(): Promise<SavedSearch[]> {
      const { data } = await this.client.get<SavedSearchDto[]>('/search/saved')
      return mapSavedSearchesDto(data)
    }

    async createSavedSearch(search: {
      name: string
      query?: string
      category?: string
      date_from?: string | null
      date_to?: string | null
    }): Promise<SavedSearch> {
      const payload = toSavedSearchCreateDto(search as SavedSearchCreateDto)
      const { data } = await this.client.post<SavedSearchDto>(
        '/search/saved',
        payload as SavedSearchCreateDto,
      )
      return mapSavedSearchDto(data)
    }

    async deleteSavedSearch(searchId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponseDto>(`/search/saved/${searchId}`)
      return mapMessageResponseDto(data)
    }

    async getBookmarks(): Promise<BookmarkDto[]> {
      const { data } = await this.client.get<BookmarkDto[]>('/engagement/bookmarks')
      return mapBookmarksDto(data)
    }

    async addBookmark(documentId: number): Promise<MessageResponse> {
      const { data } = await this.client.post<BookmarkDto | MessageResponseDto>(
        `/engagement/bookmarks/${documentId}`,
      )
      if (typeof (data as MessageResponseDto).message === 'string') {
        return mapMessageResponseDto(data as MessageResponseDto)
      }
      return { message: 'Bookmark added' }
    }

    async removeBookmark(documentId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponseDto>(
        `/engagement/bookmarks/${documentId}`,
      )
      return mapMessageResponseDto(data)
    }

    async checkBookmarkStatus(documentId: number): Promise<BookmarkStatusDto> {
      const { data } = await this.client.get<BookmarkStatusDto>(
        `/engagement/bookmarks/${documentId}/status`,
      )
      return mapBookmarkStatusDto(data)
    }

    async submitFeedback(
      documentId: number,
      isHelpful: boolean,
      comment?: string,
    ): Promise<FeedbackSubmissionDto> {
      const { data } = await this.client.post<FeedbackSubmissionDto>(
        `/engagement/feedback/${documentId}`,
        {
        is_helpful: isHelpful,
        comment,
        },
      )
      return mapFeedbackSubmissionDto(data)
    }

    async getFeedbackStats(documentId: number): Promise<FeedbackStatsDto> {
      const { data } = await this.client.get<FeedbackStatsDto>(
        `/engagement/feedback/${documentId}/stats`,
      )
      return mapFeedbackStatsDto(data)
    }

    async getMyFeedback(documentId: number): Promise<MyFeedbackDto> {
      const { data } = await this.client.get<MyFeedbackDto>(`/engagement/feedback/${documentId}/my`)
      return mapMyFeedbackDto(data)
    }

    async getReadingProgress(): Promise<ReadingProgressDto[]> {
      const { data } = await this.client.get<ReadingProgressDto[]>('/engagement/progress')
      return mapReadingProgressListDto(data)
    }

    async updateReadingProgress(
      documentId: number,
      progressPercent: number,
    ): Promise<ReadingProgressDto> {
      const { data } = await this.client.put<ReadingProgressDto>(`/engagement/progress/${documentId}`, {
        progress_percent: progressPercent,
      })
      return mapReadingProgressDto(data)
    }

    async getDocumentProgress(documentId: number): Promise<DocumentProgressDto> {
      const { data } = await this.client.get<DocumentProgressDto>(`/engagement/progress/${documentId}`)
      return mapDocumentProgressDto(data)
    }

    async getEngagementStats(): Promise<EngagementStatsDto> {
      const { data } = await this.client.get<EngagementStatsDto>('/engagement/stats')
      return mapEngagementStatsDto(data)
    }
  }

