"""Collaboration, chat, and real-time communication models."""

from app.models._shared import (
    Boolean,
    ChatBase,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SQLEnum,
    String,
    Text,
    UniqueConstraint,
    datetime,
    relationship,
)
from app.models.enums import (
    ChatMessageType,
    ChatParticipantRole,
    ChatType,
    CollaborationActivityType,
    SnapshotType,
)


class CollaborationSession(ChatBase):
    """Tracks collaboration sessions for activity feed and analytics."""

    __tablename__ = "collaboration_sessions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    edits_count = Column(Integer, default=0, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CollaborationActivity(ChatBase):
    """Individual collaboration activities for the activity feed."""

    __tablename__ = "collaboration_activities"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    activity_type = Column(SQLEnum(CollaborationActivityType), nullable=False, index=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class CollaborationSnapshot(ChatBase):
    """Point-in-time snapshot of collaborative document state."""

    __tablename__ = "collaboration_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    snapshot_type = Column(SQLEnum(SnapshotType), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    yjs_state = Column(LargeBinary, nullable=False)
    html_content = Column(Text, nullable=True)
    state_size = Column(Integer, nullable=False)
    created_by = Column(Integer, nullable=True)
    session_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_pinned = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=True)


class Chat(ChatBase):
    """Internal chat - direct messages or group conversations."""

    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(ChatType), nullable=False)
    name = Column(String(255), nullable=True)
    document_id = Column(Integer, nullable=True, index=True)
    created_by = Column(Integer, nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    last_message_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    participants = relationship("ChatParticipant", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")


class ChatParticipant(ChatBase):
    """Participant in a chat."""

    __tablename__ = "chat_participants"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_participant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(SQLEnum(ChatParticipantRole), default=ChatParticipantRole.MEMBER, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_read_at = Column(DateTime, nullable=True)
    is_muted = Column(Boolean, default=False, nullable=False)

    chat = relationship("Chat", back_populates="participants")


class ChatMessage(ChatBase):
    """Message in a chat."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_chat_created", "chat_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(ChatMessageType), default=ChatMessageType.TEXT, nullable=False)
    context_json = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_mime_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    chat = relationship("Chat", back_populates="messages")
