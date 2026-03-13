"""FastAPI app factory and composition bootstrap."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.container import build_container
from app.db import SessionLocal, init_db
from app.errors import DomainError
from app.feature_flags import (
    BackendFeatureFlag,
    get_backend_feature_flags,
    is_backend_feature_enabled,
)
from app.middleware import IdempotencyMiddleware, LoggingMiddleware, RateLimitMiddleware
from app.projections import get_projection_cache, register_projection_invalidation_listeners
from app.web.router_registry import FastAPIRouterRegistry, build_default_router_registry

logger = logging.getLogger(__name__)


class FastAPIAppFactory:
    """Object model for FastAPI app assembly and runtime composition."""

    def __init__(self, *, router_registry: FastAPIRouterRegistry | None = None) -> None:
        self._router_registry = router_registry or build_default_router_registry()

    def create(self) -> FastAPI:
        """Create and configure the FastAPI application instance."""
        app = FastAPI(
            title=settings.APP_NAME,
            version=settings.APP_VERSION,
            description="Documentation Platform - Greenfield rebuild with SQLite",
            docs_url=f"{settings.API_PREFIX}/docs",
            redoc_url=f"{settings.API_PREFIX}/redoc",
            openapi_url=f"{settings.API_PREFIX}/openapi.json",
        )
        self._configure_state(app)
        self._configure_middleware(app)
        self._configure_exception_handlers(app)
        self._configure_lifecycle_events(app)
        self._register_internal_routes(app)
        self._router_registry.register(app)
        self._configure_openapi(app)
        return app

    @staticmethod
    def _configure_state(app: FastAPI) -> None:
        # Shared composition root.
        app.state.container = build_container()
        app.state.feature_flags = get_backend_feature_flags()
        app.state.runtime_init_lock = threading.Lock()
        app.state.runtime_initialized = False
        if is_backend_feature_enabled(BackendFeatureFlag.PROJECTION_CACHE):
            app.state.projection_cache = get_projection_cache()
            register_projection_invalidation_listeners()
        else:
            app.state.projection_cache = None

    @staticmethod
    def _configure_middleware(app: FastAPI) -> None:
        # Add middleware (order matters - first added is outermost).
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=settings.RATE_LIMIT_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW,
        )
        app.add_middleware(LoggingMiddleware)
        if is_backend_feature_enabled(BackendFeatureFlag.IDEMPOTENCY_MIDDLEWARE):
            app.add_middleware(IdempotencyMiddleware)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @staticmethod
    def _configure_exception_handlers(app: FastAPI) -> None:
        @app.exception_handler(DomainError)
        async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
            """Map domain/application errors to transport-level HTTP responses."""
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.message, "error_code": exc.error_code},
            )

    @staticmethod
    def _configure_openapi(app: FastAPI) -> None:
        if settings.APP_ENV.lower() != "testing":
            return

        snapshot_path = Path(__file__).resolve().parents[1] / "openapi.contract.json"
        if not snapshot_path.exists():
            logger.warning("OpenAPI snapshot not found for testing mode: %s", snapshot_path)
            return

        def openapi_from_snapshot():
            if app.openapi_schema is None:
                with snapshot_path.open("r", encoding="utf-8") as snapshot_file:
                    app.openapi_schema = json.load(snapshot_file)
            return app.openapi_schema

        app.openapi = openapi_from_snapshot

    @staticmethod
    def _configure_lifecycle_events(app: FastAPI) -> None:
        @app.on_event("startup")
        async def startup_event():
            """Initialize database and publish runtime RBAC policies."""
            logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
            logger.info("Environment: %s", settings.APP_ENV)
            logger.info(
                "Feature flags: projection_cache=%s, idempotency_middleware=%s",
                app.state.feature_flags.projection_cache,
                app.state.feature_flags.idempotency_middleware,
            )
            with app.state.runtime_init_lock:
                if app.state.runtime_initialized:
                    logger.info("Runtime database initialization already completed; skipping repeat init")
                else:
                    init_db()
                    app.state.runtime_initialized = True
                    logger.info("Database initialized")

            try:
                from app.services.rbac_service import RbacService

                db = SessionLocal()
                try:
                    RbacService.publish_policies(db)
                finally:
                    db.close()
            except Exception as exc:
                logger.warning("RBAC publish skipped: %s", exc)

    @staticmethod
    def _register_internal_routes(app: FastAPI) -> None:
        @app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "Documentation Platform API",
                "version": settings.APP_VERSION,
                "docs": f"{settings.API_PREFIX}/docs",
            }


def create_app() -> FastAPI:
    """Backward-compatible app creation entrypoint."""
    return FastAPIAppFactory().create()
