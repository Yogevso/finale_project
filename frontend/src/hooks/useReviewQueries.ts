import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { queryKeys } from '@/lib/queryKeys'

export function usePendingReviewsQuery(documentId?: number, enabled: boolean = true) {
  const params = {
    per_page: 50,
    document_id: documentId,
  }

  return useQuery({
    queryKey: queryKeys.reviews.pending(params),
    queryFn: () => api.getPendingReviews(params),
    enabled,
  })
}

export function useMySubmissionsQuery(
  statusFilter: string,
  documentId?: number,
  enabled: boolean = true,
) {
  const params = {
    per_page: 50,
    status: statusFilter || undefined,
    document_id: documentId,
  }

  return useQuery({
    queryKey: queryKeys.reviews.mySubmissions(params),
    queryFn: () => api.getMySubmissions(params),
    enabled,
  })
}
