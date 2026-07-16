"""add job application decisions

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_application_decisions",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("user_profile_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "user_profile_id", name="uq_job_application_decisions_job_user"),
    )
    op.create_index("ix_job_application_decisions_job_id", "job_application_decisions", ["job_id"])
    op.create_index("ix_job_application_decisions_user_profile_id", "job_application_decisions", ["user_profile_id"])
    op.create_index("ix_job_application_decisions_status", "job_application_decisions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_job_application_decisions_status", table_name="job_application_decisions")
    op.drop_index("ix_job_application_decisions_user_profile_id", table_name="job_application_decisions")
    op.drop_index("ix_job_application_decisions_job_id", table_name="job_application_decisions")
    op.drop_table("job_application_decisions")
