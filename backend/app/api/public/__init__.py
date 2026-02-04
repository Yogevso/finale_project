"""Public API Router - No Authentication Required"""

from fastapi import APIRouter

from app.api.public.documents import router as documents_router
from app.api.public.topics import router as topics_router

router = APIRouter()

# Include public documents endpoints
router.include_router(documents_router)
router.include_router(topics_router)
