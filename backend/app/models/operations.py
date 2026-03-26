"""Admin operations, tenant configuration, and GDPR request models."""

from app.models._shared import (
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
from app.models.enums import (
    AdminActionStatus,
    AdminActionType,
    DataRequestStatus,
    DataRequestType,
    DomainVerificationStatus,
)


class ImpersonationSession(Base):
    """Tracks when a system admin is impersonating a tenant."""

    __tablename__ = "impersonation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    session_token = Column(String(128), unique=True, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    admin_user = relationship("User", foreign_keys=[admin_user_id])
    target_tenant = relationship("Tenant")


class AdminAction(Base):
    """Queued admin actions requiring second sysadmin approval."""

    __tablename__ = "admin_actions"

    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(SQLEnum(AdminActionType), nullable=False, index=True)
    status = Column(SQLEnum(AdminActionStatus), default=AdminActionStatus.PENDING, nullable=False, index=True)
    payload = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)
    target_tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)

    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    target_tenant = relationship("Tenant")


class TenantQuota(Base):
    """Configurable quotas per tenant."""

    __tablename__ = "tenant_quotas"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_quota"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    max_users = Column(Integer, nullable=True)
    max_documents = Column(Integer, nullable=True)
    max_storage_mb = Column(Integer, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", backref="quota")
    updater = relationship("User")


class FeatureFlag(Base):
    """Per-tenant feature flags with rollout targeting."""

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("tenant_id", "feature_key", name="uq_tenant_feature"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    feature_key = Column(String(100), nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    rollout_percentage = Column(Integer, nullable=True, default=100)
    target_tenant_ids = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    updater = relationship("User")


class DomainVerification(Base):
    """DNS domain verification for tenant ownership."""

    __tablename__ = "domain_verifications"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    verification_token = Column(String(128), nullable=False)
    status = Column(
        SQLEnum(DomainVerificationStatus),
        default=DomainVerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    tenant = relationship("Tenant")


class MaintenanceWindow(Base):
    """Scheduled maintenance windows with notification."""

    __tablename__ = "maintenance_windows"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_start = Column(DateTime, nullable=False, index=True)
    scheduled_end = Column(DateTime, nullable=False)
    is_read_only = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    notification_sent = Column(Boolean, default=False, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    creator = relationship("User")


class DataRequest(Base):
    """GDPR data export/deletion request."""

    __tablename__ = "data_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_type = Column(SQLEnum(DataRequestType), nullable=False, index=True)
    status = Column(SQLEnum(DataRequestStatus), default=DataRequestStatus.PENDING, nullable=False, index=True)
    reason = Column(Text, nullable=False)
    admin_comment = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    download_token = Column(String(128), nullable=True, unique=True)
    download_expires_at = Column(DateTime, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
