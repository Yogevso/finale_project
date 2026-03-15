"""AI assistant tool registry — imports and registers all tools."""

from app.assistant.tools.registry import ToolRegistry, registry

from app.assistant.tools.document_tools import (
    CreateDocumentTool,
    DeleteDocumentTool,
    EditDocumentTool,
    GetDocumentTool,
    GetDocumentsByStatusTool,
    GetRecentDocumentsTool,
    SearchDocumentsTool,
)
from app.assistant.tools.user_tools import (
    ChangeUserRoleTool,
    CreateUserTool,
    DeactivateUserTool,
    GetUserTool,
    ListUsersTool,
)
from app.assistant.tools.settings_tools import (
    CreateAnnouncementTool,
    CreateTopicTool,
    GetSiteSettingsTool,
    ListAnnouncementsTool,
    ListTopicsTool,
    UpdateSiteSettingTool,
)
from app.assistant.tools.tenant_tools import (
    GetTenantTool,
    ListTenantsTool,
    UpdateTenantTool,
)
from app.assistant.tools.info_tools import (
    GetDocumentContentTool,
    GetHelpTool,
    GetMyPermissionsTool,
    GetMyProfileTool,
    SearchPublicDocumentsTool,
)
from app.assistant.tools.support_tools import (
    CreateSupportTicketTool,
    GetTicketDetailsTool,
    ListMyTicketsTool,
)
from app.assistant.tools.feedback_tools import (
    GetMyFeedbackTool,
    SubmitFeedbackTool,
)
from app.assistant.tools.rag_tools import (
    AskAboutDocumentTool,
    SemanticSearchTool,
    SummarizeDocumentTool,
)
from app.assistant.tools.file_tools import (
    AnalyzeUploadedFileTool,
    CompareFilesTool,
)
from app.assistant.tools.version_tools import (
    CompareVersionsTool,
    GetDocumentHistoryTool,
    GetDocumentWorkflowTool,
    PublishDocumentTool,
)
from app.assistant.tools.attachment_tools import (
    GetAttachmentInfoTool,
    ListAttachmentsTool,
)
from app.assistant.tools.analytics_tools import (
    GetContentAnalyticsTool,
    GetEngagementAnalyticsTool,
    GetPlatformAnalyticsTool,
)
from app.assistant.tools.audit_tools import (
    GetUserActivityTool,
    SearchAuditLogsTool,
)
from app.assistant.tools.notification_tools import (
    GetMyNotificationsTool,
    MarkNotificationsReadTool,
)
from app.assistant.tools.comment_tools import (
    AddCommentTool,
    ListDocumentCommentsTool,
    ResolveCommentTool,
)
from app.assistant.tools.review_tools import (
    ListPendingReviewsTool,
    SubmitReviewTool,
)
from app.assistant.tools.invitation_tools import (
    CreateInvitationTool,
    ListInvitationsTool,
)
from app.assistant.tools.collaboration_tools import (
    GetActiveCollaboratorsTool,
    GetCollaborationHistoryTool,
)
from app.assistant.tools.engagement_tools import (
    BookmarkDocumentTool,
    GetMyWatchedDocumentsTool,
    GetReadingProgressTool,
    ListMyBookmarksTool,
    RemoveBookmarkTool,
    UnwatchDocumentTool,
    UpdateReadingProgressTool,
    WatchDocumentTool,
)
from app.assistant.tools.chat_tools import (
    GetChatMessagesTool,
    GetChatParticipantsTool,
    GetUnreadChatsTool,
    ListMyChatsTool,
    MarkChatReadTool,
    SearchChatMessagesTool,
    SendChatMessageTool,
)
from app.assistant.tools.admin_tools import (
    CreateMaintenanceWindowTool,
    GetPlatformOverviewTool,
    GetTenantQuotaTool,
    GetTenantSummaryTool,
    ListAdminActionsTool,
    ListFeatureFlagsTool,
    ListImpersonationSessionsTool,
    ListMaintenanceWindowsTool,
    ReviewAdminActionTool,
    ToggleFeatureFlagTool,
    UpdateTenantQuotaTool,
)
from app.assistant.tools.version_tools_ext import (
    CancelScheduledPublishTool,
    GetDocumentVersionStatsTool,
    GetVersionDetailsTool,
    ListScheduledPublishesTool,
    ListUnpublishedVersionsTool,
)
from app.assistant.tools.attachment_tools_ext import (
    GetAttachmentStatsTool,
    GetLargestAttachmentsTool,
    SearchAttachmentsTool,
)
from app.assistant.tools.security_tools import (
    CancelInvitationTool,
    GetInvitationStatusTool,
    GetMySecurityEventsTool,
    GetMySessionsTool,
    GetSecurityEventsAdminTool,
    RevokeSessionTool,
)

# -- Register all tools with the singleton registry --

# Document tools
registry.register(SearchDocumentsTool())
registry.register(GetDocumentTool())
registry.register(CreateDocumentTool())
registry.register(EditDocumentTool())
registry.register(DeleteDocumentTool())
registry.register(GetDocumentsByStatusTool())
registry.register(GetRecentDocumentsTool())

# User tools
registry.register(ListUsersTool())
registry.register(GetUserTool())
registry.register(CreateUserTool())
registry.register(DeactivateUserTool())
registry.register(ChangeUserRoleTool())

# Settings / announcements / topics
registry.register(GetSiteSettingsTool())
registry.register(UpdateSiteSettingTool())
registry.register(CreateAnnouncementTool())
registry.register(ListAnnouncementsTool())
registry.register(ListTopicsTool())
registry.register(CreateTopicTool())

# Tenant tools
registry.register(ListTenantsTool())
registry.register(GetTenantTool())
registry.register(UpdateTenantTool())

# Info tools
registry.register(GetMyProfileTool())
registry.register(GetMyPermissionsTool())
registry.register(GetHelpTool())
registry.register(SearchPublicDocumentsTool())
registry.register(GetDocumentContentTool())

# Support tools
registry.register(CreateSupportTicketTool())
registry.register(ListMyTicketsTool())
registry.register(GetTicketDetailsTool())

# Feedback tools
registry.register(SubmitFeedbackTool())
registry.register(GetMyFeedbackTool())

# RAG tools
registry.register(SemanticSearchTool())
registry.register(SummarizeDocumentTool())
registry.register(AskAboutDocumentTool())

# File tools
registry.register(AnalyzeUploadedFileTool())
registry.register(CompareFilesTool())

# Version tools
registry.register(CompareVersionsTool())
registry.register(GetDocumentHistoryTool())
registry.register(PublishDocumentTool())
registry.register(GetDocumentWorkflowTool())

# Attachment tools
registry.register(ListAttachmentsTool())
registry.register(GetAttachmentInfoTool())

# Analytics tools
registry.register(GetPlatformAnalyticsTool())
registry.register(GetEngagementAnalyticsTool())
registry.register(GetContentAnalyticsTool())

# Audit tools
registry.register(SearchAuditLogsTool())
registry.register(GetUserActivityTool())

# Notification tools
registry.register(GetMyNotificationsTool())
registry.register(MarkNotificationsReadTool())

# Comment tools
registry.register(ListDocumentCommentsTool())
registry.register(AddCommentTool())
registry.register(ResolveCommentTool())

# Review tools
registry.register(SubmitReviewTool())
registry.register(ListPendingReviewsTool())

# Invitation tools
registry.register(CreateInvitationTool())
registry.register(ListInvitationsTool())

# Collaboration tools
registry.register(GetActiveCollaboratorsTool())
registry.register(GetCollaborationHistoryTool())

# Engagement tools (Phase 21)
registry.register(BookmarkDocumentTool())
registry.register(RemoveBookmarkTool())
registry.register(ListMyBookmarksTool())
registry.register(WatchDocumentTool())
registry.register(UnwatchDocumentTool())
registry.register(GetMyWatchedDocumentsTool())
registry.register(GetReadingProgressTool())
registry.register(UpdateReadingProgressTool())

# Chat tools (Phase 22)
registry.register(ListMyChatsTool())
registry.register(GetChatMessagesTool())
registry.register(SendChatMessageTool())
registry.register(SearchChatMessagesTool())
registry.register(GetChatParticipantsTool())
registry.register(GetUnreadChatsTool())
registry.register(MarkChatReadTool())

# Admin tools (Phase 23)
registry.register(ListFeatureFlagsTool())
registry.register(ToggleFeatureFlagTool())
registry.register(ListMaintenanceWindowsTool())
registry.register(CreateMaintenanceWindowTool())
registry.register(GetTenantQuotaTool())
registry.register(UpdateTenantQuotaTool())
registry.register(ListImpersonationSessionsTool())
registry.register(ListAdminActionsTool())
registry.register(ReviewAdminActionTool())
registry.register(GetPlatformOverviewTool())
registry.register(GetTenantSummaryTool())

# Extended version tools (Phase 24)
registry.register(ListScheduledPublishesTool())
registry.register(GetVersionDetailsTool())
registry.register(GetDocumentVersionStatsTool())
registry.register(CancelScheduledPublishTool())
registry.register(ListUnpublishedVersionsTool())

# Extended attachment tools (Phase 24)
registry.register(SearchAttachmentsTool())
registry.register(GetAttachmentStatsTool())
registry.register(GetLargestAttachmentsTool())

# Security tools (Phase 25)
registry.register(GetMySessionsTool())
registry.register(RevokeSessionTool())
registry.register(GetMySecurityEventsTool())
registry.register(GetSecurityEventsAdminTool())
registry.register(GetInvitationStatusTool())
registry.register(CancelInvitationTool())

__all__ = ["registry", "ToolRegistry"]
