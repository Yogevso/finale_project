"""Add review assignment rules and structured feedback storage.

Revision ID: 20260419_0001
Revises: 20260328_0003
Create Date: 2026-04-19
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op


revision = "20260419_0001"
down_revision = "20260328_0003"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _foreign_key_exists(
    inspector: sa.Inspector,
    table_name: str,
    constrained_columns: Iterable[str],
    referred_table: str,
) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    constrained = list(constrained_columns)
    for foreign_key in inspector.get_foreign_keys(table_name):
        if foreign_key.get("referred_table") != referred_table:
            continue
        if list(foreign_key.get("constrained_columns") or []) == constrained:
            return True
    return False


def _find_foreign_key_name(
    inspector: sa.Inspector,
    table_name: str,
    constrained_columns: Iterable[str],
    referred_table: str,
) -> str | None:
    if not _table_exists(inspector, table_name):
        return None
    constrained = list(constrained_columns)
    for foreign_key in inspector.get_foreign_keys(table_name):
        if foreign_key.get("referred_table") != referred_table:
            continue
        if list(foreign_key.get("constrained_columns") or []) == constrained:
            return foreign_key.get("name")
    return None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "review_requests") and not _column_exists(
        inspector, "review_requests", "review_feedback_json"
    ):
        with op.batch_alter_table("review_requests", schema=None) as batch_op:
            batch_op.add_column(sa.Column("review_feedback_json", sa.Text(), nullable=True))

    if _table_exists(inspector, "comments"):
        with op.batch_alter_table("comments", schema=None) as batch_op:
            if not _column_exists(inspector, "comments", "review_id"):
                batch_op.add_column(sa.Column("review_id", sa.Integer(), nullable=True))
            if not _foreign_key_exists(inspector, "comments", ["review_id"], "review_requests"):
                batch_op.create_foreign_key(
                    "fk_comments_review_id_review_requests",
                    "review_requests",
                    ["review_id"],
                    ["id"],
                )

        inspector = sa.inspect(bind)
        if not _index_exists(inspector, "comments", "ix_comments_review_id"):
            op.create_index("ix_comments_review_id", "comments", ["review_id"], unique=False)

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "review_ownership_rules"):
        op.create_table(
            "review_ownership_rules",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(length=100), nullable=True),
            sa.Column("platform", sa.String(length=100), nullable=True),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("reviewer_id", sa.Integer(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "review_ownership_rules"):
        if not _index_exists(inspector, "review_ownership_rules", "ix_review_ownership_rules_tenant_id"):
            op.create_index(
                "ix_review_ownership_rules_tenant_id",
                "review_ownership_rules",
                ["tenant_id"],
                unique=False,
            )
        if not _index_exists(inspector, "review_ownership_rules", "ix_review_ownership_rules_category"):
            op.create_index(
                "ix_review_ownership_rules_category",
                "review_ownership_rules",
                ["category"],
                unique=False,
            )
        if not _index_exists(inspector, "review_ownership_rules", "ix_review_ownership_rules_platform"):
            op.create_index(
                "ix_review_ownership_rules_platform",
                "review_ownership_rules",
                ["platform"],
                unique=False,
            )
        if not _index_exists(inspector, "review_ownership_rules", "ix_review_ownership_rules_company_id"):
            op.create_index(
                "ix_review_ownership_rules_company_id",
                "review_ownership_rules",
                ["company_id"],
                unique=False,
            )
        if not _index_exists(inspector, "review_ownership_rules", "ix_review_ownership_rules_reviewer_id"):
            op.create_index(
                "ix_review_ownership_rules_reviewer_id",
                "review_ownership_rules",
                ["reviewer_id"],
                unique=False,
            )
        if not _index_exists(inspector, "review_ownership_rules", "ix_review_ownership_rules_is_active"):
            op.create_index(
                "ix_review_ownership_rules_is_active",
                "review_ownership_rules",
                ["is_active"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "review_request_reviewers"):
        op.create_table(
            "review_request_reviewers",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("review_id", sa.Integer(), nullable=False),
            sa.Column("reviewer_id", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
            sa.Column("rule_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["review_id"], ["review_requests.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["rule_id"], ["review_ownership_rules.id"]),
            sa.UniqueConstraint(
                "review_id",
                "reviewer_id",
                name="uq_review_request_reviewers_review_reviewer",
            ),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "review_request_reviewers"):
        if not _index_exists(inspector, "review_request_reviewers", "ix_review_request_reviewers_review_id"):
            op.create_index(
                "ix_review_request_reviewers_review_id",
                "review_request_reviewers",
                ["review_id"],
                unique=False,
            )
        if not _index_exists(inspector, "review_request_reviewers", "ix_review_request_reviewers_reviewer_id"):
            op.create_index(
                "ix_review_request_reviewers_reviewer_id",
                "review_request_reviewers",
                ["reviewer_id"],
                unique=False,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "review_request_reviewers"):
        if _index_exists(inspector, "review_request_reviewers", "ix_review_request_reviewers_reviewer_id"):
            op.drop_index(
                "ix_review_request_reviewers_reviewer_id",
                table_name="review_request_reviewers",
            )
        if _index_exists(inspector, "review_request_reviewers", "ix_review_request_reviewers_review_id"):
            op.drop_index(
                "ix_review_request_reviewers_review_id",
                table_name="review_request_reviewers",
            )
        op.drop_table("review_request_reviewers")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "review_ownership_rules"):
        for index_name in [
            "ix_review_ownership_rules_is_active",
            "ix_review_ownership_rules_reviewer_id",
            "ix_review_ownership_rules_company_id",
            "ix_review_ownership_rules_platform",
            "ix_review_ownership_rules_category",
            "ix_review_ownership_rules_tenant_id",
        ]:
            if _index_exists(inspector, "review_ownership_rules", index_name):
                op.drop_index(index_name, table_name="review_ownership_rules")
        op.drop_table("review_ownership_rules")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "comments"):
        if _index_exists(inspector, "comments", "ix_comments_review_id"):
            op.drop_index("ix_comments_review_id", table_name="comments")
        if _column_exists(inspector, "comments", "review_id"):
            fk_name = _find_foreign_key_name(
                inspector,
                "comments",
                ["review_id"],
                "review_requests",
            )
            with op.batch_alter_table("comments", schema=None) as batch_op:
                if fk_name:
                    batch_op.drop_constraint(
                        fk_name,
                        type_="foreignkey",
                    )
                batch_op.drop_column("review_id")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "review_requests") and _column_exists(
        inspector, "review_requests", "review_feedback_json"
    ):
        with op.batch_alter_table("review_requests", schema=None) as batch_op:
            batch_op.drop_column("review_feedback_json")
