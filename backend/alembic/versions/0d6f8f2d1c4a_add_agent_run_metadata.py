"""add agent run metadata

Revision ID: 0d6f8f2d1c4a
Revises: cc58dd933593
Create Date: 2026-07-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0d6f8f2d1c4a"
down_revision: Union[str, None] = "cc58dd933593"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "metadata")
