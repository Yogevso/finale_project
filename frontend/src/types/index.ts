// User types
export type UserRole = 'system_admin' | 'admin' | 'manager' | 'editor' | 'viewer' | 'customer'

export type Permission =
  | 'view_public_docs'
  | 'view_internal_docs'
  | 'view_company_docs'
  | 'create_document'
  | 'edit_document'
  | 'delete_document'
  | 'submit_review'
  | 'approve_review'
  | 'approve_peer_review'
  | 'publish_document'
  | 'assign_companies'
  | 'add_comments'
  | 'submit_feedback'
  | 'download_attachments'
  | 'manage_users'
  | 'manage_editors'
  | 'manage_companies'
  | 'system_settings'
  | 'manage_admins'

export interface User {
  id: number
  email: string
  username: string
  full_name: string
  role: UserRole
  is_active: boolean
  tenant_id?: number
  timezone?: string
  locale?: string
  notification_preferences?: Record<string, boolean>
  avatar_url?: string | null
  permissions?: Permission[]
  tenant?: Tenant
  company_name?: string
  company_slug?: string
  created_at: string
  updated_at: string
}

export interface UserCreate {
  email: string
  username: string
  full_name: string
  password: string
  role?: UserRole
  tenant_id?: number
}

export interface UserUpdate {
  email?: string
  full_name?: string
  role?: UserRole
  is_active?: boolean
  tenant_id?: number
}

export interface UserSession {
  id: number
  ip_address?: string | null
  user_agent?: string | null
  created_at: string
  last_active_at: string
  is_current: boolean
}

export interface UserSessionListResponse {
  items: UserSession[]
  total: number
}

export interface SessionBulkRevokeResponse {
  message: string
  revoked_count: number
}

export interface SecurityEvent {
  id: number
  event_type: string
  ip_address?: string | null
  user_agent?: string | null
  created_at: string
}

export interface SecurityEventListResponse {
  items: SecurityEvent[]
  total: number
  page: number
  page_size: number
  pages: number
}

// Auth types
export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string | null
  token_type: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface PasswordChange {
  old_password: string
  new_password: string
}

// Document types
export type DocumentStatus = 'draft' | 'pending_review' | 'approved' | 'active' | 'archived'
export type DocumentVisibility = 'public' | 'internal' | 'company'

export interface Document {
  id: number
  title: string
  document_number: string
  description: string | null
  version_label?: string | null
  topic?: string | null
  platform?: string | null
  platform_id?: number | null
  release_branch?: string | null
  due_date?: string | null
  status: DocumentStatus
  visibility: DocumentVisibility
  category: string | null
  tags: string | null
  parent_id?: number | null
  row_version?: number
  etag?: string
  created_by: number
  created_at: string
  updated_at: string
  created_by_user?: User
  versions_count?: number
  attachments_count?: number
  comments_count?: number
  assigned_companies?: Tenant[]
}

export interface DocumentCreate {
  title: string
  description?: string
  version_label?: string
  topic?: string
  platform?: string
  platform_id?: number
  release_branch?: string
  due_date?: string | null
  document_number?: string
  parent_id?: number
  status?: DocumentStatus
  visibility?: DocumentVisibility
  company_ids?: number[]
  category?: string
  tags?: string
}

export interface DocumentUpdate {
  title?: string
  description?: string
  version_label?: string
  topic?: string
  platform?: string
  platform_id?: number
  release_branch?: string
  due_date?: string | null
  status?: DocumentStatus
  visibility?: DocumentVisibility
  reason?: string
  company_ids?: number[]
  category?: string
  tags?: string
}

export interface DocumentListResponse {
  items: Document[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface DocumentWatchStatus {
  is_watching: boolean
}

export interface DocumentWatchResponse {
  document_id: number
  user_id: number
  is_watching: boolean
  watched_at: string | null
}

export interface DocumentArchiveResult {
  document_id: number
  status: DocumentStatus | 'archived'
  previous_status?: DocumentStatus | null
  visibility?: DocumentVisibility
}

export interface DocumentCalendarExport {
  document_id: number
  filename: string
  content_type: string
  due_date: string
  ical: string
}

export interface DocumentDashboardStats {
  total: number
  published: number
  approved: number
  draft: number
}

export interface AudienceAccessTargetCompany {
  id: number
  name: string
  slug: string
}

export interface AudienceAccessPreview {
  visibility: DocumentVisibility
  is_public: boolean
  includes_internal_users: boolean
  target_companies: AudienceAccessTargetCompany[]
  access_summary: string
}

export interface DocumentDetailPageBundle {
  document: Document
  attachments: Attachment[]
  assigned_companies: Company[]
  audience_access_preview: AudienceAccessPreview
  review_history: ReviewListResponse
}

// Version types
export type VersionBumpType = 'major' | 'minor' | 'patch'

export interface VersionReviewSummary {
  id: number
  status: ReviewStatus
  submitted_at: string
  reviewed_at?: string | null
  submitted_by: number
  reviewed_by?: number | null
  submitter?: User
  reviewer?: User
}

export interface Version {
  id: number
  document_id: number
  version_number: number
  semantic_version?: string | null
  bump_type?: VersionBumpType
  row_version?: number
  etag?: string
  content: string | null
  changes_summary: string | null
  is_published: boolean
  published_at: string | null
  published_by?: number | null
  created_by: number
  created_at: string
  created_by_user?: User
  published_by_user?: User
  latest_review?: VersionReviewSummary | null
}

export interface VersionCreate {
  content?: string
  changes_summary?: string
  bump_type?: VersionBumpType
}

export interface VersionUpdate {
  content?: string
  changes_summary?: string
}

export interface VersionListResponse {
  items: Version[]
  total: number
}

// Attachment types
export interface Attachment {
  id: number
  document_id: number
  filename: string
  original_filename: string
  file_size: number
  size_bytes?: number
  mime_type: string
  sha256?: string
  reader_html_status?: 'pending' | 'processing' | 'ready' | 'failed' | null
  reader_toc_source?: 'headings' | 'slides' | 'none' | string | null
  uploaded_by: number
  uploaded_at: string
  uploader_name?: string  // populated from join
}

export interface AttachmentUploadResponse {
  id: number
  filename: string
  sha256?: string
  url: string
  message: string
}

export interface AttachmentExtractionWarning {
  code: string
  message: string
  count?: number | null
}

export interface AttachmentReaderViewResponse {
  attachment_id: number
  status: 'pending' | 'processing' | 'ready' | 'failed' | string
  html_content: string | null
  toc_items: AttachmentOutlineItem[]
  toc_source: 'headings' | 'slides' | 'none' | string | null
  warnings?: AttachmentExtractionWarning[]
  confidence?: number | null
  error: string | null
  generated_at: string | null
}

export interface AttachmentOutlineItem {
  id: string
  level: number
  title: string
  page: number
  page_start: number
  page_end?: number | null
  anchor_id?: string | null
}

// Comment types
export interface Comment {
  id: number
  document_id: number
  user_id: number
  author_id?: number  // alias for user_id
  author_name?: string // populated from join
  parent_id: number | null
  content: string
  is_private: boolean
  anchor_text?: string | null
  anchor_id?: string | null
  is_resolved: boolean
  created_at: string
  updated_at: string
  user?: {
    id: number
    username: string
    full_name?: string
    role: string
  }
  replies: Comment[]
  reply_count: number
}

export interface CommentCreate {
  content: string
  is_private?: boolean
  anchor_text?: string
  anchor_id?: string
  parent_id?: number
}

export interface CommentUpdate {
  content?: string
  is_resolved?: boolean
}

// Audit types
export type ActionType = 'create' | 'update' | 'delete' | 'view' | 'download'

export interface AuditLog {
  id: number
  user_id: number | null
  document_id: number | null
  action: ActionType
  details: string | null
  ip_address: string | null
  created_at: string
  user?: User
}

// API response types
export interface MessageResponse {
  message: string
}

export interface ErrorResponse {
  detail: string
}

// Query params
export interface DocumentQueryParams {
  page?: number
  page_size?: number
  status?: DocumentStatus
  visibility?: DocumentVisibility
  category?: string
  search?: string
  company_id?: number
  date_from?: string
  date_to?: string
}

export interface DuplicateDocumentMatch {
  document_id: number
  title: string
  document_number: string
  similarity: number
}

export interface DuplicateCheckResponse {
  title: string
  threshold: number
  has_matches: boolean
  matches: DuplicateDocumentMatch[]
}

export interface BulkDocumentMetadataUpdate {
  document_ids: number[]
  category?: string
  visibility?: DocumentVisibility
  company_ids?: number[]
  reason?: string
}

export interface BulkDocumentMetadataUpdateResponse {
  updated_count: number
  document_ids: number[]
  message: string
}

export interface SavedSearch {
  id: number
  name: string
  query: string | null
  category: string | null
  date_from?: string | null
  date_to?: string | null
  created_at: string
}

// Notification types
export type NotificationType = 
  | 'document_created'
  | 'document_updated'
  | 'document_published'
  | 'comment_added'
  | 'comment_reply'
  | 'version_published'
  | 'review_submitted'
  | 'review_approved'
  | 'review_rejected'
  | 'review_reminder'
  | 'review_escalated'
  | 'feedback_received'
  | 'feedback_responded'
  | 'invitation_sent'
  | 'system'

export interface Notification {
  id: number
  type: NotificationType
  title: string
  message: string | null
  link: string | null
  is_read: boolean
  read_at: string | null
  created_at: string
}

export interface NotificationListResponse {
  items: Notification[]
  total: number
  unread_count: number
}

export interface NotificationCountResponse {
  unread_count: number
}

// Tenant/Company types
export type CompanyType = 'customer' | 'partner' | 'internal'

export interface Tenant {
  id: number
  name: string
  slug: string
  is_active: boolean
  company_logo?: string | null
  contact_email?: string | null
  company_type: CompanyType
  created_at: string
  updated_at: string
}

export interface TenantCreate {
  name: string
  slug?: string
  contact_email?: string
  company_type?: CompanyType
  is_active?: boolean
}

export interface TenantUpdate {
  name?: string
  slug?: string
  contact_email?: string
  company_type?: CompanyType
  is_active?: boolean
  company_logo?: string
}

export interface TenantListResponse {
  items: Tenant[]
  total: number
}

export interface SystemSettingsResponse {
  settings: Record<string, unknown>
}

export interface SystemSettingsUpdate {
  settings: Record<string, unknown>
}

export interface RbacPolicy {
  role: UserRole
  permissions: Permission[]
}

export interface RbacPoliciesResponse {
  policies: RbacPolicy[]
}

export interface RbacPoliciesUpdate {
  policies: RbacPolicy[]
}

// Extended Company types for admin management
export interface CompanyUser {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

export interface Company extends Tenant {
  user_count: number
  owned_document_count: number
  assigned_document_count: number
  customer_visible_document_count: number
  // Backward-compatible alias from API; mirrors assigned_document_count.
  document_count: number
  users?: CompanyUser[]
}

export interface CompanyListResponse {
  items: Company[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface CompanyCreate {
  name: string
  slug?: string
  contact_email?: string
  company_type?: CompanyType
  company_logo?: string
  is_active?: boolean
}

export interface CompanyUpdate {
  name?: string
  slug?: string
  contact_email?: string
  company_type?: CompanyType
  company_logo?: string
  is_active?: boolean
}

export interface CompanyUserAdd {
  user_id?: number
  email?: string
}

export interface CompanyDocument {
  id: number
  title: string
  category: string | null
  status: DocumentStatus
  visibility: DocumentVisibility
  updated_at: string
}

export interface CompanyDocumentsResponse {
  items: CompanyDocument[]
  total: number
  page: number
  per_page: number
  pages: number
  scope?: 'assigned' | 'owned' | 'customer_visible'
}

// Review types
export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'

export interface ReviewRequest {
  id: number
  document_id: number
  version_id?: number | null
  submitted_by: number
  reviewed_by?: number | null
  status: ReviewStatus
  message?: string | null
  review_comments?: string | null
  submitted_at: string
  reviewed_at?: string | null
  created_at: string
  document?: Document
  submitter?: User
  reviewer?: User
}

export interface ReviewSubmit {
  version_id?: number
  message?: string
}

export interface ReviewAction {
  comments?: string
}

export interface ReviewListResponse {
  items: ReviewRequest[]
  total: number
  page: number
  per_page: number
  has_more: boolean
}

// Feedback types (customer portal)
export type FeedbackType = 'question' | 'suggestion' | 'issue' | 'other'
export type FeedbackStatus = 'pending' | 'responded' | 'closed'

export interface Feedback {
  id: number
  user_id: number
  document_id: number
  feedback_type: FeedbackType
  status: FeedbackStatus
  content: string
  response?: string | null
  responded_by?: number | null
  responded_at?: string | null
  created_at: string
  user?: User
  document?: Document
  responder?: User
}

export interface FeedbackCreate {
  document_id: number
  feedback_type: FeedbackType
  content: string
}

export interface FeedbackResponse {
  response: string
  status?: FeedbackStatus
}

export interface FeedbackDetailResponse {
  id: number
  document_id: number
  document_title: string
  document_number: string
  user_id: number
  user_name: string
  user_email: string
  tenant_id?: number | null
  tenant_name?: string | null
  feedback_type: FeedbackType
  status: FeedbackStatus
  content: string
  response?: string | null
  responded_by?: number | null
  responder_name?: string | null
  responded_at?: string | null
  created_at: string
}

export interface FeedbackListManagementResponse {
  items: FeedbackDetailResponse[]
  total: number
  page: number
  per_page: number
  has_more: boolean
}

export interface FeedbackListResponse {
  items: Feedback[]
  total: number
}

// Role helpers
export const INTERNAL_ROLES: UserRole[] = ['system_admin', 'admin', 'manager', 'editor', 'viewer']
export const ADMIN_ROLES: UserRole[] = ['system_admin', 'admin']
export const CAN_PUBLISH_ROLES: UserRole[] = ['system_admin', 'admin', 'manager']
export const CAN_EDIT_ROLES: UserRole[] = ['system_admin', 'admin', 'manager', 'editor']

export function isInternalUser(role: UserRole): boolean {
  return role !== 'customer'
}

// ========== Invitation Types ==========
export type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'cancelled'

export interface Invitation {
  id: number
  email: string
  role: UserRole
  tenant_id?: number
  tenant_name?: string
  invited_by: number
  inviter_name: string
  status: InvitationStatus
  message?: string
  expires_at: string
  created_at: string
  accepted_at?: string
}

export interface InvitationListResponse {
  items: Invitation[]
  total: number
  page: number
  per_page: number
  has_more: boolean
}

export interface InvitationCreate {
  email: string
  role: UserRole
  tenant_id?: number
  message?: string
}

export interface InvitationValidateResponse {
  valid: boolean
  email?: string
  role?: string
  company_name?: string
  inviter_name?: string
  message?: string
  expires_at?: string
}

export interface AcceptInvitationRequest {
  token: string
  username: string
  full_name: string
  password: string
}

// ========== Analytics Types ==========

export type TimeGranularity = 'daily' | 'weekly' | 'monthly'

export interface TimeSeriesPoint {
  date: string
  value: number
}

export interface DocumentStats {
  document_id: number
  document_number: string
  title: string
  view_count: number
  download_count: number
}

export interface CategoryCount {
  category: string
  count: number
}

export interface AssignmentChurnItem {
  document_id: number
  churn_count: number
}

export interface RecentActivity {
  id: number
  action: string
  document_id?: number
  document_title?: string
  user_id: number
  user_name: string
  created_at: string
  details?: string
}

export interface AnalyticsOverview {
  period_start: string
  period_end: string
  total_documents: number
  total_users: number
  total_views: number
  total_downloads: number
  documents_by_status: Record<string, number>
  documents_by_category: CategoryCount[]
  by_audience_type?: Record<string, number>
  pending_reviews: number
  views_today: number
  new_docs_this_week: number
  exposure_risk_transitions_30d?: number
  assignment_churn_90d?: AssignmentChurnItem[]
}

export interface CompanyAudienceAnalytics {
  company_id: number
  company_name: string
  document_count: number
  active_document_count: number
  company_visible_document_count: number
  view_count_30d: number
  download_count_30d: number
  assignment_churn_90d: number
}

export interface AudienceAlertRule {
  id: string
  metric: string
  threshold: number
  window_minutes: number
  document_id?: number | null
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface AudienceAlertRuleCreate {
  metric: string
  threshold: number
  window_minutes: number
  document_id?: number | null
  enabled?: boolean
}

export interface EngagementAnalytics {
  period_start: string
  period_end: string
  granularity: TimeGranularity
  views_over_time: TimeSeriesPoint[]
  downloads_over_time: TimeSeriesPoint[]
  unique_visitors: number
  avg_reading_progress: number
  completion_rate: number
  total_time_spent_minutes: number
}

export interface TopDocuments {
  by_views: DocumentStats[]
  by_downloads: DocumentStats[]
}

export interface UserActivityItem {
  user_id: number
  username: string
  full_name: string
  role: string
  action_count: number
  last_active?: string
}

export interface UserAnalytics {
  period_start: string
  period_end: string
  granularity: TimeGranularity
  total_users: number
  active_users: number
  inactive_users: number
  users_by_role: Record<string, number>
  new_users_over_time: TimeSeriesPoint[]
  most_active_users: UserActivityItem[]
}

export interface ContentAnalytics {
  period_start: string
  period_end: string
  granularity: TimeGranularity
  documents_created_over_time: TimeSeriesPoint[]
  versions_published_over_time: TimeSeriesPoint[]
  comments_over_time: TimeSeriesPoint[]
  avg_review_turnaround_hours: number | null
  approval_rate: number
  reviews_by_status: Record<string, number>
  total_documents_created: number
  total_versions_published: number
  total_comments: number
}

export interface FeedbackAnalytics {
  period_start: string
  period_end: string
  granularity: TimeGranularity
  total_feedback: number
  pending_feedback: number
  responded_feedback: number
  feedback_by_type: Record<string, number>
  feedback_by_status: Record<string, number>
  feedback_over_time: TimeSeriesPoint[]
  avg_response_time_hours: number | null
  helpfulness_rate: number
}

export interface TenantMetrics {
  tenant_id: number
  tenant_name: string
  total_documents: number
  total_users: number
  active_users_30d: number
  total_views_30d: number
  health_score: number
}

export interface TenantAnalytics {
  period_start: string
  period_end: string
  total_tenants: number
  active_tenants: number
  tenants: TenantMetrics[]
}

export interface AnalyticsQueryParams {
  date_from?: string
  date_to?: string
  granularity?: TimeGranularity
}

export function canManageUsers(role: UserRole): boolean {
  return ['system_admin', 'admin', 'manager'].includes(role)
}

export function canPublishDocuments(role: UserRole): boolean {
  return CAN_PUBLISH_ROLES.includes(role)
}

export function canEditDocuments(role: UserRole): boolean {
  return CAN_EDIT_ROLES.includes(role)
}
