/**
 * Portal API - Customer authenticated API calls
 */
import axios, { AxiosHeaders } from 'axios'
import { api } from '@/lib/api'
import { withTraceHeader } from '@/lib/requestTrace'
import type { AttachmentOutlineItem } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Create axios instance for portal API
const portalClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth header to requests
portalClient.interceptors.request.use((config) => {
  const headers = AxiosHeaders.from(config.headers ?? {})
  const tracedHeaders = withTraceHeader(headers.toJSON() as Record<string, string>)
  Object.entries(tracedHeaders).forEach(([name, value]) => {
    headers.set(name, value)
  })
  config.headers = headers
  // AD-004: get token from in-memory API client, not localStorage
  const token = api.getToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

// ============ Types ============

export interface PortalDocument {
  id: number
  document_number?: string
  title: string
  description?: string
  category?: string
  topic?: string
  platform?: string
  release_branch?: string
  tags?: string
  thumbnail_url?: string
  visibility: string
  version: number
  created_at?: string
  updated_at: string
  published_at?: string
  has_attachments: boolean
}

export interface PortalDocumentDetail {
  id: number
  document_number?: string
  title: string
  description?: string
  content: string
  category?: string
  topic?: string
  platform?: string
  release_branch?: string
  tags: string[]
  thumbnail_url?: string
  visibility: string
  version: number
  created_at: string
  updated_at: string
  published_at?: string
  toc_items?: AttachmentOutlineItem[]
  attachments: PortalAttachment[]
}

export interface PortalAttachment {
  id: number
  filename: string
  file_size: number
  mime_type?: string
  created_at: string
  download_url?: string
}

export interface PortalDocumentListResponse {
  items: PortalDocument[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface FeedbackItem {
  id: number
  document_id: number
  document_title: string
  ticket_id?: number | null
  feedback_type: 'question' | 'suggestion' | 'issue' | 'other'
  content: string
  anchor_text?: string | null
  status: 'pending' | 'responded' | 'closed'
  response?: string
  responded_at?: string
  responded_by_name?: string
  created_at: string
  updated_at: string
}

export interface FeedbackListResponse {
  items: FeedbackItem[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface DashboardStats {
  total_documents: number
  public_documents: number
  company_documents: number
  pending_feedback: number
  responded_feedback: number
}

export interface PortalReadingProgressItem {
  id: number
  document_id: number
  document_title: string
  progress_percent: number
  last_read_at: string
  completed_at: string | null
}

export interface PortalDocumentProgress {
  has_progress: boolean
  progress_percent: number
  is_completed: boolean
  last_read_at?: string | null
}

export interface CategoryCount {
  category: string
  count: number
}

export interface FacetItem {
  name: string
  count: number
}

export interface PortalFacetsResponse {
  categories: FacetItem[]
  topics: FacetItem[]
  platforms: FacetItem[]
}

// ============ API Functions ============

export const portalApi = {
  // Documents
  async getDocuments(params: {
    page?: number
    per_page?: number
    category?: string
    search?: string
    topic?: string
    platform?: string
    date_from?: string
    date_to?: string
  } = {}): Promise<PortalDocumentListResponse> {
    const searchParams = new URLSearchParams()
    if (params.page) searchParams.set('page', String(params.page))
    if (params.per_page) searchParams.set('per_page', String(params.per_page))
    if (params.category) searchParams.set('category', params.category)
    if (params.search) searchParams.set('search', params.search)
    if (params.topic) searchParams.set('topic', params.topic)
    if (params.platform) searchParams.set('platform', params.platform)
    if (params.date_from) searchParams.set('date_from', params.date_from)
    if (params.date_to) searchParams.set('date_to', params.date_to)
    
    const response = await portalClient.get(`/portal/documents?${searchParams.toString()}`)
    return response.data
  },

  async getDocument(id: number): Promise<PortalDocumentDetail> {
    const response = await portalClient.get(`/portal/documents/${id}`)
    return response.data
  },

  async getCategories(): Promise<CategoryCount[]> {
    const response = await portalClient.get('/portal/categories')
    return response.data
  },

  async getFacets(): Promise<PortalFacetsResponse> {
    const response = await portalClient.get('/portal/facets')
    return response.data
  },

  async getRelatedDocuments(documentId: number, limit = 5): Promise<Array<{
    id: number
    title: string
    description: string | null
    category: string | null
    thumbnail_url: string | null
    updated_at: string | null
  }>> {
    const response = await portalClient.get(`/portal/documents/${documentId}/related`, {
      params: { limit },
    })
    return response.data
  },

  async getDashboardStats(): Promise<DashboardStats> {
    const response = await portalClient.get('/portal/dashboard/stats')
    return response.data
  },

  async getRecentlyViewed(limit = 10): Promise<Array<{
    document_id: number
    title: string
    category: string | null
    thumbnail_url: string | null
    progress_percent: number
    last_read_at: string | null
  }>> {
    const response = await portalClient.get('/portal/reading-progress/recent', {
      params: { limit },
    })
    return response.data
  },

  async getContinueReading(limit = 5): Promise<Array<{
    document_id: number
    title: string
    category: string | null
    thumbnail_url: string | null
    progress_percent: number
    last_read_at: string | null
  }>> {
    const response = await portalClient.get('/portal/reading-progress/continue', {
      params: { limit },
    })
    return response.data
  },

  async getReadingProgress(): Promise<PortalReadingProgressItem[]> {
    const response = await portalClient.get('/portal/reading-progress')
    return response.data
  },

  async getDocumentProgress(documentId: number): Promise<PortalDocumentProgress> {
    const response = await portalClient.get(`/portal/reading-progress/${documentId}`)
    return response.data
  },

  async updateReadingProgress(
    documentId: number,
    progressPercent: number,
  ): Promise<PortalReadingProgressItem> {
    const response = await portalClient.put(`/portal/reading-progress/${documentId}`, {
      progress_percent: progressPercent,
    })
    return response.data
  },

  async getNpsStatus(): Promise<{ should_show: boolean }> {
    const response = await portalClient.get('/portal/nps/status')
    return response.data
  },

  async submitNps(score: number, comment?: string): Promise<void> {
    await portalClient.post('/portal/nps', { score, comment })
  },

  async search(params: {
    q: string
    category?: string
    page?: number
    per_page?: number
  }): Promise<{
    query: string
    results: Array<{
      id: number
      title: string
      description?: string
      category?: string
      snippet: string
      updated_at: string
    }>
    total: number
    page: number
    per_page: number
    pages: number
  }> {
    const searchParams = new URLSearchParams()
    searchParams.set('q', params.q)
    if (params.category) searchParams.set('category', params.category)
    if (params.page) searchParams.set('page', String(params.page))
    if (params.per_page) searchParams.set('per_page', String(params.per_page))
    
    const response = await portalClient.get(`/portal/search?${searchParams.toString()}`)
    return response.data
  },

  // Feedback
  async submitFeedback(data: {
    document_id: number
    feedback_type: 'question' | 'suggestion' | 'issue' | 'other'
    content: string
    anchor_text?: string
  }): Promise<FeedbackItem> {
    const response = await portalClient.post('/portal/feedback', data)
    return response.data
  },

  async getFeedbackList(params: {
    page?: number
    per_page?: number
    status?: 'pending' | 'responded' | 'closed'
  } = {}): Promise<FeedbackListResponse> {
    const searchParams = new URLSearchParams()
    if (params.page) searchParams.set('page', String(params.page))
    if (params.per_page) searchParams.set('per_page', String(params.per_page))
    if (params.status) searchParams.set('status', params.status)
    
    const response = await portalClient.get(`/portal/feedback?${searchParams.toString()}`)
    return response.data
  },

  async getFeedback(id: number): Promise<FeedbackItem> {
    const response = await portalClient.get(`/portal/feedback/${id}`)
    return response.data
  },
}
