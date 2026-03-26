"""Repository layer for aggregate query access."""

from app.repositories.comment_repository import CommentRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.support_ticket_repository import SupportTicketRepository
from app.repositories.user_repository import UserRepository
from app.repositories.version_repository import VersionRepository

__all__ = [
    "DocumentRepository",
    "VersionRepository",
    "UserRepository",
    "CommentRepository",
    "InvitationRepository",
    "OutboxRepository",
    "SupportTicketRepository",
]
