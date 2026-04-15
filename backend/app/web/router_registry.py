"""Central router registry for FastAPI app composition."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, FastAPI

from app.api import health
from app.api.bff import documents as bff_documents
from app.api.management import (
    admin_ops,
    analytics,
    announcements,
    assistant,
    attachments,
    audience_governance,
    auth,
    broken_links,
    canned_responses,
    changelog,
    chat,
    collaboration,
    comments,
    companies,
    company_maintenance,
    documents,
    engagement,
    experimentation,
    feedback,
    gdpr,
    invitations,
    notifications,
    permission_debugger,
    rbac,
    reviews,
    search,
    snapshot_diff,
    support,
    system_settings,
    tenants,
    users,
    versions,
)
from app.api.portal import router as portal_router
from app.api.public import router as public_router
from app.api.public.platforms import router as public_platforms_router
from app.api.viewer import documents as viewer_documents
from app.config import settings
from app.ws import chat_ws, support_ws


@dataclass(frozen=True, slots=True)
class RouterRegistration:
    """Declarative registration entry for a FastAPI router."""

    router: APIRouter
    prefix: str = ""
    tags: tuple[str, ...] = ()


class FastAPIRouterRegistry:
    """Object model for router registration and composition order."""

    def __init__(self, *, api_prefix: str) -> None:
        self._api_prefix = api_prefix

    def registrations(self) -> tuple[RouterRegistration, ...]:
        """Return ordered router registration entries."""
        return (
            RouterRegistration(health.router, tags=("Health",)),
            # Public API (no authentication required)
            RouterRegistration(public_router, prefix=self._api_prefix, tags=("Public",)),
            RouterRegistration(public_platforms_router, prefix="/api", tags=("Public",)),
            RouterRegistration(auth.router, prefix=self._api_prefix, tags=("Authentication",)),
            RouterRegistration(documents.router, prefix=self._api_prefix, tags=("Documents",)),
            RouterRegistration(versions.router, prefix=self._api_prefix, tags=("Versions",)),
            RouterRegistration(attachments.router, prefix=self._api_prefix, tags=("Attachments",)),
            RouterRegistration(comments.router, prefix=self._api_prefix, tags=("Comments",)),
            RouterRegistration(search.router, prefix=self._api_prefix, tags=("Search",)),
            RouterRegistration(engagement.router, prefix=self._api_prefix, tags=("Engagement",)),
            RouterRegistration(tenants.router, prefix=self._api_prefix, tags=("Tenants",)),
            RouterRegistration(users.router, prefix=self._api_prefix, tags=("Users",)),
            RouterRegistration(
                notifications.router, prefix=self._api_prefix, tags=("Notifications",)
            ),
            RouterRegistration(companies.router, prefix=self._api_prefix, tags=("Companies",)),
            RouterRegistration(
                company_maintenance.router, prefix=self._api_prefix, tags=("Company Maintenance",)
            ),
            RouterRegistration(reviews.router, prefix=self._api_prefix, tags=("Reviews",)),
            RouterRegistration(feedback.router, prefix=self._api_prefix, tags=("Feedback",)),
            RouterRegistration(invitations.router, prefix=self._api_prefix, tags=("Invitations",)),
            RouterRegistration(analytics.router, prefix=self._api_prefix, tags=("Analytics",)),
            RouterRegistration(
                broken_links.router, prefix=self._api_prefix, tags=("Broken Links",)
            ),
            RouterRegistration(changelog.router, prefix=self._api_prefix, tags=("Changelog",)),
            RouterRegistration(
                announcements.router, prefix=self._api_prefix, tags=("Announcements",)
            ),
            RouterRegistration(
                audience_governance.router,
                prefix=self._api_prefix,
                tags=("Audience Governance",),
            ),
            RouterRegistration(
                collaboration.router, prefix=self._api_prefix, tags=("Collaboration",)
            ),
            RouterRegistration(chat.router, prefix=self._api_prefix, tags=("Chat",)),
            RouterRegistration(support.router, prefix=self._api_prefix, tags=("Support",)),
            RouterRegistration(
                canned_responses.router, prefix=self._api_prefix, tags=("Canned Responses",)
            ),
            # WebSocket endpoints (no prefix — paths already include /ws/)
            RouterRegistration(chat_ws.router, tags=("WebSocket",)),
            RouterRegistration(support_ws.router, tags=("WebSocket",)),
            RouterRegistration(
                system_settings.router, prefix=self._api_prefix, tags=("System Settings",)
            ),
            RouterRegistration(rbac.router, prefix=self._api_prefix, tags=("RBAC",)),
            RouterRegistration(
                admin_ops.router, prefix=self._api_prefix, tags=("Admin Operations",)
            ),
            RouterRegistration(
                permission_debugger.router, prefix=self._api_prefix, tags=("Permission Debugger",)
            ),
            RouterRegistration(
                snapshot_diff.router, prefix=self._api_prefix, tags=("Snapshot Diff",)
            ),
            RouterRegistration(gdpr.router, prefix=self._api_prefix, tags=("GDPR & Compliance",)),
            RouterRegistration(
                experimentation.router, prefix=self._api_prefix, tags=("Experimentation",)
            ),
            RouterRegistration(assistant.router, prefix=self._api_prefix, tags=("Assistant",)),
            RouterRegistration(bff_documents.router, prefix=self._api_prefix, tags=("BFF",)),
            # Viewer Portal (public, no auth required)
            RouterRegistration(viewer_documents.router, prefix=self._api_prefix, tags=("Viewer",)),
            # Customer Portal (authenticated customers only)
            RouterRegistration(portal_router, prefix=self._api_prefix, tags=("Customer Portal",)),
        )

    def register(self, app: FastAPI) -> None:
        """Register routers on a FastAPI app in deterministic order."""
        for registration in self.registrations():
            include_kwargs: dict[str, object] = {}
            if registration.prefix:
                include_kwargs["prefix"] = registration.prefix
            if registration.tags:
                include_kwargs["tags"] = list(registration.tags)
            app.include_router(registration.router, **include_kwargs)


def build_default_router_registry() -> FastAPIRouterRegistry:
    """Construct the default router registry for runtime composition."""
    return FastAPIRouterRegistry(api_prefix=settings.API_PREFIX)


def register_routers(app: FastAPI) -> None:
    """Backward-compatible router registration entrypoint."""
    build_default_router_registry().register(app)
