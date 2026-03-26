"""Platform and topic normalization helpers for documents."""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import NotFoundError, ValidationError
from app.models import Platform, Topic
from app.utils.topic_normalization import build_topic_lookup, normalize_topic_to_slug


class DocumentMetadataService:
    """Resolve document platform and topic metadata."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _slugify_platform(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
        slug = slug.strip("-")
        return slug or "platform"

    @staticmethod
    def _normalize_platform_name(name: Optional[str]) -> str:
        if not name or not name.strip():
            return "Unspecified"
        return name.strip()

    @staticmethod
    def require_platform_selection(
        *,
        platform_name: Optional[str] = None,
        platform_id: Optional[int] = None,
    ) -> None:
        if platform_id is not None:
            return
        if platform_name is not None and platform_name.strip():
            return
        raise ValidationError("Platform is required")

    def normalize_topic(self, raw_topic: Optional[str]) -> Optional[str]:
        normalized = normalize_topic_to_slug(raw_topic)
        if normalized is None:
            return None

        topics = self.db.query(Topic).all()
        if not topics:
            return normalized

        topic_lookup = build_topic_lookup(topics)
        return normalize_topic_to_slug(raw_topic, topic_lookup) or normalized

    def get_or_create_platform(
        self,
        *,
        platform_name: Optional[str] = None,
        platform_id: Optional[int] = None,
    ) -> Platform:
        if platform_id is not None:
            platform = self.db.query(Platform).filter(Platform.id == platform_id).first()
            if not platform:
                raise NotFoundError(f"Platform {platform_id} not found")
            return platform

        normalized_name = self._normalize_platform_name(platform_name)
        platform = (
            self.db.query(Platform)
            .filter(func.lower(Platform.name) == normalized_name.lower())
            .first()
        )
        if platform:
            return platform

        base_slug = self._slugify_platform(normalized_name)
        slug = base_slug
        suffix = 2
        while self.db.query(Platform).filter(Platform.slug == slug).first():
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        platform = Platform(name=normalized_name, slug=slug)
        self.db.add(platform)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            existing = (
                self.db.query(Platform)
                .filter(func.lower(Platform.name) == normalized_name.lower())
                .first()
            )
            if existing:
                return existing
            raise
        return platform
