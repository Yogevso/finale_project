"""Shared assistant document/version visibility rules."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.policies.access_policies import DocumentAccessPolicy, safe_user_role
from app.models import Document, DocumentStatus, DocumentVisibility, User, UserRole, Version

_access_policy = DocumentAccessPolicy()


def assistant_can_view_document(
    user: User,
    document: Document,
    *,
    tenant_id: int | None = None,
) -> bool:
    """Assistant-facing document read check.

    This keeps the document visibility rules from ``DocumentAccessPolicy`` while
    preserving tenant isolation for non-public content and unpublished public drafts.
    """
    if not _access_policy.can_view_document(user, document):
        return False

    role = safe_user_role(user)
    if role is None:
        return False

    if role == UserRole.SYSTEM_ADMIN:
        return True

    scoped_tenant_id = tenant_id if tenant_id is not None else user.tenant_id

    if document.visibility == DocumentVisibility.PUBLIC:
        if document.status == DocumentStatus.ACTIVE:
            return True
        return (
            role != UserRole.CUSTOMER
            and scoped_tenant_id is not None
            and document.tenant_id == scoped_tenant_id
        )

    if role == UserRole.CUSTOMER:
        return True

    return scoped_tenant_id is not None and document.tenant_id == scoped_tenant_id


def resolve_assistant_visible_version(
    db: Session,
    *,
    user: User,
    document: Document,
    tenant_id: int | None = None,
) -> Version | None:
    """Return the document version the assistant should expose to this user.

    Internal users follow management behavior and see the latest version.
    Customers follow portal/viewer behavior and only see the latest published version.
    """
    if not assistant_can_view_document(user, document, tenant_id=tenant_id):
        return None

    query = db.query(Version).filter(Version.document_id == document.id)
    role = safe_user_role(user)
    if role is None:
        return None
    if role == UserRole.CUSTOMER:
        query = query.filter(Version.is_published.is_(True))

    return query.order_by(Version.version_number.desc()).first()
