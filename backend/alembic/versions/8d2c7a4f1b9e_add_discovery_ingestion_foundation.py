"""add discovery ingestion foundation

Revision ID: 8d2c7a4f1b9e
Revises: cc58dd933593
Create Date: 2026-07-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8d2c7a4f1b9e"
down_revision: Union[str, None] = "cc58dd933593"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


discovery_source = sa.Enum(
    "manual",
    "hacker_news",
    "product_hunt",
    "yc",
    "wellfound",
    "vc_portfolio",
    "rss",
    "newsletter",
    "company_directory",
    "other",
    name="discoverysource",
    native_enum=False,
)

discovery_run_status = sa.Enum(
    "pending",
    "running",
    "success",
    "partial_success",
    "failed",
    name="discoveryrunstatus",
    native_enum=False,
)

discovery_candidate_status = sa.Enum(
    "discovered",
    "normalized",
    "duplicate",
    "rejected",
    "ingested",
    "failed",
    name="discoverycandidatestatus",
    native_enum=False,
)

discovery_decision = sa.Enum(
    "created_company",
    "matched_existing_company",
    "rejected",
    "failed",
    name="discoverydecision",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "discovery_runs",
        sa.Column("source", discovery_source, nullable=False),
        sa.Column("status", discovery_run_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candidates_found", sa.Integer(), nullable=False),
        sa.Column("candidates_normalized", sa.Integer(), nullable=False),
        sa.Column("companies_created", sa.Integer(), nullable=False),
        sa.Column("companies_matched", sa.Integer(), nullable=False),
        sa.Column("candidates_rejected", sa.Integer(), nullable=False),
        sa.Column("candidates_failed", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_discovery_runs_created_at"),
        "discovery_runs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_runs_source"), "discovery_runs", ["source"], unique=False
    )
    op.create_index(
        op.f("ix_discovery_runs_status"), "discovery_runs", ["status"], unique=False
    )

    op.create_table(
        "discovery_candidates",
        sa.Column("discovery_run_id", sa.String(), nullable=False),
        sa.Column("source", discovery_source, nullable=False),
        sa.Column("source_identifier", sa.String(), nullable=False),
        sa.Column("raw_name", sa.String(), nullable=False),
        sa.Column("raw_website_url", sa.String(), nullable=True),
        sa.Column("raw_description", sa.Text(), nullable=True),
        sa.Column("raw_country", sa.String(), nullable=True),
        sa.Column("normalized_name", sa.String(), nullable=True),
        sa.Column("normalized_website_url", sa.String(), nullable=True),
        sa.Column("normalized_domain", sa.String(), nullable=True),
        sa.Column("normalized_description", sa.Text(), nullable=True),
        sa.Column("normalized_country", sa.String(), nullable=True),
        sa.Column("status", discovery_candidate_status, nullable=False),
        sa.Column("decision", discovery_decision, nullable=True),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("matched_company_id", sa.String(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["discovery_run_id"], ["discovery_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["matched_company_id"], ["companies.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "discovery_run_id",
            "source",
            "source_identifier",
            name="uq_discovery_candidate_run_source_identifier",
        ),
    )
    op.create_index(
        op.f("ix_discovery_candidates_discovery_run_id"),
        "discovery_candidates",
        ["discovery_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_candidates_normalized_domain"),
        "discovery_candidates",
        ["normalized_domain"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_candidates_source_identifier"),
        "discovery_candidates",
        ["source_identifier"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_candidates_status"),
        "discovery_candidates",
        ["status"],
        unique=False,
    )

    op.create_table(
        "discovery_evidence",
        sa.Column("discovery_candidate_id", sa.String(), nullable=False),
        sa.Column("evidence_type", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
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
        op.f("ix_discovery_evidence_discovery_candidate_id"),
        "discovery_evidence",
        ["discovery_candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_evidence_evidence_type"),
        "discovery_evidence",
        ["evidence_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_discovery_evidence_evidence_type"), table_name="discovery_evidence")
    op.drop_index(
        op.f("ix_discovery_evidence_discovery_candidate_id"),
        table_name="discovery_evidence",
    )
    op.drop_table("discovery_evidence")

    op.drop_index(op.f("ix_discovery_candidates_status"), table_name="discovery_candidates")
    op.drop_index(
        op.f("ix_discovery_candidates_source_identifier"),
        table_name="discovery_candidates",
    )
    op.drop_index(
        op.f("ix_discovery_candidates_normalized_domain"),
        table_name="discovery_candidates",
    )
    op.drop_index(
        op.f("ix_discovery_candidates_discovery_run_id"),
        table_name="discovery_candidates",
    )
    op.drop_table("discovery_candidates")

    op.drop_index(op.f("ix_discovery_runs_status"), table_name="discovery_runs")
    op.drop_index(op.f("ix_discovery_runs_source"), table_name="discovery_runs")
    op.drop_index(op.f("ix_discovery_runs_created_at"), table_name="discovery_runs")
    op.drop_table("discovery_runs")
