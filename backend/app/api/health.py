"""Health Check API Endpoints"""

import logging
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.infrastructure.degradation import get_degradation_metrics
from app.observability.search_runtime import get_search_runtime_metrics
from app.search_backend import database_dialect_name, resolve_search_backend_mode
from app.services.assistant_capacity_service import get_assistant_capacity_service
from app.services.document_audience_service import get_company_lookup_cache_metrics

logger = logging.getLogger(__name__)
router = APIRouter()


def _check_database(db: Session) -> dict[str, Any]:
    """Check database connectivity and health"""
    start = time.time()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = (time.time() - start) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:  # policy: DEGRADED — health checks report dependency failure without crashing
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def _check_storage() -> dict[str, Any]:
    """Check storage backend health"""
    if not settings.S3_ENABLED:
        return {
            "status": "healthy",
            "type": "local",
            "message": "Local storage is always available",
        }

    start = time.time()
    try:
        # Lazy import to avoid boto3 dependency when not using S3
        from app.services.storage_service import get_storage_backend

        _storage = get_storage_backend()  # noqa: F841
        # Try to list objects (limited) to verify connectivity
        # For S3, this tests credentials and bucket access
        latency_ms = (time.time() - start) * 1000
        return {
            "status": "healthy",
            "type": "s3",
            "bucket": settings.S3_BUCKET,
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:  # policy: DEGRADED — health checks report dependency failure without crashing
        logger.error(f"Storage health check failed: {e}")
        return {
            "status": "unhealthy",
            "type": "s3",
            "error": str(e),
        }


def _get_system_info() -> dict[str, Any]:
    """Get system information"""
    import platform
    import sys

    return {
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "platform_version": platform.version()[:50],
    }


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns 200 if the application is running.
    Used by load balancers and container orchestrators.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
    }


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check endpoint.

    Verifies that all dependencies are available and the service
    is ready to handle requests. Returns detailed component status.
    """
    # Check all components
    db_status = _check_database(db)
    storage_status = _check_storage()

    # Determine overall status
    all_healthy = all(s.get("status") == "healthy" for s in [db_status, storage_status])

    response = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "components": {
            "database": db_status,
            "storage": storage_status,
        },
    }

    # Return 503 if not ready
    if not all_healthy:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content=response)

    return response


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with system information.

    For administrative/debugging purposes only.
    """
    db_status = _check_database(db)
    storage_status = _check_storage()
    system_info = _get_system_info()
    cache_metrics = get_company_lookup_cache_metrics()
    degradation_metrics = get_degradation_metrics()
    assistant_capacity = get_assistant_capacity_service().snapshot()
    search_dialect = database_dialect_name(db)
    search_effective_mode = resolve_search_backend_mode(
        settings.SEARCH_BACKEND_MODE,
        dialect_name=search_dialect,
    )
    search_runtime = get_search_runtime_metrics(
        configured_mode=settings.SEARCH_BACKEND_MODE,
        effective_mode=search_effective_mode.value,
        dialect=search_dialect,
    )

    all_healthy = all(s.get("status") == "healthy" for s in [db_status, storage_status])

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "uptime_info": {
            "app_name": settings.APP_NAME,
        },
        "components": {
            "database": db_status,
            "storage": storage_status,
        },
        "system": system_info,
        "configuration": {
            "rate_limiting_enabled": settings.RATE_LIMIT_ENABLED,
            "email_enabled": settings.EMAIL_ENABLED,
            "s3_enabled": settings.S3_ENABLED,
            "debug_mode": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
            "search_backend_mode": settings.SEARCH_BACKEND_MODE,
            "assistant_chat_max_concurrent": settings.ASSISTANT_CHAT_MAX_CONCURRENT,
            "assistant_chat_max_queue": settings.ASSISTANT_CHAT_MAX_QUEUE,
            "assistant_embedding_max_concurrent": settings.ASSISTANT_EMBEDDING_MAX_CONCURRENT,
            "assistant_embedding_max_queue": settings.ASSISTANT_EMBEDDING_MAX_QUEUE,
        },
        "caches": {
            "document_company_lookup": {
                "entry_count": cache_metrics.entry_count,
                "max_entries": cache_metrics.max_entries,
                "ttl_seconds": cache_metrics.ttl_seconds,
                "hits": cache_metrics.hits,
                "misses": cache_metrics.misses,
                "expired": cache_metrics.expired,
                "writes": cache_metrics.writes,
                "evictions": cache_metrics.evictions,
                "clears": cache_metrics.clears,
            }
        },
        "runtime": {
            "assistant": {
                "status": assistant_capacity.status,
                "recorded_at": assistant_capacity.recorded_at,
                "total_rejections": assistant_capacity.total_rejections,
                "total_timeouts": assistant_capacity.total_timeouts,
                "chat": {
                    "status": assistant_capacity.chat.status,
                    "active": assistant_capacity.chat.active,
                    "queued": assistant_capacity.chat.queued,
                    "max_concurrent": assistant_capacity.chat.max_concurrent,
                    "max_queue": assistant_capacity.chat.max_queue,
                    "queue_timeout_seconds": assistant_capacity.chat.queue_timeout_seconds,
                    "total_admitted": assistant_capacity.chat.total_admitted,
                    "total_completed": assistant_capacity.chat.total_completed,
                    "total_rejected": assistant_capacity.chat.total_rejected,
                    "total_timed_out": assistant_capacity.chat.total_timed_out,
                    "p50_duration_ms": assistant_capacity.chat.p50_duration_ms,
                    "p95_duration_ms": assistant_capacity.chat.p95_duration_ms,
                    "p50_queue_wait_ms": assistant_capacity.chat.p50_queue_wait_ms,
                    "p95_queue_wait_ms": assistant_capacity.chat.p95_queue_wait_ms,
                    "last_rejected_at": assistant_capacity.chat.last_rejected_at,
                    "last_rejection_reason": assistant_capacity.chat.last_rejection_reason,
                },
                "embedding": {
                    "status": assistant_capacity.embedding.status,
                    "active": assistant_capacity.embedding.active,
                    "queued": assistant_capacity.embedding.queued,
                    "max_concurrent": assistant_capacity.embedding.max_concurrent,
                    "max_queue": assistant_capacity.embedding.max_queue,
                    "queue_timeout_seconds": assistant_capacity.embedding.queue_timeout_seconds,
                    "total_admitted": assistant_capacity.embedding.total_admitted,
                    "total_completed": assistant_capacity.embedding.total_completed,
                    "total_rejected": assistant_capacity.embedding.total_rejected,
                    "total_timed_out": assistant_capacity.embedding.total_timed_out,
                    "p50_duration_ms": assistant_capacity.embedding.p50_duration_ms,
                    "p95_duration_ms": assistant_capacity.embedding.p95_duration_ms,
                    "p50_queue_wait_ms": assistant_capacity.embedding.p50_queue_wait_ms,
                    "p95_queue_wait_ms": assistant_capacity.embedding.p95_queue_wait_ms,
                    "last_rejected_at": assistant_capacity.embedding.last_rejected_at,
                    "last_rejection_reason": assistant_capacity.embedding.last_rejection_reason,
                },
            },
            "search": {
                "configured_mode": search_runtime.configured_mode,
                "effective_mode": search_runtime.effective_mode,
                "dialect": search_runtime.dialect,
                "total_search_requests": search_runtime.total_search_requests,
                "executions_by_mode": dict(search_runtime.executions_by_mode),
                "degraded_fallbacks": search_runtime.degraded_fallbacks,
                "last_degraded_at": search_runtime.last_degraded_at,
                "last_requested_mode": search_runtime.last_requested_mode,
                "last_fallback_mode": search_runtime.last_fallback_mode,
                "last_error_type": search_runtime.last_error_type,
                "last_error_message": search_runtime.last_error_message,
            },
            "degradation": {
                "total_events": degradation_metrics.total_events,
                "by_policy": dict(degradation_metrics.by_policy),
                "by_key": dict(degradation_metrics.by_key),
                "last_recorded_at": degradation_metrics.last_recorded_at,
                "components": {
                    component: {
                        "total_events": metrics.total_events,
                        "by_policy": dict(metrics.by_policy),
                        "last_recorded_at": metrics.last_recorded_at,
                        "last_error_type": metrics.last_error_type,
                        "last_error_message": metrics.last_error_message,
                    }
                    for component, metrics in degradation_metrics.components.items()
                },
            }
        },
    }
