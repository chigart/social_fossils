"""add Telegram account username

Revision ID: c1b82e7a3d46
Revises: 9a6f2d1c4b80
Create Date: 2026-10-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1b82e7a3d46"
down_revision: Union[str, Sequence[str], None] = "9a6f2d1c4b80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telegram_accounts",
        sa.Column("username", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telegram_accounts", "username")
