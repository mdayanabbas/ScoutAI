"""add application prep fields

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("job_application_decisions", sa.Column("priority", sa.String(length=16), nullable=True))
    op.add_column("job_application_decisions", sa.Column("fit_summary", sa.Text(), nullable=True))
    op.add_column("job_application_decisions", sa.Column("concerns", sa.JSON(), nullable=True))
    op.add_column("job_application_decisions", sa.Column("next_action", sa.Text(), nullable=True))
    op.add_column("job_application_decisions", sa.Column("next_action_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_application_decisions", sa.Column("source_snapshot", sa.JSON(), nullable=True))
    op.add_column("job_application_decisions", sa.Column("match_snapshot", sa.JSON(), nullable=True))
    op.add_column("job_application_decisions", sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_application_decisions", sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_application_decisions", sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_application_decisions", sa.Column("last_status_changed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("job_application_decisions", "last_status_changed_at")
    op.drop_column("job_application_decisions", "skipped_at")
    op.drop_column("job_application_decisions", "applied_at")
    op.drop_column("job_application_decisions", "saved_at")
    op.drop_column("job_application_decisions", "match_snapshot")
    op.drop_column("job_application_decisions", "source_snapshot")
    op.drop_column("job_application_decisions", "next_action_due_at")
    op.drop_column("job_application_decisions", "next_action")
    op.drop_column("job_application_decisions", "concerns")
    op.drop_column("job_application_decisions", "fit_summary")
    op.drop_column("job_application_decisions", "priority")
