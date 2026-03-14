"""Public API Router - No Authentication Required"""

from fastapi import APIRouter

from app.api.public.documents import router as documents_router
from app.api.public.platforms import router as platforms_router
from app.api.public.announcements import router as announcements_router
from app.api.public.sitemap import router as sitemap_router
from app.api.public.topics import router as topics_router

router = APIRouter()

# Include public documents endpoints
router.include_router(documents_router)
router.include_router(platforms_router)
router.include_router(topics_router)
router.include_router(sitemap_router)
router.include_router(announcements_router)
