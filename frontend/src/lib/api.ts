import { AdminOpsApiMixin } from './api/adminOpsApi'
import { AnalyticsApiMixin } from './api/analyticsApi'
import { AttachmentsApiMixin } from './api/attachmentsApi'
import { AuthApiMixin } from './api/authApi'
import { BffApiMixin } from './api/bffApi'
import { ChatApiMixin } from './api/chatApi'
import { CollaborationApiMixin } from './api/collaborationApi'
import { CompaniesApiMixin } from './api/companiesApi'
import { DocumentsApiMixin } from './api/documentsApi'
import { InvitationsApiMixin } from './api/invitationsApi'
import { NotificationsApiMixin } from './api/notificationsApi'
import { ReviewsApiMixin } from './api/reviewsApi'
import { SearchEngagementApiMixin } from './api/searchEngagementApi'
import { SupportApiMixin } from './api/supportApi'
import { ApiHttpClient } from './api/httpClient'
import { UsersApiMixin } from './api/usersApi'

type ApiModuleMembers<TClass extends { prototype: object }> = Omit<
  TClass['prototype'],
  keyof ApiHttpClient
>

const AuthApiModule = AuthApiMixin(ApiHttpClient)
const UsersApiModule = UsersApiMixin(ApiHttpClient)
const DocumentsApiModule = DocumentsApiMixin(ApiHttpClient)
const BffApiModule = BffApiMixin(ApiHttpClient)
const AttachmentsApiModule = AttachmentsApiMixin(ApiHttpClient)
const SearchEngagementApiModule = SearchEngagementApiMixin(ApiHttpClient)
const NotificationsApiModule = NotificationsApiMixin(ApiHttpClient)
const CompaniesApiModule = CompaniesApiMixin(ApiHttpClient)
const ReviewsApiModule = ReviewsApiMixin(ApiHttpClient)
const InvitationsApiModule = InvitationsApiMixin(ApiHttpClient)
const AnalyticsApiModule = AnalyticsApiMixin(ApiHttpClient)
const CollaborationApiModule = CollaborationApiMixin(ApiHttpClient)
const ChatApiModule = ChatApiMixin(ApiHttpClient)
const SupportApiModule = SupportApiMixin(ApiHttpClient)
const AdminOpsApiModule = AdminOpsApiMixin(ApiHttpClient)

export type AppApiClient = ApiHttpClient &
  ApiModuleMembers<typeof AuthApiModule> &
  ApiModuleMembers<typeof UsersApiModule> &
  ApiModuleMembers<typeof DocumentsApiModule> &
  ApiModuleMembers<typeof BffApiModule> &
  ApiModuleMembers<typeof AttachmentsApiModule> &
  ApiModuleMembers<typeof SearchEngagementApiModule> &
  ApiModuleMembers<typeof NotificationsApiModule> &
  ApiModuleMembers<typeof CompaniesApiModule> &
  ApiModuleMembers<typeof ReviewsApiModule> &
  ApiModuleMembers<typeof InvitationsApiModule> &
  ApiModuleMembers<typeof AnalyticsApiModule> &
  ApiModuleMembers<typeof CollaborationApiModule> &
  ApiModuleMembers<typeof ChatApiModule> &
  ApiModuleMembers<typeof SupportApiModule> &
  ApiModuleMembers<typeof AdminOpsApiModule>

const AuthApiClass = AuthApiMixin(ApiHttpClient)
const UsersApiClass = UsersApiMixin(AuthApiClass)
const DocumentsApiClass = DocumentsApiMixin(UsersApiClass)
const BffApiClass = BffApiMixin(DocumentsApiClass)
const AttachmentsApiClass = AttachmentsApiMixin(BffApiClass)
const SearchEngagementApiClass = SearchEngagementApiMixin(AttachmentsApiClass)
const NotificationsApiClass = NotificationsApiMixin(SearchEngagementApiClass)
const CompaniesApiClass = CompaniesApiMixin(NotificationsApiClass)
const ReviewsApiClass = ReviewsApiMixin(CompaniesApiClass)
const InvitationsApiClass = InvitationsApiMixin(ReviewsApiClass)
const AnalyticsApiClass = AnalyticsApiMixin(InvitationsApiClass)
const CollaborationApiClass = CollaborationApiMixin(AnalyticsApiClass)
const ChatApiClass = ChatApiMixin(CollaborationApiClass)
const SupportApiClass = SupportApiMixin(ChatApiClass)
const AppApiClientClass = AdminOpsApiMixin(SupportApiClass)

export const api: AppApiClient = new AppApiClientClass()
