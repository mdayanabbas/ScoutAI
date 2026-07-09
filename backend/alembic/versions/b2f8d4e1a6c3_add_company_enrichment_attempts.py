"""add company enrichment attempts

Revision ID: b2f8d4e1a6c3
Revises: 4955643c08b1
Create Date: 2026-07-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2f8d4e1a6c3"
down_revision: Union[str, None] = "4955643c08b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_enrichment_attempts",
        sa.Column("discovery_candidate_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "resolved",
                "unresolved",
                "failed",
                name="companyenrichmentstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "resolver",
            sa.Enum(
                "existing_url",
                "description_url",
                "evidence_url",
                "business_email_domain",
                "manual",
                "other",
                name="companyenrichmentresolver",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("proposed_website_url", sa.String(), nullable=True),
        sa.Column("proposed_domain", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "decision",
            sa.Enum(
                "created_company",
                "matched_existing_company",
                "unresolved",
                "rejected",
                "failed",
                name="companyenrichmentdecision",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["discovery_candidate_id"], ["discovery_candidates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_company_enrichment_attempts_discovery_candidate_id"),
        "company_enrichment_attempts",
        ["discovery_candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_enrichment_attempts_status"),
        "company_enrichment_attempts",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_enrichment_attempts_resolver"),
        "company_enrichment_attempts",
        ["resolver"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_enrichment_attempts_proposed_domain"),
        "company_enrichment_attempts",
        ["proposed_domain"],
        unique=False,
    )
    op.create_index(
        "ix_company_enrichment_attempts_created_at",
        "company_enrichment_attempts",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_company_enrichment_attempts_created_at",
        table_name="company_enrichment_attempts",
    )
    op.drop_index(
        op.f("ix_company_enrichment_attempts_proposed_domain"),
        table_name="company_enrichment_attempts",
    )
    op.drop_index(
        op.f("ix_company_enrichment_attempts_resolver"),
        table_name="company_enrichment_attempts",
    )
    op.drop_index(
        op.f("ix_company_enrichment_attempts_status"),
        table_name="company_enrichment_attempts",
    )
    op.drop_index(
        op.f("ix_company_enrichment_attempts_discovery_candidate_id"),
        table_name="company_enrichment_attempts",
    )
    op.drop_table("company_enrichment_attempts")
