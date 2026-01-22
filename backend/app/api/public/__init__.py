"""Public API Router - No Authentication Required"""

from fastapi import APIRouter

from app.api.public.documents import router as documents_router

router = APIRouter()

# Include public documents endpoints
router.include_router(documents_router)
