"""Chat service — internal messaging for direct and group chats (Wave X.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Chat,
    ChatMessage,
    ChatMessageType,
    ChatParticipant,
    ChatParticipantRole,
    ChatType,
    User,
    UserRole,
)


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Chat creation
    # ------------------------------------------------------------------

    def create_direct_chat(self, user_a: User, user_b_id: int) -> Chat:
        """Create or return existing direct chat between two users (X1-007)."""
        if user_a.id == user_b_id:
            raise HTTPException(status_code=400, detail="Cannot create chat with yourself")

        user_b = self.db.query(User).filter(User.id == user_b_id).first()
        if not user_b:
            raise HTTPException(status_code=404, detail="User not found")

        # Tenant isolation (X1-009) — allow internal staff to chat with customers cross-tenant
        internal_roles = {'system_admin', 'admin', 'manager', 'editor'}
        if user_a.tenant_id != user_b.tenant_id:
            if user_a.role not in internal_roles and user_b.role not in internal_roles:
                raise HTTPException(status_code=403, detail="Cannot chat with users in another organization")

        # Deduplication — check if direct chat already exists between these two
        dedup_query = (
            self.db.query(Chat)
            .join(ChatParticipant, Chat.id == ChatParticipant.chat_id)
            .filter(Chat.type == ChatType.DIRECT)
        )
        # Only filter by tenant when same-tenant (cross-tenant chats may be on either tenant)
        if user_a.tenant_id == user_b.tenant_id:
            dedup_query = dedup_query.filter(Chat.tenant_id == user_a.tenant_id)
        existing = (
            dedup_query
            .group_by(Chat.id)
            .having(
                and_(
                    func.sum(case((ChatParticipant.user_id == user_a.id, 1), else_=0)) > 0,
                    func.sum(case((ChatParticipant.user_id == user_b_id, 1), else_=0)) > 0,
                    func.count(ChatParticipant.id) == 2,
                )
            )
            .first()
        )
        if existing:
            return existing

        chat = Chat(
            type=ChatType.DIRECT,
            created_by=user_a.id,
            tenant_id=user_a.tenant_id,
        )
        self.db.add(chat)
        self.db.flush()

        for uid, role in [
            (user_a.id, ChatParticipantRole.OWNER),
            (user_b_id, ChatParticipantRole.MEMBER),
        ]:
            self.db.add(ChatParticipant(chat_id=chat.id, user_id=uid, role=role))

        self.db.commit()
        self.db.refresh(chat)
        return chat

    def create_group_chat(self, creator: User, name: str, participant_ids: list[int]) -> Chat:
        """Create a new group chat (X1-008)."""
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Group name is required")
        if len(participant_ids) < 1:
            raise HTTPException(status_code=400, detail="At least one other participant is required")

        # Validate all participants exist and are in the same tenant
        participants = (
            self.db.query(User)
            .filter(User.id.in_(participant_ids), User.tenant_id == creator.tenant_id, User.is_active.is_(True))
            .all()
        )
        valid_ids = {p.id for p in participants}
        invalid = set(participant_ids) - valid_ids - {creator.id}
        if invalid:
            raise HTTPException(status_code=400, detail="Some participants not found or not in your organization")

        chat = Chat(
            type=ChatType.GROUP,
            name=name.strip(),
            created_by=creator.id,
            tenant_id=creator.tenant_id,
        )
        self.db.add(chat)
        self.db.flush()

        # Creator is always owner
        self.db.add(ChatParticipant(chat_id=chat.id, user_id=creator.id, role=ChatParticipantRole.OWNER))
        for uid in valid_ids:
            if uid != creator.id:
                self.db.add(ChatParticipant(chat_id=chat.id, user_id=uid, role=ChatParticipantRole.MEMBER))

        # System message
        self.db.add(ChatMessage(
            chat_id=chat.id,
            sender_id=creator.id,
            content=f"{creator.full_name} created the group \"{name.strip()}\"",
            message_type=ChatMessageType.SYSTEM,
        ))

        self.db.commit()
        self.db.refresh(chat)
        return chat

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    def add_participant(self, chat_id: int, current_user: User, user_id: int) -> ChatParticipant:
        """Add a participant to a group chat (X1-008)."""
        chat = self._get_chat_with_permission(chat_id, current_user, require_admin=True)
        if chat.type != ChatType.GROUP:
            raise HTTPException(status_code=400, detail="Cannot add participants to direct chats")

        target = self.db.query(User).filter(User.id == user_id, User.tenant_id == chat.tenant_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")

        existing = self.db.query(ChatParticipant).filter_by(chat_id=chat_id, user_id=user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="User is already a participant")

        participant = ChatParticipant(chat_id=chat_id, user_id=user_id, role=ChatParticipantRole.MEMBER)
        self.db.add(participant)

        # System message
        self.db.add(ChatMessage(
            chat_id=chat_id,
            sender_id=current_user.id,
            content=f"{current_user.full_name} added {target.full_name} to the group",
            message_type=ChatMessageType.SYSTEM,
        ))

        self.db.commit()
        self.db.refresh(participant)
        return participant

    def remove_participant(self, chat_id: int, current_user: User, user_id: int) -> None:
        """Remove a participant from a group chat (X1-008)."""
        chat = self._get_chat_with_permission(chat_id, current_user, require_admin=True)
        if chat.type != ChatType.GROUP:
            raise HTTPException(status_code=400, detail="Cannot remove participants from direct chats")

        participant = self.db.query(ChatParticipant).filter_by(chat_id=chat_id, user_id=user_id).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")

        if participant.role == ChatParticipantRole.OWNER:
            raise HTTPException(status_code=400, detail="Cannot remove the chat owner")

        target = self.db.query(User).filter(User.id == user_id).first()
        self.db.delete(participant)

        self.db.add(ChatMessage(
            chat_id=chat_id,
            sender_id=current_user.id,
            content=f"{current_user.full_name} removed {target.full_name if target else 'a user'} from the group",
            message_type=ChatMessageType.SYSTEM,
        ))
        self.db.commit()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    # AD-018: maximum allowed chat message length (characters)
    MAX_MESSAGE_LENGTH = 5000

    def send_message(self, chat_id: int, sender: User, content: str) -> ChatMessage:
        """Send a message in a chat (X1-006)."""
        self._get_chat_with_permission(chat_id, sender)
        content = content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="Message content cannot be empty")
        if len(content) > self.MAX_MESSAGE_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Message exceeds maximum length of {self.MAX_MESSAGE_LENGTH} characters",
            )

        msg = ChatMessage(
            chat_id=chat_id,
            sender_id=sender.id,
            content=content,
            message_type=ChatMessageType.TEXT,
        )
        self.db.add(msg)

        # Update chat's last_message_at for sorting
        self.db.query(Chat).filter(Chat.id == chat_id).update({"last_message_at": datetime.utcnow()})

        self.db.commit()
        self.db.refresh(msg)
        return msg

    def send_file_message(
        self,
        chat_id: int,
        sender: User,
        file_url: str,
        file_name: str,
        file_size: int,
        file_mime_type: str,
    ) -> ChatMessage:
        """Send a file/image message in a chat."""
        self._get_chat_with_permission(chat_id, sender)

        msg = ChatMessage(
            chat_id=chat_id,
            sender_id=sender.id,
            content=file_name,
            message_type=ChatMessageType.FILE,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            file_mime_type=file_mime_type,
        )
        self.db.add(msg)
        self.db.query(Chat).filter(Chat.id == chat_id).update({"last_message_at": datetime.utcnow()})
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_chat_history(
        self, chat_id: int, current_user: User, before_id: Optional[int] = None, limit: int = 50
    ) -> list[ChatMessage]:
        """Get paginated message history for a chat (X1-010)."""
        self._get_chat_with_permission(chat_id, current_user)

        query = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.chat_id == chat_id, ChatMessage.deleted_at.is_(None))
            .options(joinedload(ChatMessage.sender))
        )
        if before_id:
            query = query.filter(ChatMessage.id < before_id)

        return query.order_by(ChatMessage.created_at.desc()).limit(min(limit, 100)).all()

    # ------------------------------------------------------------------
    # Chat listing & details
    # ------------------------------------------------------------------

    def get_user_chats(self, user: User) -> list[dict]:
        """List user's chats with last message preview and unread count (X1-011)."""
        # Get all chats where user is a participant
        participations = (
            self.db.query(ChatParticipant)
            .filter(ChatParticipant.user_id == user.id)
            .options(joinedload(ChatParticipant.chat))
            .all()
        )

        results = []
        for p in participations:
            chat = p.chat

            # Last message
            last_msg = (
                self.db.query(ChatMessage)
                .filter(ChatMessage.chat_id == chat.id, ChatMessage.deleted_at.is_(None))
                .order_by(ChatMessage.created_at.desc())
                .first()
            )

            # Unread count
            unread = 0
            if p.last_read_at:
                unread = (
                    self.db.query(func.count(ChatMessage.id))
                    .filter(
                        ChatMessage.chat_id == chat.id,
                        ChatMessage.created_at > p.last_read_at,
                        ChatMessage.sender_id != user.id,
                        ChatMessage.deleted_at.is_(None),
                    )
                    .scalar()
                ) or 0
            elif last_msg:
                unread = (
                    self.db.query(func.count(ChatMessage.id))
                    .filter(
                        ChatMessage.chat_id == chat.id,
                        ChatMessage.sender_id != user.id,
                        ChatMessage.deleted_at.is_(None),
                    )
                    .scalar()
                ) or 0

            # For direct chats, get the other participant's name
            display_name = chat.name
            if chat.type == ChatType.DIRECT:
                other = (
                    self.db.query(ChatParticipant)
                    .options(joinedload(ChatParticipant.user))
                    .filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id != user.id)
                    .first()
                )
                display_name = other.user.full_name if other and other.user else "Unknown"

            results.append({
                "chat": chat,
                "display_name": display_name,
                "last_message": last_msg,
                "unread_count": unread,
                "is_muted": p.is_muted,
            })

        # Sort by last activity
        results.sort(key=lambda r: r["chat"].last_message_at or r["chat"].created_at, reverse=True)
        return results

    def get_chat(self, chat_id: int, current_user: User) -> Chat:
        """Get chat details with participants (X1-013)."""
        return self._get_chat_with_permission(chat_id, current_user, load_participants=True)

    def delete_chat(self, chat_id: int, current_user: User) -> None:
        """Delete a chat (X1-018)."""
        chat = self._get_chat_with_permission(chat_id, current_user)

        if chat.type == ChatType.GROUP:
            # Only owner can delete group chats
            owner = self.db.query(ChatParticipant).filter_by(
                chat_id=chat_id, user_id=current_user.id, role=ChatParticipantRole.OWNER
            ).first()
            if not owner and current_user.role != UserRole.SYSTEM_ADMIN:
                raise HTTPException(status_code=403, detail="Only the group owner can delete this chat")

        self.db.delete(chat)
        self.db.commit()

    def mark_as_read(self, chat_id: int, current_user: User) -> None:
        """Mark chat as read up to latest message (X1-017)."""
        self._get_chat_with_permission(chat_id, current_user)
        self.db.query(ChatParticipant).filter_by(
            chat_id=chat_id, user_id=current_user.id
        ).update({"last_read_at": datetime.utcnow()})
        self.db.commit()

    def search_messages(
        self, chat_id: int, current_user: User, query: str, limit: int = 50
    ) -> list[ChatMessage]:
        """Search messages in a chat by content (X1-043)."""
        self._get_chat_with_permission(chat_id, current_user)
        pattern = f"%{query}%"
        return (
            self.db.query(ChatMessage)
            .filter(
                ChatMessage.chat_id == chat_id,
                ChatMessage.deleted_at.is_(None),
                ChatMessage.content.ilike(pattern),
            )
            .options(joinedload(ChatMessage.sender))
            .order_by(ChatMessage.created_at.desc())
            .limit(min(limit, 100))
            .all()
        )

    def search_all_messages(
        self, current_user: User, query: str, limit: int = 50
    ) -> list[ChatMessage]:
        """Search messages across all chats the user participates in."""
        # Get all chat IDs this user participates in
        chat_ids = [
            row[0] for row in
            self.db.query(ChatParticipant.chat_id)
            .filter(ChatParticipant.user_id == current_user.id)
            .all()
        ]
        if not chat_ids:
            return []
        pattern = f"%{query}%"
        return (
            self.db.query(ChatMessage)
            .filter(
                ChatMessage.chat_id.in_(chat_ids),
                ChatMessage.deleted_at.is_(None),
                ChatMessage.content.ilike(pattern),
            )
            .options(joinedload(ChatMessage.sender))
            .order_by(ChatMessage.created_at.desc())
            .limit(min(limit, 100))
            .all()
        )

    def update_chat(self, chat_id: int, current_user: User, name: str) -> Chat:
        """Rename a group chat (X1-045)."""
        chat = self._get_chat_with_permission(chat_id, current_user, require_admin=True)
        if chat.type != ChatType.GROUP:
            raise HTTPException(status_code=400, detail="Cannot rename direct chats")
        old_name = chat.name
        chat.name = name.strip()
        self.db.add(ChatMessage(
            chat_id=chat_id,
            sender_id=current_user.id,
            content=f'{current_user.full_name} renamed the group from "{old_name}" to "{name.strip()}"',
            message_type=ChatMessageType.SYSTEM,
        ))
        self.db.commit()
        self.db.refresh(chat)
        return chat

    def toggle_mute(self, chat_id: int, current_user: User) -> bool:
        """Toggle mute status for a chat participant (X1-025)."""
        self._get_chat_with_permission(chat_id, current_user)
        participant = self.db.query(ChatParticipant).filter_by(
            chat_id=chat_id, user_id=current_user.id
        ).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Not a participant")
        participant.is_muted = not participant.is_muted
        self.db.commit()
        return participant.is_muted

    def update_participant_role(
        self, chat_id: int, current_user: User, target_user_id: int, new_role: ChatParticipantRole
    ) -> ChatParticipant:
        """Change a participant's role (X1-046)."""
        chat = self._get_chat_with_permission(chat_id, current_user, require_admin=True)
        if chat.type != ChatType.GROUP:
            raise HTTPException(status_code=400, detail="Cannot change roles in direct chats")

        participant = self.db.query(ChatParticipant).filter_by(
            chat_id=chat_id, user_id=target_user_id
        ).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        if participant.role == ChatParticipantRole.OWNER:
            raise HTTPException(status_code=400, detail="Cannot change the owner's role")
        if new_role == ChatParticipantRole.OWNER:
            raise HTTPException(status_code=400, detail="Cannot transfer ownership")

        participant.role = new_role
        target = self.db.query(User).filter(User.id == target_user_id).first()
        self.db.add(ChatMessage(
            chat_id=chat_id,
            sender_id=current_user.id,
            content=f'{current_user.full_name} changed {target.full_name if target else "a user"}\'s role to {new_role.value}',
            message_type=ChatMessageType.SYSTEM,
        ))
        self.db.commit()
        self.db.refresh(participant)
        return participant

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_chat_with_permission(
        self, chat_id: int, user: User, require_admin: bool = False, load_participants: bool = False
    ) -> Chat:
        """Validate chat access with tenant isolation (X1-009)."""
        query = self.db.query(Chat).filter(Chat.id == chat_id)
        if load_participants:
            query = query.options(joinedload(Chat.participants).joinedload(ChatParticipant.user))
        chat = query.first()

        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # Participation check — being a participant grants access regardless of tenant
        participant = self.db.query(ChatParticipant).filter_by(
            chat_id=chat_id, user_id=user.id
        ).first()
        if not participant and user.role != UserRole.SYSTEM_ADMIN:
            # Tenant isolation — non-participants can only see chats in their tenant
            if chat.tenant_id != user.tenant_id:
                raise HTTPException(status_code=404, detail="Chat not found")
            raise HTTPException(status_code=403, detail="You are not a participant in this chat")

        if require_admin and participant:
            if participant.role not in (ChatParticipantRole.OWNER, ChatParticipantRole.ADMIN):
                if user.role != UserRole.SYSTEM_ADMIN:
                    raise HTTPException(status_code=403, detail="Only chat owner/admin can perform this action")

        return chat
