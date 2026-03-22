"""chat_baseline

Baseline migration for the chat database.
Tables: notifications, chats, chat_participants, chat_messages,
        collaboration_sessions, collaboration_activities,
        collaboration_snapshots, assistant_conversations,
        assistant_messages, assistant_uploaded_files.

These tables already exist in the shared DB; this migration stamps the
initial revision so future autogenerate diffs work correctly.
"""

# revision identifiers, used by Alembic.
revision = 'c0a1b2c3d4e5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
