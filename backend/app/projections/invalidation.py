"""Write-side invalidation hooks for read projections."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import (
    Attachment,
    AuditLog,
    Comment,
    Document,
    Feedback,
    ReadingProgress,
    ReviewRequest,
    SavedSearch,
    Tenant,
    User,
    Version,
)
from app.projections.runtime import invalidate_projection_scopes

_SESSION_SCOPES_KEY = "projection_invalidation_scopes"
_LISTENERS_REGISTERED = False

_MODEL_SCOPES: tuple[tuple[type[object], frozenset[str]], ...] = (
    (Document, frozenset({"analytics", "search", "portal", "public"})),
    (Version, frozenset({"analytics", "search", "portal", "public"})),
    (Attachment, frozenset({"portal", "public"})),
    (Feedback, frozenset({"analytics", "portal"})),
    (Comment, frozenset({"analytics"})),
    (AuditLog, frozenset({"analytics"})),
    (ReadingProgress, frozenset({"analytics"})),
    (ReviewRequest, frozenset({"analytics"})),
    (User, frozenset({"analytics"})),
    (Tenant, frozenset({"analytics", "portal"})),
    (SavedSearch, frozenset({"search"})),
)


def _scopes_for_instance(instance: object) -> set[str]:
    scopes: set[str] = set()
    for model_type, model_scopes in _MODEL_SCOPES:
        if isinstance(instance, model_type):
            scopes.update(model_scopes)
    return scopes


def _record_pending_projection_scopes(session: Session) -> None:
    pending_scopes = set(session.info.get(_SESSION_SCOPES_KEY, set()))
    changed_instances = tuple(session.new) + tuple(session.dirty) + tuple(session.deleted)
    for instance in changed_instances:
        pending_scopes.update(_scopes_for_instance(instance))
    if pending_scopes:
        session.info[_SESSION_SCOPES_KEY] = pending_scopes


def _on_after_flush(session: Session, _flush_context) -> None:
    _record_pending_projection_scopes(session)


def _on_after_commit(session: Session) -> None:
    scopes = set(session.info.pop(_SESSION_SCOPES_KEY, set()))
    if scopes:
        invalidate_projection_scopes(scopes)


def _on_after_rollback(session: Session) -> None:
    session.info.pop(_SESSION_SCOPES_KEY, None)


def register_projection_invalidation_listeners() -> None:
    """Register SQLAlchemy session listeners once per process."""
    global _LISTENERS_REGISTERED
    if _LISTENERS_REGISTERED:
        return

    event.listen(Session, "after_flush", _on_after_flush)
    event.listen(Session, "after_commit", _on_after_commit)
    event.listen(Session, "after_rollback", _on_after_rollback)
    _LISTENERS_REGISTERED = True
