"""Repository for comment aggregate access patterns."""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.models import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository):
    """Comment persistence/query access."""

    def list_top_level_with_replies(self, document_id: int) -> list[Comment]:
        return (
            self.db.query(Comment)
            .filter(
                Comment.document_id == document_id,
                Comment.parent_id == None,  # noqa: E711
            )
            .options(
                joinedload(Comment.user),
                joinedload(Comment.replies).joinedload(Comment.user),
                joinedload(Comment.replies).joinedload(Comment.replies).joinedload(Comment.user),
            )
            .order_by(Comment.created_at.desc())
            .all()
        )

    def list_for_document(self, document_id: int) -> list[Comment]:
        return self.db.query(Comment).filter(Comment.document_id == document_id).all()

    def get_by_id_for_document(
        self,
        comment_id: int,
        document_id: int,
        include_replies: bool = False,
    ) -> Comment | None:
        query = self.db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.document_id == document_id,
        )
        if include_replies:
            query = query.options(
                joinedload(Comment.user),
                joinedload(Comment.replies).joinedload(Comment.user),
                joinedload(Comment.replies).joinedload(Comment.replies).joinedload(Comment.user),
            )
        return query.first()

    def get_by_id_for_update(self, comment_id: int, document_id: int) -> Comment | None:
        """
        Get a comment with a row-level lock for update (Y15-018).

        This prevents race conditions when adding replies to the same parent comment.
        Uses SELECT ... FOR UPDATE on PostgreSQL, no-op on SQLite (uses serializable isolation).
        """
        dialect = self.db.bind.dialect.name if self.db.bind else "sqlite"
        query = self.db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.document_id == document_id,
        )
        query = query.options(
            joinedload(Comment.parent).joinedload(Comment.parent),
        )
        # PostgreSQL supports row-level locking; SQLite uses serializable transactions
        if dialect != "sqlite":
            query = query.with_for_update()
        return query.first()

    def list_distinct_user_ids_for_document(self, document_id: int) -> list[int]:
        rows = (
            self.db.query(Comment.user_id)
            .filter(Comment.document_id == document_id)
            .distinct()
            .all()
        )
        return [row[0] for row in rows]

    def delete_replies_for_parent(self, parent_comment_id: int) -> None:
        self.db.query(Comment).filter(Comment.parent_id == parent_comment_id).delete()
