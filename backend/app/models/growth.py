"""Experimentation, growth, webhook, and API-key models."""

from app.models._shared import (
    AnalyticsBase,
    Base,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SQLEnum,
    String,
    Text,
    UniqueConstraint,
    datetime,
    relationship,
)
from app.models.enums import ExperimentStatus


class Experiment(Base):
    """A/B experiment definition."""

    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    feature_flag_key = Column(String(100), nullable=True, index=True)
    status = Column(SQLEnum(ExperimentStatus), default=ExperimentStatus.DRAFT, nullable=False, index=True)
    variants = Column(Text, nullable=False, default='["control","treatment"]')
    traffic_percentage = Column(Integer, default=100, nullable=False)
    primary_metric = Column(String(100), nullable=True)
    guardrail_metrics = Column(Text, nullable=True)
    guardrail_threshold = Column(Integer, default=10, nullable=False)
    winner_variant = Column(String(100), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    creator = relationship("User")
    assignments = relationship("ExperimentAssignment", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentAssignment(Base):
    """Deterministic user-to-variant assignment for an experiment."""

    __tablename__ = "experiment_assignments"
    __table_args__ = (
        UniqueConstraint("experiment_id", "user_id", name="uq_experiment_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    variant = Column(String(100), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    experiment = relationship("Experiment", back_populates="assignments")
    user = relationship("User")


class ExperimentMetricSnapshot(Base):
    """Point-in-time metric readings per variant."""

    __tablename__ = "experiment_metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    variant = Column(String(100), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(String(50), nullable=False)
    sample_size = Column(Integer, default=0, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class WebhookRegistration(Base):
    """Registered webhook URLs for domain events."""

    __tablename__ = "webhook_registrations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False)
    event_types = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    creator = relationship("User")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    """Delivery log for a webhook invocation."""

    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhook_registrations.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(120), nullable=False)
    payload_json = Column(Text, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=1, nullable=False)
    delivered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    webhook = relationship("WebhookRegistration", back_populates="deliveries")


class ApiKey(Base):
    """Developer API keys for programmatic access."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    key_prefix = Column(String(8), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    scopes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    user = relationship("User")
