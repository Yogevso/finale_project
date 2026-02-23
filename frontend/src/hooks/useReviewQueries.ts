import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { queryKeys } from '@/lib/queryKeys'

export function usePendingReviewsQuery(enabled: boolean = true) {
  const params = { per_page: 50 }

  return useQuery({
    queryKey: queryKeys.reviews.pending(params),
    queryFn: () => api.getPendingReviews(params),
    enabled,
  })
}

export function useMySubmissionsQuery(statusFilter: string, enabled: boolean = true) {
  const params = { per_page: 50, status: statusFilter || undefined }

  return useQuery({
    queryKey: queryKeys.reviews.mySubmissions(params),
    queryFn: () => api.getMySubmissions(params),
    enabled,
  })
}
