"""Version-domain factories for candidate creation workflows."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.conversion.version_toc import derive_version_toc
from app.domain.value_objects import SemanticVersion
from app.models import Version, VersionBumpType


def _previous_toc(last_version: Optional[Version]) -> list[dict[str, Any]]:
    """Read the previous version's stored contents, tolerating a bad column."""
    raw = getattr(last_version, "toc_json", None) if last_version else None
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


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

        # An edit yields HTML, never the original file, so the contents are
        # rebuilt from its headings and the page numbers are carried across from
        # the previous version. Skipping this leaves the new version with none,
        # and a review then reports every entry as removed.
        toc_items = derive_version_toc(content, _previous_toc(last_version))

        return Version(
            document_id=document_id,
            version_number=next_version_number,
            semantic_version=next_semantic_version,
            bump_type=bump_type,
            content=content,
            toc_json=json.dumps(toc_items) if toc_items else None,
            changes_summary=changes_summary,
            created_by=created_by,
            is_published=False,
        )
