"""Unit tests for explicit access-policy objects."""

from app.application.policies import DocumentAccessPolicy, InvitationPolicy, ReviewPolicy
from app.dependencies.tenant import TenantContext
from app.models import Document, DocumentStatus, User, UserRole


def _build_user(user_id: int, role: UserRole, tenant_id: int | None = None) -> User:
    return User(
        id=user_id,
        username=f"user-{user_id}",
        email=f"user-{user_id}@example.com",
        role=role,
        tenant_id=tenant_id,
        is_active=True,
        hashed_password="x",
    )


def test_document_policy_tenant_boundary_blocks_cross_tenant_internal_user():
    policy = DocumentAccessPolicy()
    user = _build_user(1, UserRole.EDITOR, tenant_id=2)
    document = Document(
        id=10,
        title="Scoped",
        document_number="DOC-SCOPED-001",
        status=DocumentStatus.DRAFT,
        tenant_id=1,
        created_by=1,
    )
    assert policy.can_access_document_tenant(user, document) is False


def test_review_policy_allows_peer_review_for_editor_submitter():
    policy = ReviewPolicy()
    reviewer = _build_user(1, UserRole.EDITOR, tenant_id=1)
    submitter = _build_user(2, UserRole.EDITOR, tenant_id=1)
    assert (
        policy.can_approve_review(
            reviewer,
            submitter,
            has_approve_permission=False,
            has_peer_approve_permission=True,
        )
        is True
    )


def test_review_policy_blocks_self_approval():
    policy = ReviewPolicy()
    reviewer = _build_user(1, UserRole.MANAGER, tenant_id=1)
    assert (
        policy.can_approve_review(
            reviewer,
            reviewer,
            has_approve_permission=True,
            has_peer_approve_permission=False,
        )
        is False
    )


def test_invitation_policy_resolve_tenant_for_non_system_user():
    policy = InvitationPolicy()
    tenant_ctx = TenantContext(
        tenant_id=7,
        user_id=1,
        user_role=UserRole.ADMIN,
        is_system_admin=False,
    )
    assert policy.resolve_invitation_tenant_id(None, tenant_ctx) == 7
    assert policy.resolve_invitation_tenant_id(7, tenant_ctx) == 7
    assert policy.resolve_invitation_tenant_id(8, tenant_ctx) is None


def test_document_policy_requires_editor_ownership_for_edits():
    policy = DocumentAccessPolicy()
    owner = _build_user(1, UserRole.EDITOR, tenant_id=7)
    other_editor = _build_user(2, UserRole.EDITOR, tenant_id=7)
    document = Document(
        id=11,
        title="Owned draft",
        document_number="DOC-OWN-001",
        status=DocumentStatus.DRAFT,
        tenant_id=7,
        created_by=owner.id,
    )

    assert policy.can_edit_document(owner, document, has_edit_permission=True) is True
    assert policy.can_edit_document(other_editor, document, has_edit_permission=True) is False
    assert policy.can_delete_document(other_editor, document, has_delete_permission=True) is False


def test_document_policy_allows_manager_to_manage_same_tenant_document():
    policy = DocumentAccessPolicy()
    manager = _build_user(3, UserRole.MANAGER, tenant_id=7)
    document = Document(
        id=12,
        title="Team doc",
        document_number="DOC-TEAM-001",
        status=DocumentStatus.DRAFT,
        tenant_id=7,
        created_by=99,
    )

    assert policy.can_edit_document(manager, document, has_edit_permission=True) is True
    assert policy.can_delete_document(manager, document, has_delete_permission=True) is True
