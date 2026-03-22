"""Collaboration snapshot manager."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.collaboration.base import CollaborationManagerBase
from app.models import SnapshotType, User
from app.repositories import UserRepository
from app.services.snapshot_service import SnapshotService


class SnapshotManager(CollaborationManagerBase):
    """Manages collaboration snapshot workflows."""

    def __init__(self, db: Session, **kwargs) -> None:
        super().__init__(db, **kwargs)
        self.user_repository = UserRepository(db)

    def create_snapshot(
        self,
        *,
        document_id: int,
        current_user: User,
        name: str | None,
        description: str | None,
        session_id: str | None,
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_write_access(
            document=document,
            current_user=current_user,
            denied_detail="You don't have permission to create snapshots for this document",
        )

        if not document.yjs_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no collaboration state to snapshot",
            )

        snapshot = SnapshotService.create_snapshot(
            db=self.chat_db,
            document_id=document_id,
            snapshot_type=SnapshotType.MANUAL_SAVE,
            yjs_state=document.yjs_state,
            user_id=current_user.id,
            session_id=session_id,
            name=name,
            description=description,
        )
        return self._serialize_snapshot(snapshot, created_by_username=current_user.username)

    def list_snapshots(
        self,
        *,
        document_id: int,
        current_user: User,
        limit: int,
        offset: int,
        include_expired: bool,
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_read_access(document=document, current_user=current_user)

        snapshots, total = SnapshotService.list_snapshots(
            db=self.chat_db,
            document_id=document_id,
            include_expired=include_expired,
            limit=limit,
            offset=offset,
        )
        usernames_by_id = self._batch_snapshot_creator_usernames(snapshots)

        return {
            "document_id": document_id,
            "snapshots": [
                self._serialize_snapshot(
                    snapshot,
                    created_by_username=usernames_by_id.get(snapshot.created_by),
                )
                for snapshot in snapshots
            ],
            "total": total,
            "has_more": offset + limit < total,
        }

    def get_snapshot(
        self, *, document_id: int, snapshot_id: int, current_user: User
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_read_access(document=document, current_user=current_user)

        snapshot = SnapshotService.get_snapshot(self.chat_db, snapshot_id)
        if not snapshot or snapshot.document_id != document_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

        username = None
        if snapshot.created_by:
            user = self.user_repository.get_by_id(snapshot.created_by)
            username = user.username if user else None
        return self._serialize_snapshot(snapshot, created_by_username=username)

    def restore_snapshot(
        self,
        *,
        document_id: int,
        snapshot_id: int,
        session_id: str | None,
        current_user: User,
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_write_access(
            document=document,
            current_user=current_user,
            denied_detail="You don't have permission to restore snapshots for this document",
        )

        snapshot = SnapshotService.get_snapshot(self.chat_db, snapshot_id)
        if not snapshot or snapshot.document_id != document_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

        updated_document = SnapshotService.restore_snapshot(
            db=self.chat_db,
            snapshot_id=snapshot_id,
            user_id=current_user.id,
            session_id=session_id,
        )
        if not updated_document:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore snapshot",
            )

        return {
            "message": "Snapshot restored successfully",
            "snapshot_id": snapshot_id,
            "snapshot_name": snapshot.name,
            "document_id": document_id,
        }

    def update_snapshot(
        self,
        *,
        document_id: int,
        snapshot_id: int,
        current_user: User,
        name: str | None,
        description: str | None,
        is_pinned: bool | None,
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_write_access(
            document=document,
            current_user=current_user,
            denied_detail="You don't have permission to modify snapshots for this document",
        )

        snapshot = SnapshotService.get_snapshot(self.chat_db, snapshot_id)
        if not snapshot or snapshot.document_id != document_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

        updated_snapshot = SnapshotService.update_snapshot(
            db=self.chat_db,
            snapshot_id=snapshot_id,
            name=name,
            description=description,
            is_pinned=is_pinned,
        )
        if not updated_snapshot:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update snapshot",
            )

        username = None
        if updated_snapshot.created_by:
            user = self.user_repository.get_by_id(updated_snapshot.created_by)
            username = user.username if user else None
        return self._serialize_snapshot(updated_snapshot, created_by_username=username)

    def delete_snapshot(
        self, *, document_id: int, snapshot_id: int, current_user: User
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_write_access(
            document=document,
            current_user=current_user,
            denied_detail="You don't have permission to delete snapshots for this document",
        )

        snapshot = SnapshotService.get_snapshot(self.chat_db, snapshot_id)
        if not snapshot or snapshot.document_id != document_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

        success = SnapshotService.delete_snapshot(self.chat_db, snapshot_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete snapshot",
            )
        return {"message": "Snapshot deleted successfully", "snapshot_id": snapshot_id}

    def create_auto_snapshot(
        self, *, document_id: int, session_id: str | None, current_user: User
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)

        if not document.yjs_state:
            return {"created": False, "reason": "No collaboration state"}
        if not SnapshotService.should_auto_save(self.chat_db, document_id):
            return {"created": False, "reason": "Too soon since last auto-save"}

        snapshot = SnapshotService.create_snapshot(
            db=self.chat_db,
            document_id=document_id,
            snapshot_type=SnapshotType.AUTO_SAVE,
            yjs_state=document.yjs_state,
            user_id=current_user.id,
            session_id=session_id,
        )
        return {
            "created": True,
            "snapshot_id": snapshot.id,
            "snapshot_name": snapshot.name,
        }

    def _batch_snapshot_creator_usernames(self, snapshots: list) -> dict[int, str]:
        creator_ids = {snapshot.created_by for snapshot in snapshots if snapshot.created_by}
        if not creator_ids:
            return {}
        users = self.user_repository.list_by_ids(list(creator_ids))
        return {user.id: user.username for user in users}

    @staticmethod
    def _serialize_snapshot(snapshot, *, created_by_username: str | None) -> dict[str, object]:
        return {
            "id": snapshot.id,
            "document_id": snapshot.document_id,
            "snapshot_type": snapshot.snapshot_type.value,
            "name": snapshot.name,
            "description": snapshot.description,
            "state_size": snapshot.state_size,
            "created_by": snapshot.created_by,
            "created_by_username": created_by_username,
            "session_id": snapshot.session_id,
            "is_pinned": snapshot.is_pinned,
            "expires_at": snapshot.expires_at,
            "created_at": snapshot.created_at,
        }
