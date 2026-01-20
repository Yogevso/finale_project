// User types
export type UserRole = 'super_admin' | 'admin' | 'editor' | 'viewer'

export interface User {
  id: number
  email: string
  username: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserCreate {
  email: string
  username: string
  full_name: string
  password: string
  role?: UserRole
}

export interface UserUpdate {
  email?: string
  full_name?: string
  role?: UserRole
  is_active?: boolean
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
export type DocumentStatus = 'draft' | 'active' | 'archived'

export interface Document {
  id: number
  title: string
  document_number: string
  description: string | null
  status: DocumentStatus
  category: string | null
  tags: string | null
  created_by: number
  created_at: string
  updated_at: string
  created_by_user?: User
  versions_count?: number
  attachments_count?: number
  comments_count?: number
}

export interface DocumentCreate {
  title: string
  description?: string
  status?: DocumentStatus
  category?: string
  tags?: string
}

export interface DocumentUpdate {
  title?: string
  description?: string
  status?: DocumentStatus
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
