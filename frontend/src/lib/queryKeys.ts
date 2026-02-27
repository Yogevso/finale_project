type QueryEntityId = number | string

const normalizeId = (id: QueryEntityId) => String(id)

export const queryKeys = {
  documents: {
    all: ['documents'] as const,
    list: (params?: {
      page?: number
      page_size?: number
      search?: string
      status?: string
      visibility?: string
    }) => ['documents', 'list', params ?? {}] as const,
    detail: (documentId: QueryEntityId) => ['documents', 'detail', normalizeId(documentId)] as const,
    assignedCompanies: (documentId: QueryEntityId) =>
      ['documents', 'detail', normalizeId(documentId), 'assigned-companies'] as const,
    versions: (documentId: QueryEntityId) =>
      ['documents', 'detail', normalizeId(documentId), 'versions'] as const,
  },

  attachments: {
    all: ['attachments'] as const,
    byDocument: (documentId: QueryEntityId) =>
      ['attachments', 'document', normalizeId(documentId)] as const,
  },

  comments: {
    all: ['comments'] as const,
    byDocument: (documentId: QueryEntityId) => ['comments', 'document', normalizeId(documentId)] as const,
  },

  reviews: {
    all: ['reviews'] as const,
    pending: (params?: { page?: number; per_page?: number }) =>
      ['reviews', 'pending', params ?? {}] as const,
    mySubmissions: (params?: { page?: number; per_page?: number; status?: string }) =>
      ['reviews', 'my-submissions', params ?? {}] as const,
    byDocument: (documentId: QueryEntityId, params?: { page?: number; per_page?: number }) =>
      ['reviews', 'document', normalizeId(documentId), params ?? {}] as const,
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
