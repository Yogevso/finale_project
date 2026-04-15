"""Base repository with constructor-injected SQLAlchemy session."""

from sqlalchemy.orm import Session


class BaseRepository:
    """Simple shared base for repositories."""

    def __init__(self, db: Session):
        self.db = db
