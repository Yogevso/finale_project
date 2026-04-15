"""AI assistant conversation and upload models."""

from app.models._shared import (
    Boolean,
    ChatBase,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    datetime,
    relationship,
)


class AssistantConversation(ChatBase):
    """A conversation between a user and the AI assistant."""

    __tablename__ = "assistant_conversations"
    __table_args__ = (Index("ix_assistant_conv_user_created", "user_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    tenant_id = Column(Integer, nullable=True)
    title = Column(String(255), default="New Chat", nullable=False)
    summary = Column(Text, nullable=True)
    context_document_ids = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    messages = relationship(
        "AssistantMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at",
    )


class AssistantMessage(ChatBase):
    """A single message within an assistant conversation."""

    __tablename__ = "assistant_messages"
    __table_args__ = (Index("ix_assistant_msg_conv_created", "conversation_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=True)
    tool_calls = Column(Text, nullable=True)
    tool_call_id = Column(String(100), nullable=True)
    tool_name = Column(String(100), nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("AssistantConversation", back_populates="messages")


class AssistantUploadedFile(ChatBase):
    """A file uploaded by a user in the assistant chat."""

    __tablename__ = "assistant_uploaded_files"
    __table_args__ = (Index("ix_assistant_file_user", "user_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    conversation_id = Column(
        Integer,
        ForeignKey("assistant_conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("AssistantConversation")
