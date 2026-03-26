"""Dependency providers for collaboration managers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.collaboration import CollabStateManager, SessionManager, SnapshotManager
from app.db import get_chat_db, get_db
from app.dependencies.services import get_collaboration_service
from app.services.collaboration_service import CollaborationService


def get_collab_state_manager(db: Session = Depends(get_db)) -> CollabStateManager:
    return CollabStateManager(db)


def get_session_manager(
    db: Session = Depends(get_db),
    chat_db: Session = Depends(get_chat_db),
    collaboration_service: CollaborationService = Depends(get_collaboration_service),
) -> SessionManager:
    return SessionManager(db, chat_db=chat_db, collaboration_service=collaboration_service)


def get_snapshot_manager(
    db: Session = Depends(get_db),
    chat_db: Session = Depends(get_chat_db),
    collaboration_service: CollaborationService = Depends(get_collaboration_service),
) -> SnapshotManager:
    return SnapshotManager(db, chat_db=chat_db, collaboration_service=collaboration_service)
