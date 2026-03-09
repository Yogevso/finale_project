import type { OpenApiSchema, OpenApiSchemas } from '@/lib/api/generated/openapi-contracts'
import type {
  AnalyticsOverview,
  Attachment,
  AttachmentOutlineResponse,
  AttachmentReaderViewResponse,
  AttachmentUploadResponse,
  Company,
  CompanyCreate,
  CompanyDocumentsResponse,
  CompanyListResponse,
  CompanyUpdate,
  CompanyUser,
  CompanyUserAdd,
  Comment,
  ContentAnalytics,
  EngagementAnalytics,
  Document,
  DocumentCreate,
  DocumentDetailPageBundle,
  DocumentListResponse,
  DocumentUpdate,
  FeedbackAnalytics,
  FeedbackDetailResponse,
  FeedbackListManagementResponse,
  AcceptInvitationRequest,
  Invitation,
  InvitationCreate,
  InvitationListResponse,
  InvitationValidateResponse,
  MessageResponse,
  NotificationCountResponse,
  NotificationListResponse,
  RbacPoliciesResponse,
  RbacPoliciesUpdate,
  ReviewAction,
  ReviewListResponse,
  ReviewRequest,
  ReviewSubmit,
  SystemSettingsResponse,
  SystemSettingsUpdate,
  RecentActivity,
  TenantAnalytics,
  TokenResponse,
  TopDocuments,
  User,
  UserAnalytics,
  Version,
  VersionCreate,
  VersionListResponse,
  VersionUpdate,
} from '@/types'

// Transport DTO contracts intentionally live at the API boundary.
// Core contracts are generated from OpenAPI and intersected with
// existing domain/UI types for strict compatibility during migration.
type Contract<Name extends string, Legacy> = Name extends keyof OpenApiSchemas
  ? Legacy & Partial<OpenApiSchema<Name>>
  : Legacy

export type TokenResponseDto = Contract<'TokenResponse', TokenResponse>
export type MessageResponseDto = Contract<'MessageResponse', MessageResponse>

export type UserDto = Contract<'UserResponse', User>
export type UserCreateDto = Contract<'UserCreate', {
  email: string
  username: string
  full_name: string
  password: string
  role: User['role']
  tenant_id?: number
}>
export type UserUpdateDto = Contract<'UserUpdate', {
  email?: string
  full_name?: string
  role?: User['role']
  is_active?: boolean
  tenant_id?: number | null
}>

export type DocumentDto = Document
export type DocumentCreateDto = Contract<'DocumentCreate', DocumentCreate>
export type DocumentUpdateDto = Contract<'DocumentUpdate', DocumentUpdate>
export type DocumentListResponseDto = DocumentListResponse
export type DocumentDetailPageBundleDto = DocumentDetailPageBundle

export type VersionDto = Contract<'VersionResponse', Version>
export type VersionCreateDto = Contract<'VersionCreate', VersionCreate>
export type VersionUpdateDto = Contract<'VersionUpdate', VersionUpdate>
export type VersionListResponseDto = Contract<'VersionListResponse', VersionListResponse>

export type CommentDto = Contract<'CommentResponse', Comment>

export type AnalyticsOverviewDto = Contract<'AnalyticsOverview', AnalyticsOverview>
export type RecentActivityDto = RecentActivity
export type EngagementAnalyticsDto = Contract<'EngagementAnalytics', EngagementAnalytics>
export type TopDocumentsDto = Contract<'TopDocuments', TopDocuments>
export type UserAnalyticsDto = Contract<'UserAnalytics', UserAnalytics>
export type ContentAnalyticsDto = Contract<'ContentAnalytics', ContentAnalytics>
export type FeedbackAnalyticsDto = Contract<'FeedbackAnalytics', FeedbackAnalytics>
export type TenantAnalyticsDto = Contract<'TenantAnalytics', TenantAnalytics>

export type AttachmentDto = Contract<'AttachmentResponse', Attachment>
export type AttachmentUploadResponseDto = Contract<'AttachmentUploadResponse', AttachmentUploadResponse>
export type AttachmentReaderViewResponseDto = Contract<'AttachmentReaderViewResponse', AttachmentReaderViewResponse>
export type AttachmentOutlineResponseDto = Contract<'AttachmentOutlineResponse', AttachmentOutlineResponse>

export type CompanyDto = Contract<'CompanyResponse', Company>
export type CompanyCreateDto = Contract<'CompanyCreate', CompanyCreate>
export type CompanyUpdateDto = Contract<'CompanyUpdate', CompanyUpdate>
export type CompanyListResponseDto = Contract<'CompanyListResponse', CompanyListResponse>
export type CompanyUserDto = Contract<'CompanyUserInfo', CompanyUser>
export type CompanyUserAddDto = Contract<'CompanyUserAdd', CompanyUserAdd>
export type CompanyDocumentsResponseDto = CompanyDocumentsResponse

export type InvitationDto = Contract<'InvitationResponse', Invitation>
export type InvitationCreateDto = Contract<'InvitationCreate', InvitationCreate>
export type InvitationListResponseDto = Contract<'InvitationListResponse', InvitationListResponse>
export type InvitationValidateResponseDto = Contract<'InvitationValidateResponse', InvitationValidateResponse>
export type AcceptInvitationRequestDto = Contract<'AcceptInvitationRequest', AcceptInvitationRequest>

export type NotificationListResponseDto = Contract<'NotificationListResponse', NotificationListResponse>
export type NotificationCountResponseDto = NotificationCountResponse

export type SystemSettingsResponseDto = Contract<'SystemSettingsResponse', SystemSettingsResponse>
export type SystemSettingsUpdateDto = Contract<'SystemSettingsUpdate', SystemSettingsUpdate>
export type RbacPoliciesResponseDto = Contract<'RbacPoliciesResponse', RbacPoliciesResponse>
export type RbacPoliciesUpdateDto = Contract<'RbacPoliciesUpdate', RbacPoliciesUpdate>

export type ReviewRequestDto = ReviewRequest
export type ReviewListResponseDto = ReviewListResponse
export type ReviewSubmitDto = Contract<'ReviewSubmit', ReviewSubmit>
export type ReviewActionDto = Contract<'ReviewAction', ReviewAction>
export type FeedbackDetailResponseDto = Contract<'FeedbackDetailResponse', FeedbackDetailResponse>
export type FeedbackListManagementResponseDto = Contract<'FeedbackListManagementResponse', FeedbackListManagementResponse>
export type ManagementFeedbackStatsDto = {
  total: number
  pending: number
  responded: number
  closed: number
  by_type: Record<string, number>
}

export type CollaborationTokenResponseDto = Contract<'CollabTokenResponse', {
  token: string
  document_id: number
  permissions: string[]
  websocket_url: string
  expires_in: number
}>

export type CollaborationStatusResponseDto = Contract<'CollaborationStatusResponse', {
  document_id: number
  active_collaborators: Array<{
    user_id: number
    username: string
    color: string
    is_editing: boolean
  }>
  is_collaborative_mode: boolean
  has_unsaved_changes: boolean
}>

export type CollaborationSessionStartResponseDto = Contract<'SessionStartResponse', {
  session_id: string
  document_id: number
  started_at: string
}>

export type CollaborationActivityFeedResponseDto = Contract<'ActivityFeedResponse', {
  document_id: number
  activities: Array<{
    id: number
    document_id: number
    user_id: number
    username: string
    activity_type: string
    details: Record<string, unknown> | null
    created_at: string
  }>
  total: number
  has_more: boolean
}>

export type CollaborationActiveSessionsResponseDto = {
  document_id: number
  sessions: Array<{
    session_id: string
    user_id: number
    username: string
    started_at: string
    last_activity_at: string
    edits_count: number
  }>
  count: number
}

export type CollaborationSnapshotDto = Contract<'SnapshotResponse', {
  id: number
  document_id: number
  snapshot_type: string
  name: string | null
  description: string | null
  state_size: number
  created_by: number | null
  created_by_username: string | null
  session_id: string | null
  is_pinned: boolean
  expires_at: string | null
  created_at: string
}>

export type CollaborationSnapshotListResponseDto = Contract<'SnapshotListResponse', {
  document_id: number
  snapshots: CollaborationSnapshotDto[]
  total: number
  has_more: boolean
}>

export type CollaborationRestoreSnapshotResponseDto = {
  message: string
  snapshot_id: number
  snapshot_name: string
  document_id: number
}

export type CollaborationAutoSnapshotResponseDto = {
  created: boolean
  reason?: string
  snapshot_id?: number
  snapshot_name?: string
}

export type SearchResultDto = Contract<'SearchResult', {
  id: number
  title: string
  document_number: string
  description: string | null
  category: string | null
  status: string
  created_at: string
  updated_at: string
  relevance_score: number
}>

export type SearchResponseDto = Contract<'SearchResponse', {
  items: SearchResultDto[]
  total: number
  query: string
  suggestions: string[]
}>

export type SearchAutocompleteResponseDto = {
  suggestions: string[]
}

export type SearchFacetsResponseDto = {
  categories: Array<{ name: string; count: number }>
  statuses: Array<{ name: string; count: number }>
}

export type SavedSearchDto = Contract<'SavedSearchResponse', {
  id: number
  name: string
  query: string | null
  category: string | null
  date_from?: string | null
  date_to?: string | null
  created_at: string
}>

export type SavedSearchCreateDto = Contract<'SavedSearchCreate', {
  name: string
  query?: string
  category?: string
  date_from?: string | null
  date_to?: string | null
}>

export type BookmarkDto = Contract<'BookmarkResponse', {
  id: number
  document_id: number
  document_title: string
  document_number: string
  created_at: string
}>

export type BookmarkStatusDto = {
  is_bookmarked: boolean
}

export type FeedbackSubmissionDto = Contract<'app__api__management__engagement__FeedbackResponse', {
  id: number
  document_id: number
  is_helpful: boolean
  comment: string | null
  created_at: string
}>

export type FeedbackStatsDto = Contract<'FeedbackStats', {
  document_id: number
  helpful_count: number
  not_helpful_count: number
  total_count: number
  helpful_percentage: number
}>

export type MyFeedbackDto = {
  has_feedback: boolean
  is_helpful: boolean | null
  comment?: string | null
}

export type ReadingProgressDto = Contract<'ReadingProgressResponse', {
  id: number
  document_id: number
  document_title: string
  progress_percent: number
  last_read_at: string
  completed_at: string | null
}>

export type DocumentProgressDto = {
  has_progress: boolean
  progress_percent: number
  is_completed: boolean
  last_read_at?: string
}

export type EngagementStatsDto = {
  bookmarks: number
  feedbacks_given: number
  documents_started: number
  documents_completed: number
}
