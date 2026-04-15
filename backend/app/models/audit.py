"""Audit, analytics, and operational ledger models."""

from app.models._shared import (
    AnalyticsBase,
    Base,
    Column,
    DateTime,
    Index,
    Integer,
    SQLEnum,
    String,
    Text,
    UniqueConstraint,
    datetime,
)
from app.models.enums import ActionType, AudienceEventType


class DomainEventOutbox(AnalyticsBase):
    """Persisted domain events for reliable side-effect delivery."""

    __tablename__ = "domain_event_outbox"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(120), nullable=False, index=True)
    event_key = Column(String(255), nullable=True, unique=True, index=True)
    payload_json = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    next_attempt_at = Column(DateTime, nullable=True, index=True)
    last_error = Column(Text, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class IdempotencyKeyRecord(Base):
    """Persisted request/response fingerprints for idempotent retries."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            "method",
            "path",
            "user_scope",
            name="uq_idempotency_scope",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    user_scope = Column(String(64), nullable=False)
    user_id = Column(Integer, nullable=True, index=True)
    request_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="processing", index=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_content_type = Column(String(120), nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditLog(AnalyticsBase):
    """Audit log model."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    document_id = Column(Integer, nullable=True, index=True)
    action = Column(SQLEnum(ActionType), nullable=False, index=True)
    audience_event_type = Column(SQLEnum(AudienceEventType), nullable=True, index=True)
    details = Column(Text, nullable=True)
    assignment_diff = Column(Text, nullable=True)
    signature_key_id = Column(String(32), nullable=True)
    signature = Column(String(128), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class SecurityEvent(AnalyticsBase):
    """Security event log for account anomalies and security actions."""

    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class SearchAnalytics(AnalyticsBase):
    """Search analytics - tracks queries, results, and clicks."""

    __tablename__ = "search_analytics"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(500), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    results_count = Column(Integer, nullable=False, default=0)
    clicked_document_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class NpsSurvey(AnalyticsBase):
    """Net Promoter Score survey responses."""

    __tablename__ = "nps_surveys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    tenant_id = Column(Integer, nullable=True)
    score = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OnboardingEvent(AnalyticsBase):
    """Funnel event for onboarding analytics."""

    __tablename__ = "onboarding_events"
    __table_args__ = (Index("ix_onboarding_user_step", "user_id", "step"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    step = Column(String(50), nullable=False)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ActivationMilestone(AnalyticsBase):
    """Per-user milestone tracking."""

    __tablename__ = "activation_milestones"
    __table_args__ = (UniqueConstraint("user_id", "milestone", name="uq_user_milestone"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    milestone = Column(String(50), nullable=False)
    achieved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
