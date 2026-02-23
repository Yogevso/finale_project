import { AnalyticsApiMixin } from './api/analyticsApi'
import { AttachmentsApiMixin } from './api/attachmentsApi'
import { AuthApiMixin } from './api/authApi'
import { CollaborationApiMixin } from './api/collaborationApi'
import { CompaniesApiMixin } from './api/companiesApi'
import { DocumentsApiMixin } from './api/documentsApi'
import { InvitationsApiMixin } from './api/invitationsApi'
import { NotificationsApiMixin } from './api/notificationsApi'
import { ReviewsApiMixin } from './api/reviewsApi'
import { SearchEngagementApiMixin } from './api/searchEngagementApi'
import { ApiHttpClient } from './api/httpClient'
import { UsersApiMixin } from './api/usersApi'

class ApiClient extends CollaborationApiMixin(
  AnalyticsApiMixin(
    InvitationsApiMixin(
      ReviewsApiMixin(
        CompaniesApiMixin(
          NotificationsApiMixin(
            SearchEngagementApiMixin(
              AttachmentsApiMixin(DocumentsApiMixin(UsersApiMixin(AuthApiMixin(ApiHttpClient)))),
            ),
          ),
        ),
      ),
    ),
  ),
) {}

export const api = new ApiClient()
