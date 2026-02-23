"""Collaboration API routes."""

from fastapi import APIRouter

from .activity import router as activity_router
from .sessions import router as sessions_router
from .snapshots import router as snapshots_router
from .state import router as state_router

router = APIRouter()
router.include_router(state_router)
router.include_router(sessions_router)
router.include_router(activity_router)
router.include_router(snapshots_router)

__all__ = ["router"]
