/**
 * Public API Client - No Authentication Required
 * 
 * This module provides API functions for public, unauthenticated access
 * to published documents with PUBLIC visibility.
 */

const API_BASE = '/api/v1/public'

// Types matching backend schemas
export interface PublicDocumentSummary {
  id: number
  document_number: string
  title: string
  description?: string
  category?: string
  topic?: string
  platform?: string
  tags?: string
  created_at: string
  updated_at?: string
}

export interface PublicAttachmentInfo {
  id: number
  filename: string
  file_size: number
  content_type: string
  created_at: string
}

export interface PublicDocumentDetail extends PublicDocumentSummary {
  content?: string
  version_number?: number
  published_at?: string
  has_attachments: boolean
  attachment_count: number
  attachments?: PublicAttachmentInfo[]
}

export interface PublicCategoryCount {
  category: string
  count: number
}

export interface PublicCategoriesResponse {
  items: PublicCategoryCount[]
  total: number
}

export interface PublicDocumentListResponse {
  items: PublicDocumentSummary[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PublicSearchResult {
  id: number
  document_number: string
  title: string
  description?: string
  category?: string
  topic?: string
  platform?: string
  snippet?: string
  score: number
}

export interface PublicSearchResponse {
  query: string
  items: PublicSearchResult[]
  total: number
  page: number
  page_size: number
}

export interface PublicStats {
  total_documents: number
  total_categories: number
}

export interface PublicTopic {
  name: string
  slug: string
  description?: string
  image_url?: string
  document_count: number
}

export interface PublicTopicsResponse {
  items: PublicTopic[]
  total: number
}

// API Functions
export const publicApi = {
  /**
   * Get list of public documents
   */
  async getDocuments(params: {
    page?: number
    page_size?: number
    category?: string
    topic?: string
    platform?: string
    search?: string
    sort_by?: string
    sort_order?: string
  } = {}): Promise<PublicDocumentListResponse> {
    const searchParams = new URLSearchParams()
    if (params.page) searchParams.set('page', params.page.toString())
    if (params.page_size) searchParams.set('page_size', params.page_size.toString())
    if (params.category) searchParams.set('category', params.category)
    if (params.topic) searchParams.set('topic', params.topic)
    if (params.platform) searchParams.set('platform', params.platform)
    if (params.search) searchParams.set('search', params.search)
    if (params.sort_by) searchParams.set('sort_by', params.sort_by)
    if (params.sort_order) searchParams.set('sort_order', params.sort_order)

    const response = await fetch(`${API_BASE}/documents?${searchParams}`)
    if (!response.ok) {
      throw new Error('Failed to fetch public documents')
    }
    return response.json()
  },

  /**
   * Get a single public document by ID
   */
  async getDocument(id: number): Promise<PublicDocumentDetail> {
    const response = await fetch(`${API_BASE}/documents/${id}`)
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Document not found or not publicly accessible')
      }
      throw new Error('Failed to fetch document')
    }
    return response.json()
  },

  /**
   * Get list of categories with document counts
   */
  async getCategories(): Promise<PublicCategoriesResponse> {
    const response = await fetch(`${API_BASE}/categories`)
    if (!response.ok) {
      throw new Error('Failed to fetch categories')
    }
    return response.json()
  },

  /**
   * Search public documents
   */
  async search(params: {
    q: string
    page?: number
    page_size?: number
    category?: string
    topic?: string
    platform?: string
  }): Promise<PublicSearchResponse> {
    const searchParams = new URLSearchParams()
    searchParams.set('q', params.q)
    if (params.page) searchParams.set('page', params.page.toString())
    if (params.page_size) searchParams.set('page_size', params.page_size.toString())
    if (params.category) searchParams.set('category', params.category)
    if (params.topic) searchParams.set('topic', params.topic)
    if (params.platform) searchParams.set('platform', params.platform)

    const response = await fetch(`${API_BASE}/search?${searchParams}`)
    if (!response.ok) {
      throw new Error('Failed to search documents')
    }
    return response.json()
  },

  /**
   * Get public statistics
   */
  async getStats(): Promise<PublicStats> {
    const response = await fetch(`${API_BASE}/stats`)
    if (!response.ok) {
      throw new Error('Failed to fetch stats')
    }
    return response.json()
  },

  /**
   * Get list of public topics
   */
  async getTopics(): Promise<PublicTopicsResponse> {
    const response = await fetch(`${API_BASE}/topics`)
    if (!response.ok) {
      throw new Error('Failed to fetch topics')
    }
    return response.json()
  },

  /**
   * Get a single topic by slug
   */
  async getTopic(slug: string): Promise<PublicTopic> {
    const response = await fetch(`${API_BASE}/topics/${slug}`)
    if (!response.ok) {
      throw new Error('Failed to fetch topic')
    }
    return response.json()
  },

  /**
   * Get attachment info for a public document
   */
  async getAttachment(documentId: number, attachmentId: number): Promise<PublicAttachmentInfo> {
    const response = await fetch(`${API_BASE}/documents/${documentId}/attachments/${attachmentId}`)
    if (!response.ok) {
      throw new Error('Failed to fetch attachment info')
    }
    return response.json()
  },
}

export default publicApi
