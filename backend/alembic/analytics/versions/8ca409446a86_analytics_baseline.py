"""analytics_baseline

Baseline migration for the analytics database.
Tables: audit_logs, security_events, search_analytics, nps_surveys,
        onboarding_events, activation_milestones, domain_event_outbox.

These tables already exist in the shared DB; this migration stamps the
initial revision so future autogenerate diffs work correctly.
"""

# revision identifiers, used by Alembic.
revision = '8ca409446a86'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
