"""C6 fix: Centralised resolver for published-version attachment scoping.

All public-facing attachment endpoints (viewer, public, portal) MUST use this
resolver instead of querying attachments directly.  The resolver consumes the
``Version.published_attachment_ids_snapshot`` captured at publish time and falls
back to a cutoff-timestamp query for versions published before the snapshot
column existed.
"""

from __future__ import annotations

import json
from typing import Optional, Set

from sqlalchemy.orm import Session

from app.models import Attachment, Version


def resolve_published_attachment_ids(
    db: Session,
    document_id: int,
    *,
    version_id: Optional[int] = None,
) -> Set[int]:
    """Return the set of attachment IDs visible for a published document.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    document_id:
        The document whose published attachments we want.
    version_id:
        If given, scope to that specific published version.  Otherwise use the
        *latest* published version.

    Returns
    -------
    set[int]
        Attachment IDs that were present at publish time.  Empty set when
        no published version exists.
    """
    if version_id is not None:
        version = (
            db.query(Version)
            .filter(
                Version.id == version_id,
                Version.document_id == document_id,
                Version.is_published.is_(True),
            )
            .first()
        )
    else:
        version = (
            db.query(Version)
            .filter(
                Version.document_id == document_id,
                Version.is_published.is_(True),
            )
            .order_by(Version.version_number.desc())
            .first()
        )

    if version is None:
        return set()

    # Prefer the explicit snapshot captured at publish time (AF-003).
    snapshot_json = getattr(version, "published_attachment_ids_snapshot", None)
    if snapshot_json:
        try:
            ids = json.loads(snapshot_json)
            if isinstance(ids, list):
                return set(ids)
        except (json.JSONDecodeError, TypeError):
            pass  # fall through to cutoff approach

    # Fallback: cutoff-timestamp query for pre-snapshot publishes.
    cutoff = version.published_at or version.created_at
    rows = (
        db.query(Attachment.id)
        .filter(
            Attachment.document_id == document_id,
            Attachment.uploaded_at <= cutoff,
        )
        .all()
    )
    return {row[0] for row in rows}


def is_attachment_in_published_snapshot(
    db: Session,
    document_id: int,
    attachment_id: int,
) -> bool:
    """Convenience: check whether *attachment_id* belongs to the published set."""
    return attachment_id in resolve_published_attachment_ids(db, document_id)
