// User types
export type UserRole = 'system_admin' | 'admin' | 'manager' | 'editor' | 'viewer' | 'customer'

export interface User {
  id: number
  email: string
  username: string
  full_name: string
  role: UserRole
  is_active: boolean
  tenant_id?: number
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
export type DocumentStatus = 'draft' | 'pending_review' | 'active' | 'archived'
export type DocumentVisibility = 'public' | 'internal' | 'company'

export interface Document {
  id: number
  title: string
  document_number: string
  description: string | null
  status: DocumentStatus
  visibility: DocumentVisibility
  category: string | null
  tags: string | null
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
  status?: DocumentStatus
  visibility?: DocumentVisibility
  category?: string
  tags?: string
}

export interface DocumentUpdate {
  title?: string
  description?: string
  status?: DocumentStatus
  visibility?: DocumentVisibility
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

// Version types
export interface Version {
  id: number
  document_id: number
  version_number: number
  content: string | null
  changes_summary: string | null
  is_published: boolean
  published_at: string | null
  created_by: number
  created_at: string
}

export interface VersionCreate {
  content?: string
  changes_summary?: string
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
  mime_type: string
  uploaded_by: number
  uploaded_at: string
  uploader_name?: string  // populated from join
}

export interface AttachmentUploadResponse {
  id: number
  filename: string
  url: string
  message: string
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
  category?: string
  search?: string
}

// Notification types
export type NotificationType = 
  | 'DOCUMENT_CREATED'
  | 'DOCUMENT_UPDATED'
  | 'DOCUMENT_PUBLISHED'
  | 'COMMENT_ADDED'
  | 'COMMENT_REPLY'
  | 'VERSION_PUBLISHED'
  | 'REVIEW_SUBMITTED'
  | 'REVIEW_APPROVED'
  | 'REVIEW_REJECTED'
  | 'FEEDBACK_RECEIVED'
  | 'FEEDBACK_RESPONDED'
  | 'SYSTEM'

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

export function canManageUsers(role: UserRole): boolean {
  return ['system_admin', 'admin', 'manager'].includes(role)
}

export function canPublishDocuments(role: UserRole): boolean {
  return CAN_PUBLISH_ROLES.includes(role)
}

export function canEditDocuments(role: UserRole): boolean {
  return CAN_EDIT_ROLES.includes(role)
}
