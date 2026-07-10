"""add job enrichment foundation

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("seniority", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("employment_type", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("apply_url", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("salary_text", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("equity_mentioned", sa.Boolean(), nullable=True))
    op.add_column("jobs", sa.Column("visa_sponsorship", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("work_authorization", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("required_skills_json", sa.JSON(), nullable=True))
    op.add_column("jobs", sa.Column("preferred_skills_json", sa.JSON(), nullable=True))
    op.add_column("jobs", sa.Column("technologies_json", sa.JSON(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column(
            "enrichment_status",
            sa.String(length=32),
            server_default="not_enriched",
            nullable=False,
        ),
    )
    op.add_column("jobs", sa.Column("enrichment_confidence", sa.Float(), nullable=True))
    op.add_column("jobs", sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("jobs", "enrichment_status", server_default=None)
    op.create_index(op.f("ix_jobs_enrichment_status"), "jobs", ["enrichment_status"], unique=False)

    op.create_table(
        "job_enrichment_attempts",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("extracted_data_json", sa.JSON(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("field_confidence_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_enrichment_attempts_job_id", "job_enrichment_attempts", ["job_id"], unique=False)
    op.create_index("ix_job_enrichment_attempts_provider", "job_enrichment_attempts", ["provider"], unique=False)
    op.create_index("ix_job_enrichment_attempts_status", "job_enrichment_attempts", ["status"], unique=False)
    op.create_index("ix_job_enrichment_attempts_created_at", "job_enrichment_attempts", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_enrichment_attempts_created_at", table_name="job_enrichment_attempts")
    op.drop_index("ix_job_enrichment_attempts_status", table_name="job_enrichment_attempts")
    op.drop_index("ix_job_enrichment_attempts_provider", table_name="job_enrichment_attempts")
    op.drop_index("ix_job_enrichment_attempts_job_id", table_name="job_enrichment_attempts")
    op.drop_table("job_enrichment_attempts")

    op.drop_index(op.f("ix_jobs_enrichment_status"), table_name="jobs")
    op.drop_column("jobs", "enriched_at")
    op.drop_column("jobs", "enrichment_confidence")
    op.drop_column("jobs", "enrichment_status")
    op.drop_column("jobs", "technologies_json")
    op.drop_column("jobs", "preferred_skills_json")
    op.drop_column("jobs", "required_skills_json")
    op.drop_column("jobs", "work_authorization")
    op.drop_column("jobs", "visa_sponsorship")
    op.drop_column("jobs", "equity_mentioned")
    op.drop_column("jobs", "salary_text")
    op.drop_column("jobs", "last_verified_at")
    op.drop_column("jobs", "published_at")
    op.drop_column("jobs", "apply_url")
    op.drop_column("jobs", "employment_type")
    op.drop_column("jobs", "seniority")
