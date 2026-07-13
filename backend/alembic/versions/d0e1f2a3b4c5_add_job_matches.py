"""add job matches

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_matches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("job_matching_profile_id", sa.String(), nullable=False),
        sa.Column("eligibility_status", sa.String(length=32), nullable=False),
        sa.Column("eligibility_reason", sa.String(length=500), nullable=True),
        sa.Column("remote_eligibility", sa.String(length=64), nullable=False),
        sa.Column("match_tier", sa.String(length=32), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("role_score", sa.Float(), nullable=False),
        sa.Column("seniority_score", sa.Float(), nullable=False),
        sa.Column("remote_score", sa.Float(), nullable=False),
        sa.Column("experience_score", sa.Float(), nullable=False),
        sa.Column("employment_type_score", sa.Float(), nullable=False),
        sa.Column("skills_score", sa.Float(), nullable=False),
        sa.Column("technology_score", sa.Float(), nullable=False),
        sa.Column("salary_score", sa.Float(), nullable=False),
        sa.Column("company_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("hard_filter_reasons_json", sa.JSON(), nullable=False),
        sa.Column("positive_signals_json", sa.JSON(), nullable=False),
        sa.Column("negative_signals_json", sa.JSON(), nullable=False),
        sa.Column("missing_information_json", sa.JSON(), nullable=False),
        sa.Column("score_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("scoring_version", sa.String(length=64), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_matching_profile_id"], ["job_matching_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "job_matching_profile_id", name="uq_job_matches_job_profile"),
    )
    op.create_index("ix_job_matches_job_id", "job_matches", ["job_id"])
    op.create_index("ix_job_matches_profile_id", "job_matches", ["job_matching_profile_id"])
    op.create_index("ix_job_matches_eligibility_status", "job_matches", ["eligibility_status"])
    op.create_index("ix_job_matches_remote_eligibility", "job_matches", ["remote_eligibility"])
    op.create_index("ix_job_matches_match_tier", "job_matches", ["match_tier"])
    op.create_index("ix_job_matches_total_score", "job_matches", ["total_score"])
    op.create_index("ix_job_matches_scored_at", "job_matches", ["scored_at"])
    op.create_index("ix_job_matches_profile_score", "job_matches", ["job_matching_profile_id", "total_score"])


def downgrade() -> None:
    op.drop_index("ix_job_matches_profile_score", table_name="job_matches")
    op.drop_index("ix_job_matches_scored_at", table_name="job_matches")
    op.drop_index("ix_job_matches_total_score", table_name="job_matches")
    op.drop_index("ix_job_matches_match_tier", table_name="job_matches")
    op.drop_index("ix_job_matches_remote_eligibility", table_name="job_matches")
    op.drop_index("ix_job_matches_eligibility_status", table_name="job_matches")
    op.drop_index("ix_job_matches_profile_id", table_name="job_matches")
    op.drop_index("ix_job_matches_job_id", table_name="job_matches")
    op.drop_table("job_matches")
