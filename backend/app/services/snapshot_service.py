"""
Snapshot Service

Handles creating, restoring, and managing collaboration snapshots.
Snapshots are point-in-time saves during collaboration - NOT release versions.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    CollaborationActivity,
    CollaborationActivityType,
    CollaborationSnapshot,
    Document,
    SnapshotType,
)


class SnapshotService:
    """Service for managing collaboration snapshots"""

    # Default retention settings
    AUTO_SAVE_RETENTION_DAYS = 7
    MAX_AUTO_SAVES_PER_DOCUMENT = 10
    AUTO_SAVE_INTERVAL_MINUTES = 5

    @staticmethod
    def create_snapshot(
        db: Session,
        document_id: int,
        snapshot_type: SnapshotType,
        yjs_state: bytes,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        html_content: Optional[str] = None,
    ) -> CollaborationSnapshot:
        """
        Create a new snapshot of the document's current state.

        Args:
            db: Database session
            document_id: ID of the document
            snapshot_type: Type of snapshot (auto_save, manual_save, etc.)
            yjs_state: Binary Yjs document state
            user_id: ID of user creating snapshot (optional for auto-saves)
            session_id: Collaboration session ID (optional)
            name: Optional name for the snapshot
            description: Optional description
            html_content: Optional rendered HTML content

        Returns:
            The created CollaborationSnapshot
        """
        # Calculate expiration for auto-saves
        expires_at = None
        if snapshot_type == SnapshotType.AUTO_SAVE:
            expires_at = datetime.utcnow() + timedelta(
                days=SnapshotService.AUTO_SAVE_RETENTION_DAYS
            )

        # Generate default name if not provided
        if not name:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            type_label = snapshot_type.value.replace("_", " ").title()
            name = f"{type_label} - {timestamp}"

        # Create snapshot
        snapshot = CollaborationSnapshot(
            document_id=document_id,
            snapshot_type=snapshot_type,
            name=name,
            description=description,
            yjs_state=yjs_state,
            html_content=html_content,
            state_size=len(yjs_state),
            created_by=user_id,
            session_id=session_id,
            is_pinned=False,
            expires_at=expires_at,
        )
        db.add(snapshot)

        # Log activity
        if user_id:
            activity = CollaborationActivity(
                document_id=document_id,
                user_id=user_id,
                session_id=session_id,
                activity_type=CollaborationActivityType.SNAPSHOT_CREATED,
                details=f'{{"snapshot_type": "{snapshot_type.value}", "name": "{name}"}}',
            )
            db.add(activity)

        db.commit()
        db.refresh(snapshot)

        # Cleanup old auto-saves if needed
        if snapshot_type == SnapshotType.AUTO_SAVE:
            SnapshotService._cleanup_excess_auto_saves(db, document_id)

        return snapshot

    @staticmethod
    def restore_snapshot(
        db: Session,
        snapshot_id: int,
        user_id: int,
        session_id: Optional[str] = None,
    ) -> Optional[Document]:
        """
        Restore a document to a previous snapshot state.

        Args:
            db: Database session
            snapshot_id: ID of the snapshot to restore
            user_id: ID of user performing restore
            session_id: Current collaboration session ID

        Returns:
            The updated Document, or None if snapshot not found
        """
        snapshot = (
            db.query(CollaborationSnapshot).filter(CollaborationSnapshot.id == snapshot_id).first()
        )

        if not snapshot:
            return None

        # Get the document
        document = db.query(Document).filter(Document.id == snapshot.document_id).first()
        if not document:
            return None

        # Create a snapshot of current state before restoring (for undo)
        if document.yjs_state:
            SnapshotService.create_snapshot(
                db=db,
                document_id=document.id,
                snapshot_type=SnapshotType.MANUAL_SAVE,
                yjs_state=document.yjs_state,
                user_id=user_id,
                session_id=session_id,
                name=f"Before restore - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                description=f"Auto-created before restoring to snapshot #{snapshot_id}",
            )

        # Restore the Yjs state
        document.yjs_state = snapshot.yjs_state
        document.updated_at = datetime.utcnow()

        # Log activity
        activity = CollaborationActivity(
            document_id=document.id,
            user_id=user_id,
            session_id=session_id,
            activity_type=CollaborationActivityType.SNAPSHOT_RESTORED,
            details=f'{{"snapshot_id": {snapshot_id}, "snapshot_name": "{snapshot.name}"}}',
        )
        db.add(activity)

        db.commit()
        db.refresh(document)

        return document

    @staticmethod
    def list_snapshots(
        db: Session,
        document_id: int,
        include_expired: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CollaborationSnapshot], int]:
        """
        List snapshots for a document.

        Args:
            db: Database session
            document_id: ID of the document
            include_expired: Whether to include expired snapshots
            limit: Maximum number to return
            offset: Pagination offset

        Returns:
            Tuple of (snapshots list, total count)
        """
        query = db.query(CollaborationSnapshot).filter(
            CollaborationSnapshot.document_id == document_id
        )

        if not include_expired:
            query = query.filter(
                (CollaborationSnapshot.expires_at.is_(None))
                | (CollaborationSnapshot.expires_at > datetime.utcnow())
            )

        total = query.count()
        snapshots = (
            query.order_by(CollaborationSnapshot.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return snapshots, total

    @staticmethod
    def get_snapshot(db: Session, snapshot_id: int) -> Optional[CollaborationSnapshot]:
        """Get a single snapshot by ID."""
        return (
            db.query(CollaborationSnapshot).filter(CollaborationSnapshot.id == snapshot_id).first()
        )

    @staticmethod
    def update_snapshot(
        db: Session,
        snapshot_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_pinned: Optional[bool] = None,
    ) -> Optional[CollaborationSnapshot]:
        """
        Update snapshot metadata.

        Args:
            db: Database session
            snapshot_id: ID of the snapshot
            name: New name (optional)
            description: New description (optional)
            is_pinned: New pinned status (optional)

        Returns:
            Updated snapshot or None if not found
        """
        snapshot = (
            db.query(CollaborationSnapshot).filter(CollaborationSnapshot.id == snapshot_id).first()
        )

        if not snapshot:
            return None

        if name is not None:
            snapshot.name = name
        if description is not None:
            snapshot.description = description
        if is_pinned is not None:
            snapshot.is_pinned = is_pinned
            # If pinning, remove expiration
            if is_pinned:
                snapshot.expires_at = None

        db.commit()
        db.refresh(snapshot)
        return snapshot

    @staticmethod
    def delete_snapshot(db: Session, snapshot_id: int) -> bool:
        """
        Delete a snapshot.

        Args:
            db: Database session
            snapshot_id: ID of the snapshot to delete

        Returns:
            True if deleted, False if not found
        """
        snapshot = (
            db.query(CollaborationSnapshot).filter(CollaborationSnapshot.id == snapshot_id).first()
        )

        if not snapshot:
            return False

        db.delete(snapshot)
        db.commit()
        return True

    @staticmethod
    def _cleanup_excess_auto_saves(db: Session, document_id: int) -> int:
        """
        Remove excess auto-save snapshots beyond the limit.

        Keeps the most recent MAX_AUTO_SAVES_PER_DOCUMENT auto-saves,
        deleting older ones (unless pinned).

        Returns:
            Number of snapshots deleted
        """
        # Get all unpinned auto-saves for this document, ordered by date
        auto_saves = (
            db.query(CollaborationSnapshot)
            .filter(
                CollaborationSnapshot.document_id == document_id,
                CollaborationSnapshot.snapshot_type == SnapshotType.AUTO_SAVE,
                CollaborationSnapshot.is_pinned.is_(False),
            )
            .order_by(CollaborationSnapshot.created_at.desc())
            .all()
        )

        # Keep only the most recent ones
        if len(auto_saves) <= SnapshotService.MAX_AUTO_SAVES_PER_DOCUMENT:
            return 0

        to_delete = auto_saves[SnapshotService.MAX_AUTO_SAVES_PER_DOCUMENT :]
        deleted_count = 0

        for snapshot in to_delete:
            db.delete(snapshot)
            deleted_count += 1

        db.commit()
        return deleted_count

    @staticmethod
    def cleanup_expired_snapshots(db: Session) -> int:
        """
        Delete all expired snapshots across all documents.

        This should be called periodically (e.g., daily cron job).

        Returns:
            Number of snapshots deleted
        """
        expired = (
            db.query(CollaborationSnapshot)
            .filter(
                CollaborationSnapshot.expires_at.isnot(None),
                CollaborationSnapshot.expires_at < datetime.utcnow(),
                CollaborationSnapshot.is_pinned.is_(False),
            )
            .all()
        )

        deleted_count = len(expired)
        for snapshot in expired:
            db.delete(snapshot)

        db.commit()
        return deleted_count

    @staticmethod
    def should_auto_save(
        db: Session,
        document_id: int,
    ) -> bool:
        """
        Check if an auto-save should be created based on the interval.

        Returns:
            True if enough time has passed since last auto-save
        """
        last_auto_save = (
            db.query(CollaborationSnapshot)
            .filter(
                CollaborationSnapshot.document_id == document_id,
                CollaborationSnapshot.snapshot_type == SnapshotType.AUTO_SAVE,
            )
            .order_by(CollaborationSnapshot.created_at.desc())
            .first()
        )

        if not last_auto_save:
            return True

        time_since = datetime.utcnow() - last_auto_save.created_at
        return time_since.total_seconds() >= (SnapshotService.AUTO_SAVE_INTERVAL_MINUTES * 60)
