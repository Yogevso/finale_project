"""
Portal API - Customer authenticated endpoints
"""

from fastapi import APIRouter

from .documents import router as documents_router
from .feedback import router as feedback_router
from .nps import router as nps_router
from .support import router as support_router

router = APIRouter()
router.include_router(documents_router)
router.include_router(feedback_router)
router.include_router(nps_router)
router.include_router(support_router)

__all__ = ["router"]
