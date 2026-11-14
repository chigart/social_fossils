"""Add persistent analytics response cache.

Revision ID: d84c9a31f207
Revises: 7a31c9e4b2f0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d84c9a31f207"
down_revision: Union[str, Sequence[str], None] = "7a31c9e4b2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analytics_cache",
        sa.Column("cache_key", sa.String(length=64), primary_key=True),
        sa.Column("revision", sa.Text(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("analytics_cache")
