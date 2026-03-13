import type {
  AnalyticsOverview,
  AnalyticsQueryParams,
  AudienceAlertRule,
  AudienceAlertRuleCreate,
  CompanyAudienceAnalytics,
  ContentAnalytics,
  EngagementAnalytics,
  FeedbackAnalytics,
  RecentActivity,
  TenantAnalytics,
  TopDocuments,
  UserAnalytics,
} from '@/types'
import {
  type AnalyticsOverviewDto,
  type ContentAnalyticsDto,
  type EngagementAnalyticsDto,
  type FeedbackAnalyticsDto,
  type RecentActivityDto,
  type TenantAnalyticsDto,
  type TopDocumentsDto,
  type UserAnalyticsDto,
  mapAnalyticsOverviewDto,
  mapContentAnalyticsDto,
  mapEngagementAnalyticsDto,
  mapFeedbackAnalyticsDto,
  mapRecentActivitiesDto,
  mapTenantAnalyticsDto,
  mapTopDocumentsDto,
  mapUserAnalyticsDto,
} from './dto'
import { API_BASE_URL } from './httpClient'
import type { ApiHttpClient, Constructor } from './httpClient'

export const AnalyticsApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getAnalyticsOverview(params?: AnalyticsQueryParams): Promise<AnalyticsOverview> {
      const { data } = await this.client.get<AnalyticsOverviewDto>('/analytics/overview', { params })
      return mapAnalyticsOverviewDto(data)
    }

    async getRecentActivity(limit: number = 10): Promise<RecentActivity[]> {
      const { data } = await this.client.get<RecentActivityDto[]>('/analytics/recent-activity', {
        params: { limit },
      })
      return mapRecentActivitiesDto(data)
    }

    async getEngagementAnalytics(params?: AnalyticsQueryParams): Promise<EngagementAnalytics> {
      const { data } = await this.client.get<EngagementAnalyticsDto>('/analytics/engagement', { params })
      return mapEngagementAnalyticsDto(data)
    }

    async getTopDocuments(params?: AnalyticsQueryParams & { limit?: number }): Promise<TopDocuments> {
      const { data } = await this.client.get<TopDocumentsDto>('/analytics/engagement/top-documents', {
        params,
      })
      return mapTopDocumentsDto(data)
    }

    async getUserAnalytics(params?: AnalyticsQueryParams): Promise<UserAnalytics> {
      const { data } = await this.client.get<UserAnalyticsDto>('/analytics/users', { params })
      return mapUserAnalyticsDto(data)
    }

    async getContentAnalytics(params?: AnalyticsQueryParams): Promise<ContentAnalytics> {
      const { data } = await this.client.get<ContentAnalyticsDto>('/analytics/content', { params })
      return mapContentAnalyticsDto(data)
    }

    async getFeedbackAnalytics(params?: AnalyticsQueryParams): Promise<FeedbackAnalytics> {
      const { data } = await this.client.get<FeedbackAnalyticsDto>('/analytics/feedback', { params })
      return mapFeedbackAnalyticsDto(data)
    }

    async getTenantAnalytics(params?: AnalyticsQueryParams): Promise<TenantAnalytics> {
      const { data } = await this.client.get<TenantAnalyticsDto>('/analytics/tenants', { params })
      return mapTenantAnalyticsDto(data)
    }

    async getCompanyAudienceAnalytics(companyId: number): Promise<CompanyAudienceAnalytics> {
      const { data } = await this.client.get<CompanyAudienceAnalytics>(`/analytics/company/${companyId}`)
      return data
    }

    async getDocumentAudienceChurn(
      documentId: number,
    ): Promise<{ document_id: number; assignment_churn_90d: number }> {
      const { data } = await this.client.get<{ document_id: number; assignment_churn_90d: number }>(
        `/analytics/documents/${documentId}/audience-churn`,
      )
      return data
    }

    async listAudienceAlertRules(): Promise<AudienceAlertRule[]> {
      const { data } = await this.client.get<AudienceAlertRule[]>('/admin/alerts/audience-rules')
      return data
    }

    async createAudienceAlertRule(payload: AudienceAlertRuleCreate): Promise<AudienceAlertRule> {
      const { data } = await this.client.post<AudienceAlertRule>('/admin/alerts/audience-rules', payload)
      return data
    }

    async deleteAudienceAlertRule(ruleId: string): Promise<{ message: string; rule_id: string }> {
      const { data } = await this.client.delete<{ message: string; rule_id: string }>(
        `/admin/alerts/audience-rules/${ruleId}`,
      )
      return data
    }

    getAnalyticsExportUrl(
      report: 'overview' | 'engagement' | 'users' | 'content' | 'feedback',
      format: 'csv',
      params?: AnalyticsQueryParams,
    ): string {
      const searchParams = new URLSearchParams({ report })
      if (params?.date_from) searchParams.set('date_from', params.date_from)
      if (params?.date_to) searchParams.set('date_to', params.date_to)
      return `${API_BASE_URL}/analytics/export/${format}?${searchParams.toString()}`
    }

    async downloadAnalyticsExport(
      report: 'overview' | 'engagement' | 'users' | 'content' | 'feedback',
      format: 'csv',
      params?: AnalyticsQueryParams,
    ): Promise<Blob> {
      const response = await this.client.get(`/analytics/export/${format}`, {
        params: { report, ...params },
        responseType: 'blob',
      })
      return response.data
    }
  }

