"""add ashby board expansion links

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_job_discovery_links_candidate",
        "job_discovery_links",
        type_="unique",
    )
    op.create_table(
        "job_board_expansion_links",
        sa.Column("parent_job_id", sa.String(), nullable=False),
        sa.Column("child_job_id", sa.String(), nullable=False),
        sa.Column("discovery_candidate_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("parent_job_id <> child_job_id", name="ck_job_board_expansion_links_not_self"),
        sa.ForeignKeyConstraint(["child_job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["discovery_candidate_id"], ["discovery_candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_job_id", "child_job_id", name="uq_job_board_expansion_links_parent_child"),
    )
    op.create_index(
        "ix_job_board_expansion_links_parent_job_id",
        "job_board_expansion_links",
        ["parent_job_id"],
    )
    op.create_index(
        "ix_job_board_expansion_links_child_job_id",
        "job_board_expansion_links",
        ["child_job_id"],
    )
    op.create_index(
        "ix_job_board_expansion_links_discovery_candidate_id",
        "job_board_expansion_links",
        ["discovery_candidate_id"],
    )
    op.create_index(
        "ix_job_board_expansion_links_created_at",
        "job_board_expansion_links",
        ["created_at"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    duplicate = connection.execute(
        sa.text(
            """
            SELECT discovery_candidate_id
            FROM job_discovery_links
            GROUP BY discovery_candidate_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot restore uq_job_discovery_links_candidate while a candidate links to multiple jobs"
        )
    op.drop_index("ix_job_board_expansion_links_created_at", table_name="job_board_expansion_links")
    op.drop_index("ix_job_board_expansion_links_discovery_candidate_id", table_name="job_board_expansion_links")
    op.drop_index("ix_job_board_expansion_links_child_job_id", table_name="job_board_expansion_links")
    op.drop_index("ix_job_board_expansion_links_parent_job_id", table_name="job_board_expansion_links")
    op.drop_table("job_board_expansion_links")
    op.create_unique_constraint(
        "uq_job_discovery_links_candidate",
        "job_discovery_links",
        ["discovery_candidate_id"],
    )
