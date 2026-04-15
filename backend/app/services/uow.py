"""Unit-of-Work helper for explicit transaction boundaries."""

from __future__ import annotations

from sqlalchemy.orm import Session


class UnitOfWork:
    """Transactional scope helper around a SQLAlchemy session."""

    def __init__(self, db: Session, *, auto_commit: bool = True):
        self.db = db
        self.auto_commit = auto_commit
        self._completed = False

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            if not self._completed:
                self.db.rollback()
            return False

        if self.auto_commit and not self._completed:
            self.db.commit()
            self._completed = True
        return False

    def flush(self) -> None:
        """Flush pending writes without committing."""
        self.db.flush()

    def commit(self) -> None:
        """Commit the underlying transaction explicitly."""
        self.db.commit()
        self._completed = True

    def rollback(self) -> None:
        """Rollback the underlying transaction explicitly."""
        self.db.rollback()
        self._completed = True
