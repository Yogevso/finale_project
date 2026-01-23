import axios, { AxiosError, AxiosInstance } from 'axios'
import type {
  LoginRequest,
  TokenResponse,
  User,
  UserCreate,
  UserRole,
  Document,
  DocumentCreate,
  DocumentUpdate,
  DocumentListResponse,
  DocumentQueryParams,
  MessageResponse,
  PasswordChange,
  Version,
  VersionCreate,
  VersionUpdate,
  VersionListResponse,
  Attachment,
  AttachmentUploadResponse,
  Comment,
  CommentCreate,
  CommentUpdate,
  NotificationListResponse,
  NotificationCountResponse,
  Company,
  CompanyListResponse,
  CompanyCreate,
  CompanyUpdate,
  CompanyUserAdd,
  CompanyUser,
  CompanyDocumentsResponse,
  ReviewRequest,
  ReviewSubmit,
  ReviewAction,
  ReviewListResponse,
  FeedbackDetailResponse,
  FeedbackListManagementResponse,
  FeedbackStatus,
  FeedbackType,
  Invitation,
  InvitationListResponse,
  InvitationCreate,
  InvitationStatus,
  InvitationValidateResponse,
  AcceptInvitationRequest,
  AnalyticsOverview,
  EngagementAnalytics,
  TopDocuments,
  UserAnalytics,
  ContentAnalytics,
  FeedbackAnalytics,
  TenantAnalytics,
  RecentActivity,
  AnalyticsQueryParams,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

class ApiClient {
  private client: AxiosInstance
  private token: string | null = null
  private refreshToken: string | null = null
  private isRefreshing = false
  private refreshSubscribers: ((token: string) => void)[] = []

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Load tokens from localStorage
    this.token = localStorage.getItem('token')
    this.refreshToken = localStorage.getItem('refreshToken')

    // Add auth header to requests
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`
      }
      return config
    })

    // Handle 401 errors with token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config
        
        if (error.response?.status === 401 && originalRequest && !originalRequest.url?.includes('/auth/refresh')) {
          // Try to refresh the token
          if (this.refreshToken && !this.isRefreshing) {
            this.isRefreshing = true
            try {
              const newToken = await this.doRefreshToken()
              this.isRefreshing = false
              this.onRefreshed(newToken)
              originalRequest.headers.Authorization = `Bearer ${newToken}`
              return this.client(originalRequest)
            } catch {
              this.isRefreshing = false
              this.clearTokens()
              window.location.href = '/login'
              return Promise.reject(error)
            }
          } else if (this.isRefreshing) {
            // Wait for token refresh
            return new Promise((resolve) => {
              this.subscribeTokenRefresh((token: string) => {
                originalRequest.headers.Authorization = `Bearer ${token}`
                resolve(this.client(originalRequest))
              })
            })
          } else {
            this.clearTokens()
            window.location.href = '/login'
          }
        }
        return Promise.reject(error)
      }
    )
  }

  private subscribeTokenRefresh(cb: (token: string) => void) {
    this.refreshSubscribers.push(cb)
  }

  private onRefreshed(token: string) {
    this.refreshSubscribers.forEach(cb => cb(token))
    this.refreshSubscribers = []
  }

  private async doRefreshToken(): Promise<string> {
    const { data } = await axios.post<TokenResponse>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: this.refreshToken }
    )
    this.setToken(data.access_token)
    return data.access_token
  }

  setToken(token: string, refresh?: string | null) {
    this.token = token
    localStorage.setItem('token', token)
    if (refresh) {
      this.refreshToken = refresh
      localStorage.setItem('refreshToken', refresh)
    }
  }

  clearTokens() {
    this.token = null
    this.refreshToken = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
  }

  hasToken(): boolean {
    return !!this.token
  }

  // ========== Auth ==========
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const { data } = await this.client.post<TokenResponse>('/auth/login', credentials)
    this.setToken(data.access_token, data.refresh_token)
    return data
  }

  async register(userData: UserCreate): Promise<User> {
    const { data } = await this.client.post<User>('/auth/register', userData)
    return data
  }

  async getCurrentUser(): Promise<User> {
    const { data } = await this.client.get<User>('/auth/me')
    return data
  }

  async changePassword(passwords: PasswordChange): Promise<MessageResponse> {
    const { data } = await this.client.post<MessageResponse>('/auth/change-password', passwords)
    return data
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout')
    } catch {
      // Ignore logout errors
    }
    this.clearTokens()
  }

  // ========== Users ==========
  async getUsers(params?: {
    role?: UserRole
    company_id?: number
    is_active?: boolean
    search?: string
  }): Promise<User[]> {
    const { data } = await this.client.get<User[]>('/users', { params })
    return data
  }

  async getUser(id: number): Promise<User> {
    const { data } = await this.client.get<User>(`/users/${id}`)
    return data
  }

  async createUser(userData: {
    email: string
    username: string
    full_name: string
    password: string
    role: UserRole
    tenant_id?: number
  }): Promise<User> {
    const { data } = await this.client.post<User>('/users', userData)
    return data
  }

  async updateUser(id: number, userData: {
    email?: string
    full_name?: string
    role?: UserRole
    is_active?: boolean
    tenant_id?: number | null
  }): Promise<User> {
    const { data } = await this.client.put<User>(`/users/${id}`, userData)
    return data
  }

  async deleteUser(id: number): Promise<void> {
    await this.client.delete(`/users/${id}`)
  }

  // ========== Documents ==========
  async getDocuments(params?: DocumentQueryParams): Promise<DocumentListResponse> {
    const { data } = await this.client.get<DocumentListResponse>('/documents', { params })
    return data
  }

  async getDocument(id: number): Promise<Document> {
    const { data } = await this.client.get<Document>(`/documents/${id}`)
    return data
  }

  async createDocument(document: DocumentCreate): Promise<Document> {
    const { data } = await this.client.post<Document>('/documents', document)
    return data
  }

  async updateDocument(id: number, document: DocumentUpdate): Promise<Document> {
    const { data } = await this.client.put<Document>(`/documents/${id}`, document)
    return data
  }

  async deleteDocument(id: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/documents/${id}`)
    return data
  }

  async uploadDocument(file: File, metadata?: { title?: string; description?: string; category?: string; tags?: string }): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    if (metadata?.title) formData.append('title', metadata.title)
    if (metadata?.description) formData.append('description', metadata.description)
    if (metadata?.category) formData.append('category', metadata.category)
    if (metadata?.tags) formData.append('tags', metadata.tags)
    
    const { data } = await this.client.post<Document>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  }

  // ========== Document Company Assignment ==========
  async getAssignedCompanies(documentId: number): Promise<{ companies: Company[] }> {
    const { data } = await this.client.get<{ companies: Company[] }>(`/documents/${documentId}/assigned-companies`)
    return data
  }

  async assignCompanies(documentId: number, companyIds: number[]): Promise<{ message: string; assigned_count: number }> {
    const { data } = await this.client.post<{ message: string; assigned_count: number }>(`/documents/${documentId}/assign-companies`, { company_ids: companyIds })
    return data
  }

  async removeCompanyAssignment(documentId: number, companyId: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/documents/${documentId}/assign-companies/${companyId}`)
    return data
  }

  // ========== Versions ==========
  async getVersions(documentId: number): Promise<VersionListResponse> {
    const { data } = await this.client.get<VersionListResponse>(`/documents/${documentId}/versions`)
    return data
  }

  async getVersion(documentId: number, versionId: number): Promise<Version> {
    const { data } = await this.client.get<Version>(`/documents/${documentId}/versions/${versionId}`)
    return data
  }

  async createVersion(documentId: number, version: VersionCreate): Promise<Version> {
    const { data } = await this.client.post<Version>(`/documents/${documentId}/versions`, version)
    return data
  }

  async updateVersion(documentId: number, versionId: number, version: VersionUpdate): Promise<Version> {
    const { data } = await this.client.patch<Version>(`/documents/${documentId}/versions/${versionId}`, version)
    return data
  }

  async publishVersion(documentId: number, versionId: number): Promise<Version> {
    const { data } = await this.client.post<Version>(`/documents/${documentId}/versions/${versionId}/publish`)
    return data
  }

  async deleteVersion(documentId: number, versionId: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/documents/${documentId}/versions/${versionId}`)
    return data
  }

  // ========== Attachments ==========
  async getAttachments(documentId: number): Promise<Attachment[]> {
    const { data } = await this.client.get<Attachment[]>(`/documents/${documentId}/attachments`)
    return data
  }

  async uploadAttachment(documentId: number, file: File): Promise<AttachmentUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await this.client.post<AttachmentUploadResponse>(
      `/documents/${documentId}/attachments`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return data
  }

  async deleteAttachment(documentId: number, attachmentId: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/documents/${documentId}/attachments/${attachmentId}`)
    return data
  }

  getAttachmentDownloadUrl(documentId: number, attachmentId: number): string {
    // Include token in URL for authenticated download
    const token = this.token || localStorage.getItem('token')
    return `${API_BASE_URL}/documents/${documentId}/attachments/${attachmentId}/download?token=${token}`
  }

  async getAttachmentBlob(documentId: number, attachmentId: number): Promise<Blob> {
    const response = await this.client.get(
      `/documents/${documentId}/attachments/${attachmentId}/download`,
      { responseType: 'blob' }
    )
    return response.data
  }

  // ========== Comments ==========
  async getComments(documentId: number, parentId?: number): Promise<Comment[]> {
    const params = parentId !== undefined ? { parent_id: parentId } : {}
    const { data } = await this.client.get<Comment[]>(`/documents/${documentId}/comments`, { params })
    return data
  }

  async getComment(documentId: number, commentId: number): Promise<Comment> {
    const { data } = await this.client.get<Comment>(`/documents/${documentId}/comments/${commentId}`)
    return data
  }

  async createComment(documentId: number, comment: CommentCreate): Promise<Comment> {
    const { data } = await this.client.post<Comment>(`/documents/${documentId}/comments`, comment)
    return data
  }

  async updateComment(documentId: number, commentId: number, comment: CommentUpdate): Promise<Comment> {
    const { data } = await this.client.patch<Comment>(`/documents/${documentId}/comments/${commentId}`, comment)
    return data
  }

  async deleteComment(documentId: number, commentId: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/documents/${documentId}/comments/${commentId}`)
    return data
  }

  // ========== Search ==========
  async search(query: string, options?: { category?: string; page?: number; pageSize?: number }) {
    const params = { q: query, ...options }
    const { data } = await this.client.get('/search', { params })
    return data
  }

  async getAutocomplete(query: string) {
    const { data } = await this.client.get('/search/autocomplete', { params: { q: query } })
    return data
  }

  async getSearchFacets() {
    const { data } = await this.client.get('/search/facets')
    return data
  }

  // ========== Saved Searches ==========
  async getSavedSearches() {
    const { data } = await this.client.get('/search/saved')
    return data
  }

  async createSavedSearch(search: { name: string; query?: string; category?: string }) {
    const { data } = await this.client.post('/search/saved', search)
    return data
  }

  async deleteSavedSearch(searchId: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/search/saved/${searchId}`)
    return data
  }

  // ========== Bookmarks ==========
  async getBookmarks() {
    const { data } = await this.client.get('/engagement/bookmarks')
    return data
  }

  async addBookmark(documentId: number) {
    const { data } = await this.client.post(`/engagement/bookmarks/${documentId}`)
    return data
  }

  async removeBookmark(documentId: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/engagement/bookmarks/${documentId}`)
    return data
  }

  async checkBookmarkStatus(documentId: number) {
    const { data } = await this.client.get(`/engagement/bookmarks/${documentId}/status`)
    return data
  }

  // ========== Feedback ==========
  async submitFeedback(documentId: number, isHelpful: boolean, comment?: string) {
    const { data } = await this.client.post(`/engagement/feedback/${documentId}`, {
      is_helpful: isHelpful,
      comment,
    })
    return data
  }

  async getFeedbackStats(documentId: number) {
    const { data } = await this.client.get(`/engagement/feedback/${documentId}/stats`)
    return data
  }

  async getMyFeedback(documentId: number) {
    const { data } = await this.client.get(`/engagement/feedback/${documentId}/my`)
    return data
  }

  // ========== Reading Progress ==========
  async getReadingProgress() {
    const { data } = await this.client.get('/engagement/progress')
    return data
  }

  async updateReadingProgress(documentId: number, progressPercent: number) {
    const { data } = await this.client.put(`/engagement/progress/${documentId}`, {
      progress_percent: progressPercent,
    })
    return data
  }

  async getDocumentProgress(documentId: number) {
    const { data } = await this.client.get(`/engagement/progress/${documentId}`)
    return data
  }

  async getEngagementStats() {
    const { data } = await this.client.get('/engagement/stats')
    return data
  }

  // ========== Notifications ==========
  async getNotifications(unreadOnly: boolean = false, limit: number = 50): Promise<NotificationListResponse> {
    const { data } = await this.client.get<NotificationListResponse>('/notifications', {
      params: { unread_only: unreadOnly, limit }
    })
    return data
  }

  async getNotificationCount(): Promise<NotificationCountResponse> {
    const { data } = await this.client.get<NotificationCountResponse>('/notifications/count')
    return data
  }

  async markNotificationRead(notificationId: number): Promise<MessageResponse> {
    const { data } = await this.client.post<MessageResponse>(`/notifications/${notificationId}/read`)
    return data
  }

  async markAllNotificationsRead(notificationIds?: number[]): Promise<MessageResponse> {
    const { data } = await this.client.post<MessageResponse>('/notifications/read', {
      notification_ids: notificationIds || null
    })
    return data
  }

  async deleteNotification(notificationId: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/notifications/${notificationId}`)
    return data
  }

  async deleteAllNotifications(readOnly: boolean = true): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>('/notifications', {
      params: { read_only: readOnly }
    })
    return data
  }

  // ========== Companies (Admin) ==========
  async getCompanies(params?: {
    page?: number
    per_page?: number
    search?: string
    company_type?: string
    is_active?: boolean
  }): Promise<CompanyListResponse> {
    const { data } = await this.client.get<CompanyListResponse>('/companies', { params })
    return data
  }

  async getCompany(id: number): Promise<Company> {
    const { data } = await this.client.get<Company>(`/companies/${id}`)
    return data
  }

  async createCompany(company: CompanyCreate): Promise<Company> {
    const { data } = await this.client.post<Company>('/companies', company)
    return data
  }

  async updateCompany(id: number, company: CompanyUpdate): Promise<Company> {
    const { data } = await this.client.put<Company>(`/companies/${id}`, company)
    return data
  }

  async deleteCompany(id: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/companies/${id}`)
    return data
  }

  async getCompanyUsers(companyId: number): Promise<CompanyUser[]> {
    const { data } = await this.client.get<CompanyUser[]>(`/companies/${companyId}/users`)
    return data
  }

  async addUserToCompany(companyId: number, userData: CompanyUserAdd): Promise<MessageResponse> {
    const { data } = await this.client.post<MessageResponse>(`/companies/${companyId}/users`, userData)
    return data
  }

  async removeUserFromCompany(companyId: number, userId: number): Promise<MessageResponse> {
    const { data } = await this.client.delete<MessageResponse>(`/companies/${companyId}/users/${userId}`)
    return data
  }

  async getCompanyDocuments(companyId: number, params?: {
    page?: number
    per_page?: number
  }): Promise<CompanyDocumentsResponse> {
    const { data } = await this.client.get<CompanyDocumentsResponse>(`/companies/${companyId}/documents`, { params })
    return data
  }

  // ========== Reviews ==========
  async submitForReview(documentId: number, data: ReviewSubmit): Promise<ReviewRequest> {
    const { data: response } = await this.client.post<ReviewRequest>(`/reviews/documents/${documentId}/submit`, data)
    return response
  }

  async getPendingReviews(params?: { page?: number; per_page?: number }): Promise<ReviewListResponse> {
    const { data } = await this.client.get<ReviewListResponse>('/reviews/pending', { params })
    return data
  }

  async getMySubmissions(params?: { page?: number; per_page?: number; status?: string }): Promise<ReviewListResponse> {
    const { data } = await this.client.get<ReviewListResponse>('/reviews/my-submissions', { params })
    return data
  }

  async getReview(reviewId: number): Promise<ReviewRequest> {
    const { data } = await this.client.get<ReviewRequest>(`/reviews/${reviewId}`)
    return data
  }

  async approveReview(reviewId: number, data: ReviewAction): Promise<ReviewRequest> {
    const { data: response } = await this.client.post<ReviewRequest>(`/reviews/${reviewId}/approve`, data)
    return response
  }

  async rejectReview(reviewId: number, data: { comments: string }): Promise<ReviewRequest> {
    const { data: response } = await this.client.post<ReviewRequest>(`/reviews/${reviewId}/reject`, data)
    return response
  }

  async cancelReview(reviewId: number): Promise<ReviewRequest> {
    const { data } = await this.client.post<ReviewRequest>(`/reviews/${reviewId}/cancel`)
    return data
  }

  async getDocumentReviewHistory(documentId: number, params?: { page?: number; per_page?: number }): Promise<ReviewListResponse> {
    const { data } = await this.client.get<ReviewListResponse>(`/reviews/documents/${documentId}/history`, { params })
    return data
  }

  // ========== Feedback Management ==========
  async getAllFeedback(params?: {
    page?: number
    per_page?: number
    status?: FeedbackStatus
    type?: FeedbackType
    company_id?: number
    search?: string
  }): Promise<FeedbackListManagementResponse> {
    const { data } = await this.client.get<FeedbackListManagementResponse>('/feedback', { params })
    return data
  }

  async getFeedback(feedbackId: number): Promise<FeedbackDetailResponse> {
    const { data } = await this.client.get<FeedbackDetailResponse>(`/feedback/${feedbackId}`)
    return data
  }

  async respondToFeedback(feedbackId: number, response: string): Promise<FeedbackDetailResponse> {
    const { data } = await this.client.post<FeedbackDetailResponse>(`/feedback/${feedbackId}/respond`, { response })
    return data
  }

  async updateFeedbackStatus(feedbackId: number, status: FeedbackStatus): Promise<FeedbackDetailResponse> {
    const { data } = await this.client.put<FeedbackDetailResponse>(`/feedback/${feedbackId}/status`, { status })
    return data
  }

  async getManagementFeedbackStats(): Promise<{
    total: number
    pending: number
    responded: number
    closed: number
    by_type: Record<string, number>
  }> {
    const { data } = await this.client.get('/feedback/stats/summary')
    return data
  }

  // ========== Invitations ==========
  async getInvitations(params?: {
    page?: number
    per_page?: number
    status?: InvitationStatus
  }): Promise<InvitationListResponse> {
    const { data } = await this.client.get<InvitationListResponse>('/invitations', { params })
    return data
  }

  async getInvitation(id: number): Promise<Invitation> {
    const { data } = await this.client.get<Invitation>(`/invitations/${id}`)
    return data
  }

  async createInvitation(invitation: InvitationCreate): Promise<Invitation> {
    const { data } = await this.client.post<Invitation>('/invitations', invitation)
    return data
  }

  async cancelInvitation(id: number): Promise<void> {
    await this.client.delete(`/invitations/${id}`)
  }

  async resendInvitation(id: number): Promise<Invitation> {
    const { data } = await this.client.post<Invitation>(`/invitations/${id}/resend`)
    return data
  }

  async validateInvitation(token: string): Promise<InvitationValidateResponse> {
    const { data } = await this.client.get<InvitationValidateResponse>(`/auth/invitation/${token}`)
    return data
  }

  async acceptInvitation(request: AcceptInvitationRequest): Promise<TokenResponse> {
    const { data } = await this.client.post<TokenResponse>('/auth/invitation/accept', request)
    return data
  }

  // ========== Analytics ==========
  async getAnalyticsOverview(params?: AnalyticsQueryParams): Promise<AnalyticsOverview> {
    const { data } = await this.client.get<AnalyticsOverview>('/analytics/overview', { params })
    return data
  }

  async getRecentActivity(limit: number = 10): Promise<RecentActivity[]> {
    const { data } = await this.client.get<RecentActivity[]>('/analytics/recent-activity', { 
      params: { limit } 
    })
    return data
  }

  async getEngagementAnalytics(params?: AnalyticsQueryParams): Promise<EngagementAnalytics> {
    const { data } = await this.client.get<EngagementAnalytics>('/analytics/engagement', { params })
    return data
  }

  async getTopDocuments(params?: AnalyticsQueryParams & { limit?: number }): Promise<TopDocuments> {
    const { data } = await this.client.get<TopDocuments>('/analytics/engagement/top-documents', { params })
    return data
  }

  async getUserAnalytics(params?: AnalyticsQueryParams): Promise<UserAnalytics> {
    const { data } = await this.client.get<UserAnalytics>('/analytics/users', { params })
    return data
  }

  async getContentAnalytics(params?: AnalyticsQueryParams): Promise<ContentAnalytics> {
    const { data } = await this.client.get<ContentAnalytics>('/analytics/content', { params })
    return data
  }

  async getFeedbackAnalytics(params?: AnalyticsQueryParams): Promise<FeedbackAnalytics> {
    const { data } = await this.client.get<FeedbackAnalytics>('/analytics/feedback', { params })
    return data
  }

  async getTenantAnalytics(params?: AnalyticsQueryParams): Promise<TenantAnalytics> {
    const { data } = await this.client.get<TenantAnalytics>('/analytics/tenants', { params })
    return data
  }

  getAnalyticsExportUrl(
    report: 'overview' | 'engagement' | 'users' | 'content' | 'feedback',
    format: 'csv' | 'pdf',
    params?: AnalyticsQueryParams
  ): string {
    const searchParams = new URLSearchParams({ report })
    if (params?.date_from) searchParams.set('date_from', params.date_from)
    if (params?.date_to) searchParams.set('date_to', params.date_to)
    return `${API_BASE_URL}/analytics/export/${format}?${searchParams.toString()}`
  }

  async downloadAnalyticsExport(
    report: 'overview' | 'engagement' | 'users' | 'content' | 'feedback',
    format: 'csv' | 'pdf',
    params?: AnalyticsQueryParams
  ): Promise<Blob> {
    const response = await this.client.get(`/analytics/export/${format}`, {
      params: { report, ...params },
      responseType: 'blob',
    })
    return response.data
  }
}

// Export singleton instance
export const api = new ApiClient()
