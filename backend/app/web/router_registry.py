"""Central router registry for FastAPI app composition."""

from __future__ import annotations

from fastapi import FastAPI

from app.api import health
from app.api.management import (
    analytics,
    attachments,
    auth,
    collaboration,
    comments,
    companies,
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


def register_routers(app: FastAPI) -> None:
    """Register all API routers in one place."""
    app.include_router(health.router, tags=["Health"])

    # Public API (no authentication required)
    app.include_router(public_router, prefix=settings.API_PREFIX, tags=["Public"])
    app.include_router(public_platforms_router, prefix="/api", tags=["Public"])

    app.include_router(auth.router, prefix=settings.API_PREFIX, tags=["Authentication"])
    app.include_router(documents.router, prefix=settings.API_PREFIX, tags=["Documents"])
    app.include_router(versions.router, prefix=settings.API_PREFIX, tags=["Versions"])
    app.include_router(attachments.router, prefix=settings.API_PREFIX, tags=["Attachments"])
    app.include_router(comments.router, prefix=settings.API_PREFIX, tags=["Comments"])
    app.include_router(search.router, prefix=settings.API_PREFIX, tags=["Search"])
    app.include_router(engagement.router, prefix=settings.API_PREFIX, tags=["Engagement"])
    app.include_router(tenants.router, prefix=settings.API_PREFIX, tags=["Tenants"])
    app.include_router(users.router, prefix=settings.API_PREFIX, tags=["Users"])
    app.include_router(notifications.router, prefix=settings.API_PREFIX, tags=["Notifications"])
    app.include_router(companies.router, prefix=settings.API_PREFIX, tags=["Companies"])
    app.include_router(reviews.router, prefix=settings.API_PREFIX, tags=["Reviews"])
    app.include_router(feedback.router, prefix=settings.API_PREFIX, tags=["Feedback"])
    app.include_router(invitations.router, prefix=settings.API_PREFIX, tags=["Invitations"])
    app.include_router(analytics.router, prefix=settings.API_PREFIX, tags=["Analytics"])
    app.include_router(collaboration.router, prefix=settings.API_PREFIX, tags=["Collaboration"])
    app.include_router(system_settings.router, prefix=settings.API_PREFIX, tags=["System Settings"])
    app.include_router(rbac.router, prefix=settings.API_PREFIX, tags=["RBAC"])

    # Viewer Portal (public, no auth required)
    app.include_router(viewer_documents.router, prefix=settings.API_PREFIX, tags=["Viewer"])

    # Customer Portal (authenticated customers only)
    app.include_router(portal_router, prefix=settings.API_PREFIX, tags=["Customer Portal"])

