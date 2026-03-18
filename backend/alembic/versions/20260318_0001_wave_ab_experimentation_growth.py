"""Wave AB — Experimentation, Webhooks, API Keys, Onboarding Analytics

Revision ID: wave_ab_001
Revises: 20260317_0037
Create Date: 2026-03-18
"""

from alembic import op
import sqlalchemy as sa

revision = "wave_ab_001"
down_revision = "20260317_0037"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table_name},
    )
    return result.scalar() is not None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c["name"] for c in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    # -- Experiments --
    if not _table_exists("experiments"):
        op.create_table(
            "experiments",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("feature_flag_key", sa.String(100), nullable=True, index=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft", index=True),
            sa.Column("variants", sa.Text, nullable=False, server_default='["control","treatment"]'),
            sa.Column("traffic_percentage", sa.Integer, nullable=False, server_default="100"),
            sa.Column("primary_metric", sa.String(100), nullable=True),
            sa.Column("guardrail_metrics", sa.Text, nullable=True),
            sa.Column("guardrail_threshold", sa.Integer, nullable=False, server_default="10"),
            sa.Column("winner_variant", sa.String(100), nullable=True),
            sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True),
            sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("started_at", sa.DateTime, nullable=True),
            sa.Column("ended_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )

    if not _table_exists("experiment_assignments"):
        op.create_table(
            "experiment_assignments",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("experiment_id", sa.Integer, sa.ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("variant", sa.String(100), nullable=False),
            sa.Column("assigned_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("experiment_id", "user_id", name="uq_experiment_user"),
        )

    if not _table_exists("experiment_metric_snapshots"):
        op.create_table(
            "experiment_metric_snapshots",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("experiment_id", sa.Integer, sa.ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("variant", sa.String(100), nullable=False),
            sa.Column("metric_name", sa.String(100), nullable=False),
            sa.Column("metric_value", sa.String(50), nullable=False),
            sa.Column("sample_size", sa.Integer, nullable=False, server_default="0"),
            sa.Column("recorded_at", sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        )

    # -- Onboarding & Activation --
    if not _table_exists("onboarding_events"):
        op.create_table(
            "onboarding_events",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("step", sa.String(50), nullable=False),
            sa.Column("occurred_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_onboarding_user_step", "onboarding_events", ["user_id", "step"])

    if not _table_exists("activation_milestones"):
        op.create_table(
            "activation_milestones",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("milestone", sa.String(50), nullable=False),
            sa.Column("achieved_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "milestone", name="uq_user_milestone"),
        )

    # -- Webhooks --
    if not _table_exists("webhook_registrations"):
        op.create_table(
            "webhook_registrations",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("url", sa.String(2048), nullable=False),
            sa.Column("secret", sa.String(255), nullable=False),
            sa.Column("event_types", sa.Text, nullable=False),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
            sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )

    if not _table_exists("webhook_deliveries"):
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("webhook_id", sa.Integer, sa.ForeignKey("webhook_registrations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("event_type", sa.String(120), nullable=False),
            sa.Column("payload_json", sa.Text, nullable=False),
            sa.Column("response_status", sa.Integer, nullable=True),
            sa.Column("response_body", sa.Text, nullable=True),
            sa.Column("success", sa.Boolean, nullable=False, server_default="0"),
            sa.Column("attempts", sa.Integer, nullable=False, server_default="1"),
            sa.Column("delivered_at", sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        )

    # -- API Keys --
    if not _table_exists("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("key_prefix", sa.String(8), nullable=False),
            sa.Column("key_hash", sa.String(255), nullable=False, unique=True),
            sa.Column("scopes", sa.Text, nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
            sa.Column("last_used_at", sa.DateTime, nullable=True),
            sa.Column("expires_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )

    # -- Feature flag targeting columns (AB-001) --
    if _table_exists("feature_flags") and not _column_exists("feature_flags", "rollout_percentage"):
        op.add_column("feature_flags", sa.Column("rollout_percentage", sa.Integer, nullable=True, server_default="100"))
    if _table_exists("feature_flags") and not _column_exists("feature_flags", "target_tenant_ids"):
        op.add_column("feature_flags", sa.Column("target_tenant_ids", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("feature_flags", "target_tenant_ids")
    op.drop_column("feature_flags", "rollout_percentage")
    op.drop_table("api_keys")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_registrations")
    op.drop_table("activation_milestones")
    op.drop_index("ix_onboarding_user_step", "onboarding_events")
    op.drop_table("onboarding_events")
    op.drop_table("experiment_metric_snapshots")
    op.drop_table("experiment_assignments")
    op.drop_table("experiments")
