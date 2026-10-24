"""remove redundant source message identifier

Revision ID: c9f47a61d2e8
Revises: a31b9fc812de
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9f47a61d2e8"
down_revision: Union[str, Sequence[str], None] = "a31b9fc812de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("uq_messages_chat_source_id", type_="unique")
        batch_op.drop_column("source_message_id")


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(
            sa.Column("source_message_id", sa.String(length=200), nullable=True)
        )
        batch_op.create_unique_constraint(
            "uq_messages_chat_source_id",
            ["chat_id", "source_message_id"],
        )
