"""FastAPI Application Entry Point"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.middleware import LoggingMiddleware, RateLimitMiddleware

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Document Portal V2 - Greenfield rebuild with SQLite",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)

# Add middleware (order matters - first added is outermost)
# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW,
)

# Request logging
app.add_middleware(LoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.APP_ENV}")
    init_db()
    logger.info("Database initialized")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Document Portal V2 API",
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_PREFIX}/docs",
    }


# Import and include routers
from app.api import health  # noqa: E402
from app.api.management import (  # noqa: E402
    attachments,
    auth,
    comments,
    companies,
    documents,
    engagement,
    feedback,
    invitations,
    notifications,
    reviews,
    search,
    tenants,
    users,
    versions,
)
from app.api.portal import router as portal_router  # noqa: E402
from app.api.public import router as public_router  # noqa: E402
from app.api.viewer import documents as viewer_documents  # noqa: E402

# Health check routes (no prefix for load balancer compatibility)
app.include_router(health.router, tags=["Health"])

# Public API (no authentication required)
app.include_router(public_router, prefix=settings.API_PREFIX, tags=["Public"])

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

# Viewer Portal (public, no auth required)
app.include_router(viewer_documents.router, prefix=settings.API_PREFIX, tags=["Viewer"])

# Customer Portal (authenticated customers only)
app.include_router(portal_router, prefix=settings.API_PREFIX, tags=["Customer Portal"])
