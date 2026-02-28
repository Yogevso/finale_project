import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { queryKeys } from '@/lib/queryKeys'
import type { Attachment, DocumentDetailPageBundle } from '@/types'

type DocumentIdInput = number | string | null | undefined

const parseDocumentId = (documentId: DocumentIdInput): number | null => {
  if (documentId === null || documentId === undefined) {
    return null
  }
  const parsed = Number(documentId)
  return Number.isFinite(parsed) ? parsed : null
}

export function useDocumentDetailQuery(documentId: DocumentIdInput, enabled: boolean = true) {
  const parsedDocumentId = parseDocumentId(documentId)

  return useQuery({
    queryKey: queryKeys.documents.detail(documentId ?? 'unknown'),
    queryFn: () => api.getDocument(parsedDocumentId as number),
    enabled: enabled && parsedDocumentId !== null,
  })
}

export function useDocumentDetailPageBundleQuery(
  documentId: DocumentIdInput,
  options?: {
    enabled?: boolean
    refetchInterval?: (query: {
      state: { data: DocumentDetailPageBundle | undefined }
    }) => number | false
  },
) {
  const parsedDocumentId = parseDocumentId(documentId)

  return useQuery({
    queryKey: queryKeys.bff.documentDetailBundle(documentId ?? 'unknown'),
    queryFn: () => api.getDocumentDetailPageBundle(parsedDocumentId as number),
    enabled: (options?.enabled ?? true) && parsedDocumentId !== null,
    refetchInterval: options?.refetchInterval,
  })
}

export function useDocumentAttachmentsQuery(
  documentId: DocumentIdInput,
  options?: {
    enabled?: boolean
    refetchInterval?: (query: { state: { data: Attachment[] | undefined } }) => number | false
  },
) {
  const parsedDocumentId = parseDocumentId(documentId)

  return useQuery({
    queryKey: queryKeys.attachments.byDocument(documentId ?? 'unknown'),
    queryFn: () => api.getAttachments(parsedDocumentId as number),
    enabled: (options?.enabled ?? true) && parsedDocumentId !== null,
    refetchInterval: options?.refetchInterval,
  })
}

export function useDocumentCommentsQuery(documentId: DocumentIdInput, enabled: boolean = true) {
  const parsedDocumentId = parseDocumentId(documentId)

  return useQuery({
    queryKey: queryKeys.comments.byDocument(documentId ?? 'unknown'),
    queryFn: () => api.getComments(parsedDocumentId as number),
    enabled: enabled && parsedDocumentId !== null,
  })
}

export function useDocumentVersionsQuery(documentId: DocumentIdInput, enabled: boolean = true) {
  const parsedDocumentId = parseDocumentId(documentId)

  return useQuery({
    queryKey: queryKeys.documents.versions(documentId ?? 'unknown'),
    queryFn: () => api.getVersions(parsedDocumentId as number),
    enabled: enabled && parsedDocumentId !== null,
  })
}

export function useDocumentAssignedCompaniesQuery(documentId: DocumentIdInput, enabled: boolean = true) {
  const parsedDocumentId = parseDocumentId(documentId)

  return useQuery({
    queryKey: queryKeys.documents.assignedCompanies(documentId ?? 'unknown'),
    queryFn: () => api.getAssignedCompanies(parsedDocumentId as number),
    enabled: enabled && parsedDocumentId !== null,
  })
}

export function useDocumentReviewHistoryQuery(documentId: DocumentIdInput, enabled: boolean = true) {
  const parsedDocumentId = parseDocumentId(documentId)

  return useQuery({
    queryKey: queryKeys.reviews.byDocument(documentId ?? 'unknown'),
    queryFn: () => api.getDocumentReviewHistory(parsedDocumentId as number),
    enabled: enabled && parsedDocumentId !== null,
  })
}
