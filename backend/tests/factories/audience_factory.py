"""Audience-focused test data factories for edge-case scenarios."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Document, DocumentStatus, DocumentVisibility, Tenant
from tests.factories.domain import create_document


@dataclass(frozen=True, slots=True)
class AudienceEdgeCaseSet:
    internal_document: Document
    public_document: Document
    company_single_assignment: Document
    company_multi_assignment: Document


def create_audience_document(
    db: Session,
    *,
    created_by: int,
    title: str,
    document_number: str,
    visibility: DocumentVisibility,
    status: DocumentStatus = DocumentStatus.ACTIVE,
    assigned_companies: list[Tenant] | None = None,
    tenant_id: int | None = None,
) -> Document:
    document = create_document(
        db,
        title=title,
        document_number=document_number,
        description=f"Audience factory: {title}",
        status=status,
        visibility=visibility,
        created_by=created_by,
        tenant_id=tenant_id,
    )
    if assigned_companies:
        document.assigned_companies = list(assigned_companies)
        db.commit()
        db.refresh(document)
    return document


def create_audience_edge_case_set(
    db: Session,
    *,
    created_by: int,
    primary_company: Tenant,
    secondary_company: Tenant,
) -> AudienceEdgeCaseSet:
    internal_doc = create_audience_document(
        db,
        created_by=created_by,
        title="Audience Internal Edge",
        document_number="DOC-AUD-EDGE-INT-001",
        visibility=DocumentVisibility.INTERNAL,
        tenant_id=primary_company.id,
    )
    public_doc = create_audience_document(
        db,
        created_by=created_by,
        title="Audience Public Edge",
        document_number="DOC-AUD-EDGE-PUB-001",
        visibility=DocumentVisibility.PUBLIC,
        tenant_id=primary_company.id,
    )
    company_single = create_audience_document(
        db,
        created_by=created_by,
        title="Audience Company Single Edge",
        document_number="DOC-AUD-EDGE-COMP-001",
        visibility=DocumentVisibility.COMPANY,
        assigned_companies=[primary_company],
        tenant_id=primary_company.id,
    )
    company_multi = create_audience_document(
        db,
        created_by=created_by,
        title="Audience Company Multi Edge",
        document_number="DOC-AUD-EDGE-COMP-002",
        visibility=DocumentVisibility.COMPANY,
        assigned_companies=[primary_company, secondary_company],
        tenant_id=primary_company.id,
    )
    return AudienceEdgeCaseSet(
        internal_document=internal_doc,
        public_document=public_doc,
        company_single_assignment=company_single,
        company_multi_assignment=company_multi,
    )
