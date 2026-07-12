"""add job matching profiles

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_matching_profiles",
        sa.Column("user_profile_id", sa.String(), nullable=False),
        sa.Column("matching_enabled", sa.Boolean(), nullable=False),
        sa.Column("target_titles_json", sa.JSON(), nullable=False),
        sa.Column("target_role_categories_json", sa.JSON(), nullable=False),
        sa.Column("preferred_seniority_json", sa.JSON(), nullable=False),
        sa.Column("years_of_experience", sa.Float(), nullable=True),
        sa.Column("skills_json", sa.JSON(), nullable=False),
        sa.Column("technologies_json", sa.JSON(), nullable=False),
        sa.Column("preferred_locations_json", sa.JSON(), nullable=False),
        sa.Column("preferred_countries_json", sa.JSON(), nullable=False),
        sa.Column("accepted_remote_types_json", sa.JSON(), nullable=False),
        sa.Column("accepted_employment_types_json", sa.JSON(), nullable=False),
        sa.Column("minimum_salary", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(length=8), nullable=True),
        sa.Column("visa_sponsorship_required", sa.Boolean(), nullable=True),
        sa.Column("work_authorization_countries_json", sa.JSON(), nullable=False),
        sa.Column("willing_to_relocate", sa.Boolean(), nullable=True),
        sa.Column("preferred_company_stages_json", sa.JSON(), nullable=False),
        sa.Column("preferred_company_sizes_json", sa.JSON(), nullable=False),
        sa.Column("excluded_titles_json", sa.JSON(), nullable=False),
        sa.Column("excluded_role_categories_json", sa.JSON(), nullable=False),
        sa.Column("excluded_company_ids_json", sa.JSON(), nullable=False),
        sa.Column("excluded_locations_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_profile_id", name="uq_job_matching_profiles_user_profile_id"),
    )
    op.create_index(
        "ix_job_matching_profiles_user_profile_id",
        "job_matching_profiles",
        ["user_profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_matching_profiles_user_profile_id", table_name="job_matching_profiles")
    op.drop_table("job_matching_profiles")
