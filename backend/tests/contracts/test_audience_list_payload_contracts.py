"""Consumer-driven payload contracts for audience list endpoints."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.models import Document, DocumentStatus, DocumentVisibility, Version


class FrontendDocumentDto(BaseModel):
    """Shape expected by frontend `Document` type."""

    model_config = ConfigDict(extra="allow")

    id: int
    title: str
    document_number: str
    description: str | None
    status: Literal["draft", "pending_review", "approved", "active", "archived"]
    visibility: Literal["public", "internal", "company"]
    category: str | None
    tags: str | None
    created_by: int
    created_at: str
    updated_at: str
    version_label: str | None = None
    release_branch: str | None = None
    parent_id: int | None = None
    row_version: int | None = None
    etag: str | None = None
    created_by_user: dict[str, Any] | None = None
    versions_count: int | None = None
    attachments_count: int | None = None
    comments_count: int | None = None
    assigned_companies: list[dict[str, Any]] | None = None


class FrontendDocumentListResponseDto(BaseModel):
    """Shape expected by frontend `DocumentListResponse` type."""

    model_config = ConfigDict(extra="allow")

    items: list[FrontendDocumentDto]
    total: int
    page: int
    page_size: int
    total_pages: int


class FrontendPortalDocumentDto(BaseModel):
    """Shape expected by frontend `PortalDocument` type."""

    model_config = ConfigDict(extra="allow")

    id: int
    title: str
    visibility: str
    version: int
    updated_at: str
    has_attachments: bool
    document_number: str | None = None
    description: str | None = None
    category: str | None = None
    topic: str | None = None
    platform: str | None = None
    release_branch: str | None = None
    tags: str | None = None
    thumbnail_url: str | None = None
    created_at: str | None = None
    published_at: str | None = None


class FrontendPortalDocumentListResponseDto(BaseModel):
    """Shape expected by frontend `PortalDocumentListResponse` type."""

    model_config = ConfigDict(extra="allow")

    items: list[FrontendPortalDocumentDto]
    total: int
    page: int
    per_page: int
    total_pages: int


class FrontendPublicDocumentSummaryDto(BaseModel):
    """Shape expected by frontend `PublicDocumentSummary` type."""

    model_config = ConfigDict(extra="allow")

    id: int
    document_number: str
    title: str
    visibility: str
    created_at: str
    description: str | None = None
    category: str | None = None
    topic: str | None = None
    platform: str | None = None
    release_branch: str | None = None
    tags: str | None = None
    thumbnail_url: str | None = None
    updated_at: str | None = None
    published_at: str | None = None
    version_number: int | None = None


class FrontendPublicDocumentListResponseDto(BaseModel):
    """Shape expected by frontend `PublicDocumentListResponse` type."""

    model_config = ConfigDict(extra="allow")

    items: list[FrontendPublicDocumentSummaryDto]
    total: int
    page: int
    page_size: int
    total_pages: int


def test_management_documents_list_matches_frontend_dto_shape(
    client,
    db,
    auth_headers,
    test_user,
):
    marker = f"mgmt-contract-{uuid.uuid4().hex[:8]}"
    doc = Document(
        title=f"Management {marker}",
        document_number=f"DOC-MGMT-{uuid.uuid4().hex[:8].upper()}",
        description=marker,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
        created_by=test_user.id,
        tenant_id=test_user.tenant_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    response = client.get(
        f"/api/v1/documents?search={marker}&page=1&page_size=100",
        headers=auth_headers,
    )
    assert response.status_code == 200

    payload = FrontendDocumentListResponseDto.model_validate(response.json())
    matched = [item for item in payload.items if item.id == doc.id]
    assert matched, "Seeded management document missing from contract response"
    assert matched[0].status == "active"
    assert matched[0].visibility == "internal"


def test_portal_documents_list_matches_frontend_dto_shape(
    client,
    db,
    customer_headers,
    test_admin,
):
    marker = f"portal-contract-{uuid.uuid4().hex[:8]}"
    doc = Document(
        title=f"Portal {marker}",
        document_number=f"DOC-PORTAL-{uuid.uuid4().hex[:8].upper()}",
        description=marker,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add(doc)
    db.flush()

    published_version = Version(
        document_id=doc.id,
        version_number=1,
        content="Published content",
        changes_summary="Initial release",
        created_by=test_admin.id,
        is_published=True,
    )
    db.add(published_version)
    db.commit()
    db.refresh(doc)

    response = client.get(
        f"/api/v1/portal/documents?search={marker}&page=1&per_page=100",
        headers=customer_headers,
    )
    assert response.status_code == 200

    payload = FrontendPortalDocumentListResponseDto.model_validate(response.json())
    matched = [item for item in payload.items if item.id == doc.id]
    assert matched, "Seeded portal document missing from contract response"
    assert matched[0].visibility == "public"


def test_public_documents_list_matches_frontend_dto_shape(
    client,
    db,
    test_admin,
):
    marker = f"public-contract-{uuid.uuid4().hex[:8]}"
    doc = Document(
        title=f"Public {marker}",
        document_number=f"DOC-PUB-{uuid.uuid4().hex[:8].upper()}",
        description=marker,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    response = client.get(f"/api/v1/public/documents?search={marker}&page=1&page_size=100")
    assert response.status_code == 200

    payload = FrontendPublicDocumentListResponseDto.model_validate(response.json())
    matched = [item for item in payload.items if item.id == doc.id]
    assert matched, "Seeded public document missing from contract response"
    assert matched[0].visibility == "public"
