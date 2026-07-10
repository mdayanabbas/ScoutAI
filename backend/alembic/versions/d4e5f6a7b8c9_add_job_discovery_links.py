"""add job discovery links

Revision ID: d4e5f6a7b8c9
Revises: c7a4e91d5f20
Create Date: 2026-07-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c7a4e91d5f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_discovery_links",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("discovery_candidate_id", sa.String(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["discovery_candidate_id"], ["discovery_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "discovery_candidate_id", name="uq_job_discovery_links_job_candidate"),
        sa.UniqueConstraint("discovery_candidate_id", name="uq_job_discovery_links_candidate"),
    )
    op.create_index("ix_job_discovery_links_job_id", "job_discovery_links", ["job_id"])
    op.create_index(
        "ix_job_discovery_links_discovery_candidate_id",
        "job_discovery_links",
        ["discovery_candidate_id"],
    )
    op.create_index(
        "ix_job_discovery_links_created_at",
        "job_discovery_links",
        ["created_at"],
    )
    op.execute(
        """
        INSERT INTO job_discovery_links (id, job_id, discovery_candidate_id, created_at)
        SELECT md5(id || ':' || discovery_candidate_id), id, discovery_candidate_id, COALESCE(created_at, now())
        FROM jobs
        WHERE discovery_candidate_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_job_discovery_links_created_at", table_name="job_discovery_links")
    op.drop_index("ix_job_discovery_links_discovery_candidate_id", table_name="job_discovery_links")
    op.drop_index("ix_job_discovery_links_job_id", table_name="job_discovery_links")
    op.drop_table("job_discovery_links")
