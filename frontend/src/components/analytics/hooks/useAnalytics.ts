import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AnalyticsQueryParams } from '@/types'

export function useAnalyticsOverview(params?: AnalyticsQueryParams) {
  return useQuery({
    queryKey: ['analytics', 'overview', params],
    queryFn: () => api.getAnalyticsOverview(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useRecentActivity(limit = 10) {
  return useQuery({
    queryKey: ['analytics', 'recent-activity', limit],
    queryFn: () => api.getRecentActivity(limit),
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export function useEngagementAnalytics(params?: AnalyticsQueryParams) {
  return useQuery({
    queryKey: ['analytics', 'engagement', params],
    queryFn: () => api.getEngagementAnalytics(params),
    staleTime: 5 * 60 * 1000,
  })
}

export function useTopDocuments(limit = 10, params?: AnalyticsQueryParams) {
  return useQuery({
    queryKey: ['analytics', 'top-documents', limit, params],
    queryFn: () => api.getTopDocuments({ ...params, limit }),
    staleTime: 5 * 60 * 1000,
  })
}

export function useUserAnalytics(params?: AnalyticsQueryParams) {
  return useQuery({
    queryKey: ['analytics', 'users', params],
    queryFn: () => api.getUserAnalytics(params),
    staleTime: 5 * 60 * 1000,
  })
}

export function useContentAnalytics(params?: AnalyticsQueryParams) {
  return useQuery({
    queryKey: ['analytics', 'content', params],
    queryFn: () => api.getContentAnalytics(params),
    staleTime: 5 * 60 * 1000,
  })
}

export function useFeedbackAnalytics(params?: AnalyticsQueryParams) {
  return useQuery({
    queryKey: ['analytics', 'feedback', params],
    queryFn: () => api.getFeedbackAnalytics(params),
    staleTime: 5 * 60 * 1000,
  })
}

export function useTenantAnalytics(params?: AnalyticsQueryParams) {
  return useQuery({
    queryKey: ['analytics', 'tenant', params],
    queryFn: () => api.getTenantAnalytics(params),
    staleTime: 5 * 60 * 1000,
  })
}
