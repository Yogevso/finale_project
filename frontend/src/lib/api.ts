import { AnalyticsApiMixin } from './api/analyticsApi'
import { AttachmentsApiMixin } from './api/attachmentsApi'
import { AuthApiMixin } from './api/authApi'
import { CollaborationApiMixin } from './api/collaborationApi'
import { type ComposedApiClient, composeApiClient } from './api/composition'
import { CompaniesApiMixin } from './api/companiesApi'
import { DocumentsApiMixin } from './api/documentsApi'
import { InvitationsApiMixin } from './api/invitationsApi'
import { NotificationsApiMixin } from './api/notificationsApi'
import { ReviewsApiMixin } from './api/reviewsApi'
import { SearchEngagementApiMixin } from './api/searchEngagementApi'
import { ApiHttpClient } from './api/httpClient'
import { UsersApiMixin } from './api/usersApi'

// Keep a declarative API-module list so composition order is explicit and easy to evolve.
const apiMixins = [
  AuthApiMixin,
  UsersApiMixin,
  DocumentsApiMixin,
  AttachmentsApiMixin,
  SearchEngagementApiMixin,
  NotificationsApiMixin,
  CompaniesApiMixin,
  ReviewsApiMixin,
  InvitationsApiMixin,
  AnalyticsApiMixin,
  CollaborationApiMixin,
] as const

type AppApiClient = ComposedApiClient<typeof apiMixins>

const ApiClient = composeApiClient(ApiHttpClient, apiMixins)

export const api: AppApiClient = new ApiClient()
