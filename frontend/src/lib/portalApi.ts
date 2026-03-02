/**
 * Portal API - Customer authenticated API calls
 */
import axios from 'axios'

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
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
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
  pages: number
}

export interface FeedbackItem {
  id: number
  document_id: number
  document_title: string
  feedback_type: 'question' | 'suggestion' | 'issue' | 'other'
  content: string
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

export interface CategoryCount {
  category: string
  count: number
}

// ============ API Functions ============

export const portalApi = {
  // Documents
  async getDocuments(params: {
    page?: number
    per_page?: number
    category?: string
    search?: string
  } = {}): Promise<PortalDocumentListResponse> {
    const searchParams = new URLSearchParams()
    if (params.page) searchParams.set('page', String(params.page))
    if (params.per_page) searchParams.set('per_page', String(params.per_page))
    if (params.category) searchParams.set('category', params.category)
    if (params.search) searchParams.set('search', params.search)
    
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

  async getDashboardStats(): Promise<DashboardStats> {
    const response = await portalClient.get('/portal/dashboard/stats')
    return response.data
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
