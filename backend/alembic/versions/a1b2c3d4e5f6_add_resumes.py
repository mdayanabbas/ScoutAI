"""add resumes

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-07-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("user_profile_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("parse_status", sa.String(length=32), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed_summary_json", sa.JSON(), nullable=True),
        sa.Column("skills_json", sa.JSON(), nullable=False),
        sa.Column("technologies_json", sa.JSON(), nullable=False),
        sa.Column("projects_json", sa.JSON(), nullable=False),
        sa.Column("experience_json", sa.JSON(), nullable=False),
        sa.Column("education_json", sa.JSON(), nullable=False),
        sa.Column("certifications_json", sa.JSON(), nullable=False),
        sa.Column("links_json", sa.JSON(), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resumes_user_profile_id", "resumes", ["user_profile_id"])
    op.create_index("ix_resumes_file_sha256", "resumes", ["file_sha256"])
    op.create_index("ix_resumes_is_active", "resumes", ["is_active"])
    op.create_index("ix_resumes_parse_status", "resumes", ["parse_status"])
    op.create_index("ix_resumes_created_at", "resumes", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_resumes_created_at", table_name="resumes")
    op.drop_index("ix_resumes_parse_status", table_name="resumes")
    op.drop_index("ix_resumes_is_active", table_name="resumes")
    op.drop_index("ix_resumes_file_sha256", table_name="resumes")
    op.drop_index("ix_resumes_user_profile_id", table_name="resumes")
    op.drop_table("resumes")
