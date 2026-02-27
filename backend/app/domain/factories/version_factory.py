"""Version-domain factories for candidate creation workflows."""

from __future__ import annotations

from typing import Optional

from app.domain.value_objects import SemanticVersion
from app.models import Version, VersionBumpType


class VersionFactory:
    """Factory methods for version aggregate initialization paths."""

    @staticmethod
    def create_candidate_version(
        *,
        document_id: int,
        created_by: int,
        last_version: Optional[Version],
        bump_type: VersionBumpType,
        content: Optional[str],
        changes_summary: Optional[str],
    ) -> Version:
        next_version_number = 1 if not last_version else last_version.version_number + 1
        if not last_version:
            next_semantic_version = str(SemanticVersion.initial())
        else:
            previous_semver = SemanticVersion.from_raw(
                last_version.semantic_version,
                last_version.version_number,
            )
            next_semantic_version = str(previous_semver.bumped(bump_type))

        return Version(
            document_id=document_id,
            version_number=next_version_number,
            semantic_version=next_semantic_version,
            bump_type=bump_type,
            content=content,
            changes_summary=changes_summary,
            created_by=created_by,
            is_published=False,
        )
