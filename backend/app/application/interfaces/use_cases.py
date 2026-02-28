"""Intent-shaped use-case contracts for the application layer."""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from app.models import User, UserRole


@runtime_checkable
class UserActor(Protocol):
    """Minimal user snapshot shape required for publish workflows."""

    id: int
    role: UserRole | str
    tenant_id: int | None
    is_active: bool


@runtime_checkable
class PublishApprovedVersion(Protocol):
    """Publish an approved version as a release workflow use-case."""

    def publish_approved_version(
        self, document_id: int, version_id: int, current_user: User | UserActor
    ) -> dict:
        """Publish a reviewed version for a document."""


@runtime_checkable
class AssignCompanySet(Protocol):
    """Replace the full company assignment set for a document."""

    def assign_company_set(
        self,
        document_id: int,
        company_ids: Sequence[int],
        *,
        if_match: str | None = None,
    ) -> int:
        """Apply the target assignment set and return resulting company count."""
