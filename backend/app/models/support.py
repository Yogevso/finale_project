"""Support ticket and customer-support models."""

from app.models._shared import (
    Base,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SQLEnum,
    String,
    Text,
    UniqueConstraint,
    datetime,
    relationship,
)
from app.models.enums import SupportTicketPriority, SupportTicketStatus


class SupportTicket(Base):
    """Customer support ticket - created from feedback or directly."""

    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    status = Column(
        SQLEnum(SupportTicketStatus), default=SupportTicketStatus.OPEN, nullable=False, index=True
    )
    priority = Column(
        SQLEnum(SupportTicketPriority),
        default=SupportTicketPriority.NORMAL,
        nullable=False,
        index=True,
    )
    category = Column(String(100), nullable=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedbacks.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    customer = relationship("User", foreign_keys=[customer_id])
    tenant = relationship("Tenant")
    feedback = relationship("Feedback")
    messages = relationship(
        "SupportTicketMessage", back_populates="ticket", cascade="all, delete-orphan"
    )
    assignments = relationship(
        "SupportTicketAssignment", back_populates="ticket", cascade="all, delete-orphan"
    )


class SupportTicketMessage(Base):
    """Message in a support ticket conversation."""

    __tablename__ = "support_ticket_messages"
    __table_args__ = (Index("ix_support_messages_ticket_created", "ticket_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(
        Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sender_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, default=False, nullable=False)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_mime_type = Column(String(100), nullable=True)
    file_storage_key = Column(String(500), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    ticket = relationship("SupportTicket", back_populates="messages")
    sender = relationship("User")


class SupportTicketAssignment(Base):
    """Agent assignment to a support ticket."""

    __tablename__ = "support_ticket_assignments"
    __table_args__ = (UniqueConstraint("ticket_id", "agent_id", name="uq_ticket_assignment"),)

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(
        Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)

    ticket = relationship("SupportTicket", back_populates="assignments")
    agent = relationship("User")


class CannedResponse(Base):
    """Reusable canned response template for support agents."""

    __tablename__ = "canned_responses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    creator = relationship("User")
    tenant = relationship("Tenant")
