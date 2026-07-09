"""add discovery candidate id to jobs

Revision ID: c7a4e91d5f20
Revises: b2f8d4e1a6c3
Create Date: 2026-07-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7a4e91d5f20"
down_revision: Union[str, None] = "b2f8d4e1a6c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("discovery_candidate_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_jobs_discovery_candidate_id_discovery_candidates",
        "jobs",
        "discovery_candidates",
        ["discovery_candidate_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_jobs_discovery_candidate_id"),
        "jobs",
        ["discovery_candidate_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_discovery_candidate_id"), table_name="jobs")
    op.drop_constraint(
        "fk_jobs_discovery_candidate_id_discovery_candidates",
        "jobs",
        type_="foreignkey",
    )
    op.drop_column("jobs", "discovery_candidate_id")
