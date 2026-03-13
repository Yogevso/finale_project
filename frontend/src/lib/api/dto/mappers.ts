import type {
  AudienceAccessPreview,
  AnalyticsOverview,
  Attachment,
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
  Invitation,
  InvitationCreate,
  InvitationListResponse,
  InvitationValidateResponse,
  MessageResponse,
  NotificationCountResponse,
  NotificationListResponse,
  ReviewAction,
  ReviewListResponse,
  ReviewRequest,
  ReviewSubmit,
  RbacPoliciesResponse,
  RbacPoliciesUpdate,
  SystemSettingsResponse,
  SystemSettingsUpdate,
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
import type {
  AcceptInvitationRequestDto,
  AnalyticsOverviewDto,
  AttachmentDto,
  AttachmentReaderViewResponseDto,
  AttachmentUploadResponseDto,
  CollaborationActiveSessionsResponseDto,
  CollaborationActivityFeedResponseDto,
  CollaborationAutoSnapshotResponseDto,
  CollaborationRestoreSnapshotResponseDto,
  CollaborationSessionStartResponseDto,
  CollaborationSnapshotDto,
  CollaborationSnapshotListResponseDto,
  CollaborationStatusResponseDto,
  CollaborationTokenResponseDto,
  BookmarkDto,
  BookmarkStatusDto,
  CompanyCreateDto,
  CompanyDocumentsResponseDto,
  CompanyDto,
  CompanyListResponseDto,
  CompanyUpdateDto,
  CompanyUserAddDto,
  CompanyUserDto,
  CommentDto,
  ContentAnalyticsDto,
  DocumentCreateDto,
  DocumentDetailPageBundleDto,
  DocumentDto,
  DocumentListResponseDto,
  DocumentUpdateDto,
  EngagementAnalyticsDto,
  FeedbackAnalyticsDto,
  FeedbackDetailResponseDto,
  FeedbackListManagementResponseDto,
  InvitationCreateDto,
  InvitationDto,
  InvitationListResponseDto,
  InvitationValidateResponseDto,
  ManagementFeedbackStatsDto,
  MessageResponseDto,
  MyFeedbackDto,
  NotificationCountResponseDto,
  NotificationListResponseDto,
  RecentActivityDto,
  ReadingProgressDto,
  ReviewActionDto,
  ReviewListResponseDto,
  ReviewRequestDto,
  ReviewSubmitDto,
  SavedSearchCreateDto,
  SavedSearchDto,
  SearchAutocompleteResponseDto,
  SearchFacetsResponseDto,
  SearchResponseDto,
  RbacPoliciesResponseDto,
  RbacPoliciesUpdateDto,
  SystemSettingsResponseDto,
  SystemSettingsUpdateDto,
  TenantAnalyticsDto,
  FeedbackStatsDto,
  FeedbackSubmissionDto,
  DocumentProgressDto,
  EngagementStatsDto,
  TokenResponseDto,
  TopDocumentsDto,
  UserCreateDto,
  UserDto,
  UserUpdateDto,
  UserAnalyticsDto,
  VersionCreateDto,
  VersionDto,
  VersionListResponseDto,
  VersionUpdateDto,
} from './contracts'

export function mapTokenResponseDto(dto: TokenResponseDto): TokenResponse {
  return { ...dto }
}

export function mapMessageResponseDto(dto: MessageResponseDto): MessageResponse {
  return { ...dto }
}

export function mapSystemSettingsResponseDto(
  dto: SystemSettingsResponseDto,
): SystemSettingsResponse {
  return { settings: { ...dto.settings } }
}

export function toSystemSettingsUpdateDto(
  payload: SystemSettingsUpdate,
): SystemSettingsUpdateDto {
  return { settings: { ...payload.settings } }
}

export function mapRbacPoliciesResponseDto(
  dto: RbacPoliciesResponseDto,
): RbacPoliciesResponse {
  return {
    policies: dto.policies.map((policy) => ({
      role: policy.role,
      permissions: [...policy.permissions],
    })),
  }
}

export function toRbacPoliciesUpdateDto(payload: RbacPoliciesUpdate): RbacPoliciesUpdateDto {
  return {
    policies: payload.policies.map((policy) => ({
      role: policy.role,
      permissions: [...policy.permissions],
    })),
  }
}

export function mapUserDto(dto: UserDto): User {
  return { ...dto }
}

export function mapUsersDto(dtos: UserDto[]): User[] {
  return dtos.map(mapUserDto)
}

export function toUserCreateDto(payload: {
  email: string
  username: string
  full_name: string
  password: string
  role: User['role']
  tenant_id?: number
}): UserCreateDto {
  return { ...payload }
}

export function toUserUpdateDto(payload: {
  email?: string
  full_name?: string
  role?: User['role']
  is_active?: boolean
  tenant_id?: number | null
}): UserUpdateDto {
  return { ...payload }
}

export function mapDocumentDto(dto: DocumentDto): Document {
  return {
    ...dto,
    created_by_user: dto.created_by_user ? mapUserDto(dto.created_by_user) : undefined,
  }
}

export function mapDocumentListResponseDto(
  dto: DocumentListResponseDto,
): DocumentListResponse {
  return {
    ...dto,
    items: dto.items.map(mapDocumentDto),
  }
}

export function mapDocumentDetailPageBundleDto(
  dto: DocumentDetailPageBundleDto,
): DocumentDetailPageBundle {
  const fallbackAudienceAccessPreview = {
    visibility: dto.document.visibility,
    is_public: dto.document.visibility === 'public',
    includes_internal_users: true,
    target_companies: dto.assigned_companies.map((company) => ({
      id: company.id,
      name: company.name,
      slug: company.slug,
    })),
    access_summary: 'Audience preview unavailable.',
  }
  const previewSource = dto.audience_access_preview ?? fallbackAudienceAccessPreview
  const audienceAccessPreview: AudienceAccessPreview = {
    visibility: previewSource.visibility,
    is_public: previewSource.is_public,
    includes_internal_users: previewSource.includes_internal_users,
    target_companies: previewSource.target_companies.map((company) => ({
      id: company.id,
      name: company.name,
      slug: company.slug,
    })),
    access_summary: previewSource.access_summary,
  }

  return {
    document: mapDocumentDto(dto.document),
    attachments: dto.attachments.map(mapAttachmentDto),
    assigned_companies: dto.assigned_companies.map(mapCompanyDto),
    audience_access_preview: audienceAccessPreview,
    review_history: mapReviewListResponseDto(dto.review_history),
  }
}

function normalizeOptionalDate(value: string | null | undefined): string | null | undefined {
  if (value === '') {
    return null
  }
  return value
}

export function toDocumentCreateDto(payload: DocumentCreate): DocumentCreateDto {
  return {
    ...payload,
    due_date: normalizeOptionalDate(payload.due_date),
  }
}

export function toDocumentUpdateDto(payload: DocumentUpdate): DocumentUpdateDto {
  return {
    ...payload,
    due_date: normalizeOptionalDate(payload.due_date),
  }
}

export function mapVersionDto(dto: VersionDto): Version {
  return {
    ...dto,
    created_by_user: dto.created_by_user ? mapUserDto(dto.created_by_user) : undefined,
    published_by_user: dto.published_by_user ? mapUserDto(dto.published_by_user) : undefined,
    latest_review: dto.latest_review ? { ...dto.latest_review } : dto.latest_review,
  }
}

export function mapVersionListResponseDto(dto: VersionListResponseDto): VersionListResponse {
  const items = (dto.items as VersionDto[]).map((item) => mapVersionDto(item))

  return {
    ...dto,
    items,
  }
}

export function toVersionCreateDto(payload: VersionCreate): VersionCreateDto {
  return { ...payload }
}

export function toVersionUpdateDto(payload: VersionUpdate): VersionUpdateDto {
  return { ...payload }
}

export function mapCommentDto(dto: CommentDto): Comment {
  return {
    ...dto,
    user: dto.user ? { ...dto.user } : dto.user,
    replies: dto.replies.map(mapCommentDto),
  }
}

export function mapCommentsDto(dtos: CommentDto[]): Comment[] {
  return dtos.map(mapCommentDto)
}

export function mapAnalyticsOverviewDto(dto: AnalyticsOverviewDto): AnalyticsOverview {
  return {
    ...dto,
    documents_by_category: dto.documents_by_category.map((item) => ({ ...item })),
  }
}

export function mapRecentActivityDto(dto: RecentActivityDto): RecentActivityDto {
  return { ...dto }
}

export function mapRecentActivitiesDto(dtos: RecentActivityDto[]): RecentActivityDto[] {
  return dtos.map(mapRecentActivityDto)
}

export function mapEngagementAnalyticsDto(dto: EngagementAnalyticsDto): EngagementAnalytics {
  return {
    ...dto,
    views_over_time: dto.views_over_time.map((point) => ({ ...point })),
    downloads_over_time: dto.downloads_over_time.map((point) => ({ ...point })),
  }
}

export function mapTopDocumentsDto(dto: TopDocumentsDto): TopDocuments {
  return {
    by_views: dto.by_views.map((item) => ({ ...item })),
    by_downloads: dto.by_downloads.map((item) => ({ ...item })),
  }
}

export function mapUserAnalyticsDto(dto: UserAnalyticsDto): UserAnalytics {
  return {
    ...dto,
    new_users_over_time: dto.new_users_over_time.map((point) => ({ ...point })),
    most_active_users: dto.most_active_users.map((item) => ({ ...item })),
  }
}

export function mapContentAnalyticsDto(dto: ContentAnalyticsDto): ContentAnalytics {
  return {
    ...dto,
    documents_created_over_time: dto.documents_created_over_time.map((point) => ({ ...point })),
    versions_published_over_time: dto.versions_published_over_time.map((point) => ({ ...point })),
    comments_over_time: dto.comments_over_time.map((point) => ({ ...point })),
  }
}

export function mapFeedbackAnalyticsDto(dto: FeedbackAnalyticsDto): FeedbackAnalytics {
  return {
    ...dto,
    feedback_over_time: dto.feedback_over_time.map((point) => ({ ...point })),
  }
}

export function mapTenantAnalyticsDto(dto: TenantAnalyticsDto): TenantAnalytics {
  return {
    ...dto,
    tenants: dto.tenants.map((item) => ({ ...item })),
  }
}

export function mapAttachmentDto(dto: AttachmentDto): Attachment {
  return { ...dto }
}

export function mapAttachmentsDto(dtos: AttachmentDto[]): Attachment[] {
  return dtos.map(mapAttachmentDto)
}

export function mapAttachmentUploadResponseDto(
  dto: AttachmentUploadResponseDto,
): AttachmentUploadResponse {
  return { ...dto }
}

export function mapAttachmentReaderViewResponseDto(
  dto: AttachmentReaderViewResponseDto,
): AttachmentReaderViewResponse {
  return {
    ...dto,
    toc_items: dto.toc_items.map((item) => ({ ...item })),
    warnings: (dto.warnings || []).map((item) => ({ ...item })),
  }
}

export function mapCompanyUserDto(dto: CompanyUserDto): CompanyUser {
  return { ...dto }
}

export function mapCompanyUsersDto(dtos: CompanyUserDto[]): CompanyUser[] {
  return dtos.map(mapCompanyUserDto)
}

export function mapCompanyDto(dto: CompanyDto): Company {
  return {
    ...dto,
    users: dto.users ? mapCompanyUsersDto(dto.users) : dto.users,
  }
}

export function mapCompanyListResponseDto(dto: CompanyListResponseDto): CompanyListResponse {
  return {
    ...dto,
    items: dto.items.map(mapCompanyDto),
  }
}

export function toCompanyCreateDto(payload: CompanyCreate): CompanyCreateDto {
  return { ...payload }
}

export function toCompanyUpdateDto(payload: CompanyUpdate): CompanyUpdateDto {
  return { ...payload }
}

export function toCompanyUserAddDto(payload: CompanyUserAdd): CompanyUserAddDto {
  return { ...payload }
}

export function mapCompanyDocumentsResponseDto(
  dto: CompanyDocumentsResponseDto,
): CompanyDocumentsResponse {
  return {
    ...dto,
    items: dto.items.map((item) => ({ ...item })),
  }
}

export function mapInvitationDto(dto: InvitationDto): Invitation {
  return { ...dto }
}

export function mapInvitationListResponseDto(
  dto: InvitationListResponseDto,
): InvitationListResponse {
  return {
    ...dto,
    items: dto.items.map(mapInvitationDto),
  }
}

export function toInvitationCreateDto(payload: InvitationCreate): InvitationCreateDto {
  return { ...payload }
}

export function mapInvitationValidateResponseDto(
  dto: InvitationValidateResponseDto,
): InvitationValidateResponse {
  return { ...dto }
}

export function toAcceptInvitationRequestDto(
  payload: AcceptInvitationRequestDto,
): AcceptInvitationRequestDto {
  return { ...payload }
}

export function mapNotificationListResponseDto(
  dto: NotificationListResponseDto,
): NotificationListResponse {
  return {
    ...dto,
    items: dto.items.map((item) => ({ ...item })),
  }
}

export function mapNotificationCountResponseDto(
  dto: NotificationCountResponseDto,
): NotificationCountResponse {
  return { ...dto }
}

export function mapReviewRequestDto(dto: ReviewRequestDto): ReviewRequest {
  return {
    ...dto,
    document: dto.document ? mapDocumentDto(dto.document) : dto.document,
    submitter: dto.submitter ? mapUserDto(dto.submitter) : dto.submitter,
    reviewer: dto.reviewer ? mapUserDto(dto.reviewer) : dto.reviewer,
  }
}

export function mapReviewListResponseDto(dto: ReviewListResponseDto): ReviewListResponse {
  return {
    ...dto,
    items: dto.items.map(mapReviewRequestDto),
  }
}

export function toReviewSubmitDto(payload: ReviewSubmit): ReviewSubmitDto {
  return { ...payload }
}

export function toReviewActionDto(payload: ReviewAction): ReviewActionDto {
  return { ...payload }
}

export function mapFeedbackDetailResponseDto(
  dto: FeedbackDetailResponseDto,
): FeedbackDetailResponse {
  return { ...dto }
}

export function mapFeedbackListManagementResponseDto(
  dto: FeedbackListManagementResponseDto,
): FeedbackListManagementResponse {
  return {
    ...dto,
    items: dto.items.map(mapFeedbackDetailResponseDto),
  }
}

export function mapManagementFeedbackStatsDto(
  dto: ManagementFeedbackStatsDto,
): ManagementFeedbackStatsDto {
  return {
    ...dto,
    by_type: { ...dto.by_type },
  }
}

export function mapCollaborationTokenResponseDto(
  dto: CollaborationTokenResponseDto,
): CollaborationTokenResponseDto {
  return {
    ...dto,
    permissions: [...dto.permissions],
  }
}

export function mapCollaborationStatusResponseDto(
  dto: CollaborationStatusResponseDto,
): CollaborationStatusResponseDto {
  return {
    ...dto,
    active_collaborators: dto.active_collaborators.map((item) => ({ ...item })),
  }
}

export function mapCollaborationSessionStartResponseDto(
  dto: CollaborationSessionStartResponseDto,
): CollaborationSessionStartResponseDto {
  return { ...dto }
}

export function mapCollaborationActivityFeedResponseDto(
  dto: CollaborationActivityFeedResponseDto,
): CollaborationActivityFeedResponseDto {
  return {
    ...dto,
    activities: dto.activities.map((item) => ({ ...item })),
  }
}

export function mapCollaborationActiveSessionsResponseDto(
  dto: CollaborationActiveSessionsResponseDto,
): CollaborationActiveSessionsResponseDto {
  return {
    ...dto,
    sessions: dto.sessions.map((item) => ({ ...item })),
  }
}

export function mapCollaborationSnapshotDto(dto: CollaborationSnapshotDto): CollaborationSnapshotDto {
  return { ...dto }
}

export function mapCollaborationSnapshotListResponseDto(
  dto: CollaborationSnapshotListResponseDto,
): CollaborationSnapshotListResponseDto {
  return {
    ...dto,
    snapshots: dto.snapshots.map(mapCollaborationSnapshotDto),
  }
}

export function mapCollaborationRestoreSnapshotResponseDto(
  dto: CollaborationRestoreSnapshotResponseDto,
): CollaborationRestoreSnapshotResponseDto {
  return { ...dto }
}

export function mapCollaborationAutoSnapshotResponseDto(
  dto: CollaborationAutoSnapshotResponseDto,
): CollaborationAutoSnapshotResponseDto {
  return { ...dto }
}

export function mapSearchResponseDto(dto: SearchResponseDto): SearchResponseDto {
  return {
    ...dto,
    items: dto.items.map((item) => ({ ...item })),
    suggestions: [...dto.suggestions],
  }
}

export function mapSearchAutocompleteResponseDto(
  dto: SearchAutocompleteResponseDto,
): SearchAutocompleteResponseDto {
  return {
    suggestions: [...dto.suggestions],
  }
}

export function mapSearchFacetsResponseDto(
  dto: SearchFacetsResponseDto,
): SearchFacetsResponseDto {
  return {
    categories: dto.categories.map((item) => ({ ...item })),
    statuses: dto.statuses.map((item) => ({ ...item })),
  }
}

export function mapSavedSearchDto(dto: SavedSearchDto): SavedSearchDto {
  return { ...dto }
}

export function mapSavedSearchesDto(dtos: SavedSearchDto[]): SavedSearchDto[] {
  return dtos.map(mapSavedSearchDto)
}

export function toSavedSearchCreateDto(payload: SavedSearchCreateDto): SavedSearchCreateDto {
  return { ...payload }
}

export function mapBookmarkDto(dto: BookmarkDto): BookmarkDto {
  return { ...dto }
}

export function mapBookmarksDto(dtos: BookmarkDto[]): BookmarkDto[] {
  return dtos.map(mapBookmarkDto)
}

export function mapBookmarkStatusDto(dto: BookmarkStatusDto): BookmarkStatusDto {
  return { ...dto }
}

export function mapFeedbackSubmissionDto(dto: FeedbackSubmissionDto): FeedbackSubmissionDto {
  return { ...dto }
}

export function mapFeedbackStatsDto(dto: FeedbackStatsDto): FeedbackStatsDto {
  return { ...dto }
}

export function mapMyFeedbackDto(dto: MyFeedbackDto): MyFeedbackDto {
  return { ...dto }
}

export function mapReadingProgressDto(dto: ReadingProgressDto): ReadingProgressDto {
  return { ...dto }
}

export function mapReadingProgressListDto(dtos: ReadingProgressDto[]): ReadingProgressDto[] {
  return dtos.map(mapReadingProgressDto)
}

export function mapDocumentProgressDto(dto: DocumentProgressDto): DocumentProgressDto {
  return { ...dto }
}

export function mapEngagementStatsDto(dto: EngagementStatsDto): EngagementStatsDto {
  return { ...dto }
}
