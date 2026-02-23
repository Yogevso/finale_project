import type {
  AnalyticsOverview,
  AnalyticsQueryParams,
  ContentAnalytics,
  EngagementAnalytics,
  FeedbackAnalytics,
  RecentActivity,
  TenantAnalytics,
  TopDocuments,
  UserAnalytics,
} from '@/types'
import { API_BASE_URL } from './httpClient'
import type { ApiHttpClient, Constructor } from './httpClient'

export const AnalyticsApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getAnalyticsOverview(params?: AnalyticsQueryParams): Promise<AnalyticsOverview> {
      const { data } = await this.client.get<AnalyticsOverview>('/analytics/overview', { params })
      return data
    }

    async getRecentActivity(limit: number = 10): Promise<RecentActivity[]> {
      const { data } = await this.client.get<RecentActivity[]>('/analytics/recent-activity', {
        params: { limit },
      })
      return data
    }

    async getEngagementAnalytics(params?: AnalyticsQueryParams): Promise<EngagementAnalytics> {
      const { data } = await this.client.get<EngagementAnalytics>('/analytics/engagement', { params })
      return data
    }

    async getTopDocuments(params?: AnalyticsQueryParams & { limit?: number }): Promise<TopDocuments> {
      const { data } = await this.client.get<TopDocuments>('/analytics/engagement/top-documents', { params })
      return data
    }

    async getUserAnalytics(params?: AnalyticsQueryParams): Promise<UserAnalytics> {
      const { data } = await this.client.get<UserAnalytics>('/analytics/users', { params })
      return data
    }

    async getContentAnalytics(params?: AnalyticsQueryParams): Promise<ContentAnalytics> {
      const { data } = await this.client.get<ContentAnalytics>('/analytics/content', { params })
      return data
    }

    async getFeedbackAnalytics(params?: AnalyticsQueryParams): Promise<FeedbackAnalytics> {
      const { data } = await this.client.get<FeedbackAnalytics>('/analytics/feedback', { params })
      return data
    }

    async getTenantAnalytics(params?: AnalyticsQueryParams): Promise<TenantAnalytics> {
      const { data } = await this.client.get<TenantAnalytics>('/analytics/tenants', { params })
      return data
    }

    getAnalyticsExportUrl(
      report: 'overview' | 'engagement' | 'users' | 'content' | 'feedback',
      format: 'csv' | 'pdf',
      params?: AnalyticsQueryParams,
    ): string {
      const searchParams = new URLSearchParams({ report })
      if (params?.date_from) searchParams.set('date_from', params.date_from)
      if (params?.date_to) searchParams.set('date_to', params.date_to)
      return `${API_BASE_URL}/analytics/export/${format}?${searchParams.toString()}`
    }

    async downloadAnalyticsExport(
      report: 'overview' | 'engagement' | 'users' | 'content' | 'feedback',
      format: 'csv' | 'pdf',
      params?: AnalyticsQueryParams,
    ): Promise<Blob> {
      const response = await this.client.get(`/analytics/export/${format}`, {
        params: { report, ...params },
        responseType: 'blob',
      })
      return response.data
    }
  }

