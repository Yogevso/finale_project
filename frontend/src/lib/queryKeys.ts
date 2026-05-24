type QueryEntityId = number | string

const normalizeId = (id: QueryEntityId) => String(id)

export const queryKeys = {
  companies: {
    all: ['companies'] as const,
    selector: (params: {
      page: number
      per_page: number
      search?: string
      company_type?: string
      is_active?: boolean
    }) => ['companies', 'selector', params] as const,
  },

  documents: {
    all: ['documents'] as const,
    list: (params?: {
      page?: number
      page_size?: number
      search?: string
      status?: string
      visibility?: string
      category?: string
      company_id?: number
      date_from?: string
      date_to?: string
    }) => ['documents', 'list', params ?? {}] as const,
    deletedList: (params?: {
      page?: number
      page_size?: number
      search?: string
      status?: string
      visibility?: string
      category?: string
      company_id?: number
      date_from?: string
      date_to?: string
    }) => ['documents', 'deleted-list', params ?? {}] as const,
    detail: (documentId: QueryEntityId) => ['documents', 'detail', normalizeId(documentId)] as const,
    tags: (query?: string, limit?: number) => ['documents', 'tags', query ?? '', limit ?? 20] as const,
    duplicateCheck: (title: string) => ['documents', 'duplicate-check', title] as const,
    assignedCompanies: (documentId: QueryEntityId) =>
      ['documents', 'detail', normalizeId(documentId), 'assigned-companies'] as const,
    versions: (documentId: QueryEntityId) =>
      ['documents', 'detail', normalizeId(documentId), 'versions'] as const,
    watchStatus: (documentId: QueryEntityId) =>
      ['documents', 'detail', normalizeId(documentId), 'watch-status'] as const,
  },

  attachments: {
    all: ['attachments'] as const,
    byDocument: (documentId: QueryEntityId) =>
      ['attachments', 'document', normalizeId(documentId)] as const,
  },

  comments: {
    all: ['comments'] as const,
    byDocument: (documentId: QueryEntityId, reviewId?: number | null) =>
      ['comments', 'document', normalizeId(documentId), { review_id: reviewId ?? null }] as const,
  },

  reviews: {
    all: ['reviews'] as const,
    pending: (params?: { page?: number; per_page?: number; document_id?: number }) =>
      ['reviews', 'pending', params ?? {}] as const,
    mySubmissions: (params?: {
      page?: number
      per_page?: number
      status?: string
      document_id?: number
    }) =>
      ['reviews', 'my-submissions', params ?? {}] as const,
    byDocument: (documentId: QueryEntityId, params?: { page?: number; per_page?: number }) =>
      ['reviews', 'document', normalizeId(documentId), params ?? {}] as const,
  },

  bff: {
    documentDetailBundle: (documentId: QueryEntityId) =>
      ['bff', 'documents', normalizeId(documentId), 'detail-page'] as const,
  },

  collaboration: {
    all: ['collaboration'] as const,
    status: (documentId: QueryEntityId) =>
      ['collaboration', 'status', normalizeId(documentId)] as const,
    activity: (documentId: QueryEntityId, params?: { limit?: number; offset?: number }) =>
      ['collaboration', 'activity', normalizeId(documentId), params ?? {}] as const,
    sessions: (documentId: QueryEntityId) =>
      ['collaboration', 'sessions', normalizeId(documentId)] as const,
    snapshots: (
      documentId: QueryEntityId,
      params?: { limit?: number; offset?: number; include_expired?: boolean },
    ) => ['collaboration', 'snapshots', normalizeId(documentId), params ?? {}] as const,
  },
}
