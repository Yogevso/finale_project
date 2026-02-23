import type { MessageResponse } from '@/types'
import type { ApiHttpClient, Constructor } from './httpClient'

export const SearchEngagementApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async search(query: string, options?: { category?: string; page?: number; pageSize?: number }) {
      const params = { q: query, ...options }
      const { data } = await this.client.get('/search', { params })
      return data
    }

    async getAutocomplete(query: string) {
      const { data } = await this.client.get('/search/autocomplete', { params: { q: query } })
      return data
    }

    async getSearchFacets() {
      const { data } = await this.client.get('/search/facets')
      return data
    }

    async getSavedSearches() {
      const { data } = await this.client.get('/search/saved')
      return data
    }

    async createSavedSearch(search: { name: string; query?: string; category?: string }) {
      const { data } = await this.client.post('/search/saved', search)
      return data
    }

    async deleteSavedSearch(searchId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>(`/search/saved/${searchId}`)
      return data
    }

    async getBookmarks() {
      const { data } = await this.client.get('/engagement/bookmarks')
      return data
    }

    async addBookmark(documentId: number) {
      const { data } = await this.client.post(`/engagement/bookmarks/${documentId}`)
      return data
    }

    async removeBookmark(documentId: number): Promise<MessageResponse> {
      const { data } = await this.client.delete<MessageResponse>(`/engagement/bookmarks/${documentId}`)
      return data
    }

    async checkBookmarkStatus(documentId: number) {
      const { data } = await this.client.get(`/engagement/bookmarks/${documentId}/status`)
      return data
    }

    async submitFeedback(documentId: number, isHelpful: boolean, comment?: string) {
      const { data } = await this.client.post(`/engagement/feedback/${documentId}`, {
        is_helpful: isHelpful,
        comment,
      })
      return data
    }

    async getFeedbackStats(documentId: number) {
      const { data } = await this.client.get(`/engagement/feedback/${documentId}/stats`)
      return data
    }

    async getMyFeedback(documentId: number) {
      const { data } = await this.client.get(`/engagement/feedback/${documentId}/my`)
      return data
    }

    async getReadingProgress() {
      const { data } = await this.client.get('/engagement/progress')
      return data
    }

    async updateReadingProgress(documentId: number, progressPercent: number) {
      const { data } = await this.client.put(`/engagement/progress/${documentId}`, {
        progress_percent: progressPercent,
      })
      return data
    }

    async getDocumentProgress(documentId: number) {
      const { data } = await this.client.get(`/engagement/progress/${documentId}`)
      return data
    }

    async getEngagementStats() {
      const { data } = await this.client.get('/engagement/stats')
      return data
    }
  }

