"""
AH-013: Published Snapshot Diff Tool

Compare current document content vs. last published snapshot.
"""

from difflib import unified_diff
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Attachment,
    AttachmentArtifact,
    Document,
    User,
    UserRole,
    Version,
)
from app.security import get_current_active_user

router = APIRouter(prefix="/admin/snapshot-diff", tags=["Admin - Snapshot Diff"])


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role not in (UserRole.ADMIN, UserRole.SYSTEM_ADMIN):
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user


@router.get("/{document_id}")
async def get_snapshot_diff(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Compare current document attachments vs. last published version.

    Returns a diff for each attachment showing what changed since publish.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get last published version
    last_version = (
        db.query(Version)
        .filter(Version.document_id == document_id)
        .order_by(Version.version_number.desc())
        .first()
    )

    if not last_version:
        return {
            "document_id": document_id,
            "title": document.title,
            "has_published_version": False,
            "diff": None,
            "message": "No published version exists",
        }

    # Get current attachments
    current_attachments = (
        db.query(Attachment)
        .filter(Attachment.document_id == document_id)
        .all()
    )

    diffs = []
    for attach in current_attachments:
        # Get current HTML artifact
        current_artifact = (
            db.query(AttachmentArtifact)
            .filter(
                AttachmentArtifact.attachment_id == attach.id,
                AttachmentArtifact.kind == "reader_html",
            )
            .first()
        )

        # Get snapshot HTML from version
        snapshot_artifact = (
            db.query(AttachmentArtifact)
            .filter(
                AttachmentArtifact.attachment_id == attach.id,
                AttachmentArtifact.kind == "snapshot_html",
            )
            .first()
        )

        current_html = ""
        snapshot_html = ""

        if current_artifact and current_artifact.data:
            try:
                current_html = current_artifact.data.decode("utf-8", errors="replace")
            except Exception:
                current_html = "[binary data]"

        if snapshot_artifact and snapshot_artifact.data:
            try:
                snapshot_html = snapshot_artifact.data.decode("utf-8", errors="replace")
            except Exception:
                snapshot_html = "[binary data]"

        # Generate unified diff
        diff_lines = list(unified_diff(
            snapshot_html.splitlines(keepends=True),
            current_html.splitlines(keepends=True),
            fromfile=f"published/{attach.filename}",
            tofile=f"current/{attach.filename}",
            lineterm="",
        ))

        diffs.append({
            "attachment_id": attach.id,
            "filename": attach.filename,
            "has_changes": len(diff_lines) > 0,
            "diff": "".join(diff_lines) if diff_lines else None,
        })

    return {
        "document_id": document_id,
        "title": document.title,
        "has_published_version": True,
        "version_number": last_version.version_number,
        "published_at": last_version.created_at.isoformat() if last_version.created_at else None,
        "attachments": diffs,
    }
