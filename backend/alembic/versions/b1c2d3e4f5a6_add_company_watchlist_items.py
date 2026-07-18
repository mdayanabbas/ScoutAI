"""add company watchlist items

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-07-17 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_watchlist_items",
        sa.Column("company_id", sa.String(), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("company_domain", sa.String(length=255), nullable=True),
        sa.Column("company_url", sa.Text(), nullable=True),
        sa.Column("normalized_company_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_domain", sa.String(length=255), nullable=True),
        sa.Column("watch_status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("interest_reason", sa.Text(), nullable=True),
        sa.Column("target_roles_json", sa.JSON(), nullable=True),
        sa.Column("preferred_locations_json", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=True),
        sa.Column("remote_interest", sa.String(length=32), nullable=False),
        sa.Column("junior_friendliness_signal", sa.String(length=16), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_job_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_company_watchlist_items_company_id", "company_watchlist_items", ["company_id"])
    op.create_index("ix_company_watchlist_items_normalized_company_name", "company_watchlist_items", ["normalized_company_name"])
    op.create_index("ix_company_watchlist_items_normalized_domain", "company_watchlist_items", ["normalized_domain"])
    op.create_index("ix_company_watchlist_items_watch_status", "company_watchlist_items", ["watch_status"])
    op.create_index("ix_company_watchlist_items_priority", "company_watchlist_items", ["priority"])
    op.create_index("ix_company_watchlist_items_created_at", "company_watchlist_items", ["created_at"])
    op.create_index("ix_company_watchlist_items_updated_at", "company_watchlist_items", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_company_watchlist_items_updated_at", table_name="company_watchlist_items")
    op.drop_index("ix_company_watchlist_items_created_at", table_name="company_watchlist_items")
    op.drop_index("ix_company_watchlist_items_priority", table_name="company_watchlist_items")
    op.drop_index("ix_company_watchlist_items_watch_status", table_name="company_watchlist_items")
    op.drop_index("ix_company_watchlist_items_normalized_domain", table_name="company_watchlist_items")
    op.drop_index("ix_company_watchlist_items_normalized_company_name", table_name="company_watchlist_items")
    op.drop_index("ix_company_watchlist_items_company_id", table_name="company_watchlist_items")
    op.drop_table("company_watchlist_items")

