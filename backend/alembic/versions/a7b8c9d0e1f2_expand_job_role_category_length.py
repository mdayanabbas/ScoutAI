"""expand job role category length

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "jobs",
        "role_category",
        existing_type=sa.String(length=19),
        type_=sa.String(length=64),
        existing_nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    long_value = bind.execute(
        sa.text(
            "select role_category from jobs "
            "where role_category is not null and length(role_category) > 19 "
            "limit 1"
        )
    ).scalar()
    if long_value is not None:
        raise RuntimeError(
            "Cannot downgrade jobs.role_category to VARCHAR(19) while longer values exist"
        )
    op.alter_column(
        "jobs",
        "role_category",
        existing_type=sa.String(length=64),
        type_=sa.String(length=19),
        existing_nullable=True,
    )
