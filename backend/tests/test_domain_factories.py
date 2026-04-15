"""Tests for domain factories introduced in Task 83."""

from datetime import datetime, timedelta

from app.domain.factories import DocumentFactory, InvitationFactory, VersionFactory
from app.models import InvitationStatus, UserRole, Version, VersionBumpType


def test_document_factory_create_document_sets_core_fields():
    document = DocumentFactory.create_document(
        title="Factory Document",
        document_number="DOC-20260227-0001",
        created_by=7,
        description="factory",
        topic="sdk-tools",
        platform_name="Core Platform",
        platform_id=11,
        tenant_id=5,
        parent_id=3,
    )

    assert document.title == "Factory Document"
    assert document.document_number == "DOC-20260227-0001"
    assert document.created_by == 7
    assert document.topic == "sdk-tools"
    assert document.platform == "Core Platform"
    assert document.platform_id == 11
    assert document.tenant_id == 5
    assert document.parent_id == 3


def test_document_factory_initial_version_defaults():
    version = DocumentFactory.create_initial_version(document_id=42, created_by=9)

    assert version.document_id == 42
    assert version.version_number == 1
    assert version.semantic_version == "1.0.0"
    assert version.bump_type == VersionBumpType.MAJOR
    assert version.content == ""
    assert version.changes_summary == "Initial version"
    assert version.created_by == 9


def test_document_factory_patch_version_uses_latest_content_and_semver():
    latest = Version(
        document_id=12,
        version_number=4,
        semantic_version="4.1.9",
        content="latest content",
        created_by=3,
    )

    version = DocumentFactory.create_patch_version(
        document_id=12,
        latest_version=latest,
        changes_summary="title update",
        created_by=8,
    )

    assert version.version_number == 5
    assert version.semantic_version == "4.1.10"
    assert version.content == "latest content"
    assert version.bump_type == VersionBumpType.PATCH
    assert version.changes_summary == "title update"


def test_version_factory_creates_candidate_from_previous_version():
    last_version = Version(
        document_id=21,
        version_number=2,
        semantic_version="2.5.4",
        content="prev",
        created_by=10,
    )

    version = VersionFactory.create_candidate_version(
        document_id=21,
        created_by=11,
        last_version=last_version,
        bump_type=VersionBumpType.MINOR,
        content="new content",
        changes_summary="minor release",
    )

    assert version.version_number == 3
    assert version.semantic_version == "2.6.0"
    assert version.bump_type == VersionBumpType.MINOR
    assert version.content == "new content"
    assert version.is_published is False


def test_version_factory_falls_back_when_previous_semver_invalid():
    last_version = Version(
        document_id=22,
        version_number=3,
        semantic_version="bad-value",
        content="prev",
        created_by=10,
    )

    version = VersionFactory.create_candidate_version(
        document_id=22,
        created_by=11,
        last_version=last_version,
        bump_type=VersionBumpType.PATCH,
        content="new",
        changes_summary="patch",
    )

    assert version.version_number == 4
    assert version.semantic_version == "3.0.1"


def test_invitation_factory_builds_pending_invitation():
    expires_at = datetime.utcnow() + timedelta(days=7)
    invitation = InvitationFactory.create_invitation(
        email="factory-invite@example.com",
        token="token-123",
        role=UserRole.CUSTOMER,
        invited_by=14,
        tenant_id=2,
        message="Welcome",
        expires_at=expires_at,
    )

    assert invitation.email == "factory-invite@example.com"
    assert invitation.token == "token-123"
    assert invitation.role == UserRole.CUSTOMER
    assert invitation.invited_by == 14
    assert invitation.tenant_id == 2
    assert invitation.message == "Welcome"
    assert invitation.expires_at == expires_at
    assert invitation.status == InvitationStatus.PENDING
