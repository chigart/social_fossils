"""rename Telegram-specific message columns

Revision ID: b7f2c4d91a63
Revises: 6a81c2f9d437
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7f2c4d91a63"
down_revision: Union[str, Sequence[str], None] = "6a81c2f9d437"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("uq_messages_chat_telegram_id", type_="unique")
        batch_op.alter_column(
            "telegram_message_id",
            new_column_name="message_id",
            existing_type=sa.String(length=100),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "sender_telegram_id",
            new_column_name="sender_id",
            existing_type=sa.String(length=100),
            existing_nullable=True,
        )

    with op.batch_alter_table("messages") as batch_op:
        batch_op.create_unique_constraint(
            "uq_messages_chat_message_id",
            ["chat_id", "message_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("uq_messages_chat_message_id", type_="unique")
        batch_op.alter_column(
            "message_id",
            new_column_name="telegram_message_id",
            existing_type=sa.String(length=100),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "sender_id",
            new_column_name="sender_telegram_id",
            existing_type=sa.String(length=100),
            existing_nullable=True,
        )

    with op.batch_alter_table("messages") as batch_op:
        batch_op.create_unique_constraint(
            "uq_messages_chat_telegram_id",
            ["chat_id", "telegram_message_id"],
        )
