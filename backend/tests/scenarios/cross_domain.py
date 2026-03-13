"""Scenario-level fixture packs for tenant/user/document/review/collaboration tests."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import (
    Attachment,
    Document,
    DocumentStatus,
    DocumentVisibility,
    ReviewRequest,
    ReviewStatus,
    Tenant,
    User,
    UserRole,
)
from tests.factories import create_attachment, create_document, create_tenant, create_user


@dataclass(frozen=True)
class DocumentDetailBundleScenario:
    tenant: Tenant
    user: User
    document: Document
    attachment: Attachment
    review: ReviewRequest


@dataclass(frozen=True)
class CrossTenantDocumentScenario:
    actor_tenant: Tenant
    target_tenant: Tenant
    actor: User
    document: Document


@dataclass(frozen=True)
class CollaborationAccessScenario:
    owner_tenant: Tenant
    outsider_tenant: Tenant
    owner: User
    outsider: User
    outsider_password: str
    document: Document


def create_document_detail_bundle_scenario(
    db: Session,
    *,
    user: User,
    tenant: Tenant,
    document_title: str = "BFF Detail Document",
    review_message: str = "Please review",
) -> DocumentDetailBundleScenario:
    """Create a composed document payload with attachment + company + review history."""
    user.tenant_id = tenant.id
    db.commit()
    db.refresh(user)

    document = create_document(
        db,
        title=document_title,
        document_number=f"DOC-BFF-{uuid4().hex[:6].upper()}",
        description="Bundled detail page payload",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=user.id,
        tenant_id=tenant.id,
    )
    document.assigned_companies.append(tenant)
    db.commit()
    db.refresh(document)

    attachment = create_attachment(
        db,
        document_id=document.id,
        uploaded_by=user.id,
        filename="spec.docx",
        file_size=128,
        size_bytes=128,
        storage_path="uploads/spec.docx",
        storage_key="uploads/spec.docx",
    )

    review = ReviewRequest(
        document_id=document.id,
        submitted_by=user.id,
        status=ReviewStatus.PENDING,
        message=review_message,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return DocumentDetailBundleScenario(
        tenant=tenant,
        user=user,
        document=document,
        attachment=attachment,
        review=review,
    )


def create_cross_tenant_document_scenario(
    db: Session,
    *,
    actor: User,
    actor_tenant_name: str = "Tenant A",
    target_tenant_name: str = "Tenant B",
    document_title: str = "Cross Tenant Document",
    document_status: DocumentStatus = DocumentStatus.DRAFT,
    document_visibility: DocumentVisibility = DocumentVisibility.INTERNAL,
) -> CrossTenantDocumentScenario:
    """Create two tenants with actor scoped to tenant A and document in tenant B."""
    actor_tenant = create_tenant(
        db,
        name=actor_tenant_name,
        slug=f"scenario-actor-{uuid4().hex[:6]}",
        company_type="customer",
    )
    target_tenant = create_tenant(
        db,
        name=target_tenant_name,
        slug=f"scenario-target-{uuid4().hex[:6]}",
        company_type="customer",
    )

    actor.tenant_id = actor_tenant.id
    db.commit()
    db.refresh(actor)

    document = create_document(
        db,
        title=document_title,
        document_number=f"DOC-XTEN-{uuid4().hex[:6].upper()}",
        description="Tenant-isolated scenario document",
        status=document_status,
        visibility=document_visibility,
        created_by=actor.id,
        tenant_id=target_tenant.id,
    )
    return CrossTenantDocumentScenario(
        actor_tenant=actor_tenant,
        target_tenant=target_tenant,
        actor=actor,
        document=document,
    )


def create_collaboration_access_scenario(
    db: Session,
    *,
    owner_password: str = "owner123",
    outsider_password: str = "outsider123",
) -> CollaborationAccessScenario:
    """Create owner+outsider users in separate tenants with one tenant-scoped document."""
    owner_tenant = create_tenant(
        db,
        name="Collab Tenant A",
        slug=f"collab-tenant-a-{uuid4().hex[:6]}",
        company_type="customer",
    )
    outsider_tenant = create_tenant(
        db,
        name="Collab Tenant B",
        slug=f"collab-tenant-b-{uuid4().hex[:6]}",
        company_type="customer",
    )

    owner = create_user(
        db,
        email=f"collab-owner-{uuid4().hex[:4]}@example.com",
        username=f"collab_owner_{uuid4().hex[:4]}",
        full_name="Collab Owner",
        plain_password=owner_password,
        role=UserRole.ADMIN,
        tenant_id=owner_tenant.id,
    )
    outsider = create_user(
        db,
        email=f"collab-outsider-{uuid4().hex[:4]}@example.com",
        username=f"collab_outsider_{uuid4().hex[:4]}",
        full_name="Collab Outsider",
        plain_password=outsider_password,
        role=UserRole.EDITOR,
        tenant_id=outsider_tenant.id,
    )

    document = create_document(
        db,
        title="Tenant-scoped collaboration doc",
        document_number=f"DOC-COLLAB-{uuid4().hex[:6].upper()}",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
        tenant_id=owner_tenant.id,
        created_by=owner.id,
    )
    return CollaborationAccessScenario(
        owner_tenant=owner_tenant,
        outsider_tenant=outsider_tenant,
        owner=owner,
        outsider=outsider,
        outsider_password=outsider_password,
        document=document,
    )
