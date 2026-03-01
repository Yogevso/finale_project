"""Central router registry for FastAPI app composition."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, FastAPI

from app.api import health
from app.api.bff import documents as bff_documents
from app.api.management import (
    analytics,
    attachments,
    auth,
    collaboration,
    comments,
    companies,
    company_maintenance,
    documents,
    engagement,
    feedback,
    invitations,
    notifications,
    rbac,
    reviews,
    search,
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
            RouterRegistration(notifications.router, prefix=self._api_prefix, tags=("Notifications",)),
            RouterRegistration(companies.router, prefix=self._api_prefix, tags=("Companies",)),
            RouterRegistration(company_maintenance.router, prefix=self._api_prefix, tags=("Company Maintenance",)),
            RouterRegistration(reviews.router, prefix=self._api_prefix, tags=("Reviews",)),
            RouterRegistration(feedback.router, prefix=self._api_prefix, tags=("Feedback",)),
            RouterRegistration(invitations.router, prefix=self._api_prefix, tags=("Invitations",)),
            RouterRegistration(analytics.router, prefix=self._api_prefix, tags=("Analytics",)),
            RouterRegistration(collaboration.router, prefix=self._api_prefix, tags=("Collaboration",)),
            RouterRegistration(system_settings.router, prefix=self._api_prefix, tags=("System Settings",)),
            RouterRegistration(rbac.router, prefix=self._api_prefix, tags=("RBAC",)),
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
