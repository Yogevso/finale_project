"""Document-domain factories for complex creation workflows."""

from __future__ import annotations

from datetime import date
from typing import Optional

from app.domain.value_objects import SemanticVersion
from app.models import (
    ActionType,
    AuditLog,
    Document,
    DocumentStatus,
    DocumentVisibility,
    Version,
    VersionBumpType,
)


class DocumentFactory:
    """Factory methods for document aggregate initialization paths."""

    @staticmethod
    def create_document(
        *,
        title: str,
        document_number: str,
        created_by: int,
        description: Optional[str] = None,
        version_label: Optional[str] = None,
        status: DocumentStatus = DocumentStatus.DRAFT,
        visibility: DocumentVisibility = DocumentVisibility.INTERNAL,
        category: Optional[str] = None,
        topic: Optional[str] = None,
        platform_name: Optional[str] = None,
        platform_id: Optional[int] = None,
        release_branch: Optional[str] = None,
        tags: Optional[str] = None,
        due_date: Optional[date] = None,
        tenant_id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> Document:
        return Document(
            title=title,
            document_number=document_number,
            description=description,
            version_label=version_label,
            status=status,
            visibility=visibility,
            category=category,
            topic=topic,
            platform=platform_name,
            platform_id=platform_id,
            release_branch=release_branch,
            tags=tags,
            due_date=due_date,
            created_by=created_by,
            tenant_id=tenant_id,
            parent_id=parent_id,
        )

    @staticmethod
    def create_initial_version(*, document_id: int, created_by: int) -> Version:
        return Version(
            document_id=document_id,
            version_number=1,
            semantic_version=str(SemanticVersion.initial()),
            bump_type=VersionBumpType.MAJOR,
            content="",
            changes_summary="Initial version",
            created_by=created_by,
        )

    @staticmethod
    def create_patch_version(
        *,
        document_id: int,
        latest_version: Optional[Version],
        changes_summary: str,
        created_by: int,
    ) -> Version:
        new_version_number = (latest_version.version_number + 1) if latest_version else 1
        latest_content = latest_version.content if latest_version and latest_version.content else ""
        previous_semantic = SemanticVersion.from_raw(
            latest_version.semantic_version if latest_version else None,
            latest_version.version_number if latest_version else 1,
        )
        next_semantic = str(previous_semantic.bump_patch())
        return Version(
            document_id=document_id,
            version_number=new_version_number,
            semantic_version=next_semantic,
            bump_type=VersionBumpType.PATCH,
            content=latest_content,
            changes_summary=changes_summary,
            created_by=created_by,
        )

    @staticmethod
    def create_creation_audit(*, user_id: int, document_id: int, title: str) -> AuditLog:
        return AuditLog(
            user_id=user_id,
            document_id=document_id,
            action=ActionType.CREATE,
            details=f"Created document: {title}",
        )
