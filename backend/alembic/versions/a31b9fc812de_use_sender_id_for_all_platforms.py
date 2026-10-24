"""use sender_id for all platforms

Revision ID: a31b9fc812de
Revises: 2d91a5c7e4b0
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a31b9fc812de"
down_revision: Union[str, Sequence[str], None] = "2d91a5c7e4b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE messages "
            "SET sender_id = COALESCE(sender_id, sender_platform_user_id)"
        )
    )
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_column("sender_platform_user_id")


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(
            sa.Column("sender_platform_user_id", sa.String(length=100), nullable=True)
        )
    op.execute(
        sa.text("UPDATE messages SET sender_platform_user_id = sender_id")
    )
