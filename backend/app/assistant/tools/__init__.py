"""AI assistant tool registry — imports and registers all tools."""

from app.assistant.tools.registry import ToolRegistry, registry

from app.assistant.tools.document_tools import (
    CreateDocumentTool,
    DeleteDocumentTool,
    EditDocumentTool,
    GetDocumentTool,
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

# -- Register all tools with the singleton registry --

# Document tools
registry.register(SearchDocumentsTool())
registry.register(GetDocumentTool())
registry.register(CreateDocumentTool())
registry.register(EditDocumentTool())
registry.register(DeleteDocumentTool())

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

__all__ = ["registry", "ToolRegistry"]
