"""Dependency providers for collaboration managers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.collaboration import CollabStateManager, SessionManager, SnapshotManager
from app.db import get_db


def get_collab_state_manager(db: Session = Depends(get_db)) -> CollabStateManager:
    return CollabStateManager(db)


def get_session_manager(db: Session = Depends(get_db)) -> SessionManager:
    return SessionManager(db)


def get_snapshot_manager(db: Session = Depends(get_db)) -> SnapshotManager:
    return SnapshotManager(db)
