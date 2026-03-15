"""Wave Z — Admin operations models (impersonation, action queue, quotas, features, domains, maintenance)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260314_0023"
down_revision = "20260314_0022"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Z-001: Impersonation sessions
    if not _table_exists(inspector, "impersonation_sessions"):
        op.create_table(
            "impersonation_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("target_tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("session_token", sa.String(128), unique=True, nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        )
        op.create_index("ix_impersonation_sessions_admin_user_id", "impersonation_sessions", ["admin_user_id"])
        op.create_index("ix_impersonation_sessions_target_tenant_id", "impersonation_sessions", ["target_tenant_id"])
        op.create_index("ix_impersonation_sessions_session_token", "impersonation_sessions", ["session_token"])
        op.create_index("ix_impersonation_sessions_is_active", "impersonation_sessions", ["is_active"])

    # Z-002: Admin action queue
    if not _table_exists(inspector, "admin_actions"):
        op.create_table(
            "admin_actions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("action_type", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), default="pending", nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("review_comment", sa.Text(), nullable=True),
            sa.Column("target_tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_admin_actions_action_type", "admin_actions", ["action_type"])
        op.create_index("ix_admin_actions_status", "admin_actions", ["status"])
        op.create_index("ix_admin_actions_requested_by", "admin_actions", ["requested_by"])
        op.create_index("ix_admin_actions_target_tenant_id", "admin_actions", ["target_tenant_id"])

    # Z-012: Tenant quotas
    if not _table_exists(inspector, "tenant_quotas"):
        op.create_table(
            "tenant_quotas",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("max_users", sa.Integer(), nullable=True),
            sa.Column("max_documents", sa.Integer(), nullable=True),
            sa.Column("max_storage_mb", sa.Integer(), nullable=True),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_tenant_quotas_tenant_id", "tenant_quotas", ["tenant_id"])
        op.create_unique_constraint("uq_tenant_quota", "tenant_quotas", ["tenant_id"])

    # Z-005: Feature flags
    if not _table_exists(inspector, "feature_flags"):
        op.create_table(
            "feature_flags",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("feature_key", sa.String(100), nullable=False),
            sa.Column("enabled", sa.Boolean(), default=False, nullable=False),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_feature_flags_tenant_id", "feature_flags", ["tenant_id"])
        op.create_index("ix_feature_flags_feature_key", "feature_flags", ["feature_key"])
        op.create_unique_constraint("uq_tenant_feature", "feature_flags", ["tenant_id", "feature_key"])

    # Z-010: Domain verification
    if not _table_exists(inspector, "domain_verifications"):
        op.create_table(
            "domain_verifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("domain", sa.String(255), nullable=False),
            sa.Column("verification_token", sa.String(128), nullable=False),
            sa.Column("status", sa.String(20), default="pending", nullable=False),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_domain_verifications_tenant_id", "domain_verifications", ["tenant_id"])
        op.create_index("ix_domain_verifications_domain", "domain_verifications", ["domain"])
        op.create_index("ix_domain_verifications_status", "domain_verifications", ["status"])

    # Z-018: Maintenance windows
    if not _table_exists(inspector, "maintenance_windows"):
        op.create_table(
            "maintenance_windows",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("scheduled_start", sa.DateTime(), nullable=False),
            sa.Column("scheduled_end", sa.DateTime(), nullable=False),
            sa.Column("is_read_only", sa.Boolean(), default=True, nullable=False),
            sa.Column("is_active", sa.Boolean(), default=False, nullable=False),
            sa.Column("notification_sent", sa.Boolean(), default=False, nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_maintenance_windows_scheduled_start", "maintenance_windows", ["scheduled_start"])
        op.create_index("ix_maintenance_windows_is_active", "maintenance_windows", ["is_active"])


def downgrade() -> None:
    op.drop_table("maintenance_windows")
    op.drop_table("domain_verifications")
    op.drop_table("feature_flags")
    op.drop_table("tenant_quotas")
    op.drop_table("admin_actions")
    op.drop_table("impersonation_sessions")
