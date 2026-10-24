"""generalize account and chat identifiers

Revision ID: 6a81c2f9d437
Revises: 8d9af4113e72
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6a81c2f9d437"
down_revision: Union[str, Sequence[str], None] = "8d9af4113e72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("telegram_accounts", "account")
    op.drop_index("ix_telegram_accounts_platform", table_name="account")
    op.create_index("ix_account_platform", "account", ["platform"])
    op.drop_column("account", "telegram_user_id")

    with op.batch_alter_table("chats") as batch_op:
        batch_op.drop_constraint("uq_chats_account_telegram_id", type_="unique")
        batch_op.drop_constraint("uq_chats_account_platform_id", type_="unique")
        batch_op.alter_column(
            "platform_chat_id",
            new_column_name="chat_id",
            existing_type=sa.String(length=500),
            nullable=False,
        )
        batch_op.drop_column("telegram_chat_id")

    with op.batch_alter_table("chats") as batch_op:
        batch_op.create_unique_constraint(
            "uq_chats_account_chat_id",
            ["account_id", "chat_id"],
        )


def downgrade() -> None:
    op.add_column(
        "account",
        sa.Column("telegram_user_id", sa.String(length=100), nullable=True),
    )
    op.drop_index("ix_account_platform", table_name="account")
    op.create_index("ix_telegram_accounts_platform", "account", ["platform"])
    op.execute(
        sa.text(
            "UPDATE account SET telegram_user_id = platform_user_id "
            "WHERE platform = 'telegram'"
        )
    )
    op.rename_table("account", "telegram_accounts")

    with op.batch_alter_table("chats") as batch_op:
        batch_op.drop_constraint("uq_chats_account_chat_id", type_="unique")
        batch_op.add_column(sa.Column("telegram_chat_id", sa.String(length=100)))
        batch_op.alter_column(
            "chat_id",
            new_column_name="platform_chat_id",
            existing_type=sa.String(length=500),
            nullable=True,
        )

    with op.batch_alter_table("chats") as batch_op:
        batch_op.create_unique_constraint(
            "uq_chats_account_telegram_id",
            ["account_id", "telegram_chat_id"],
        )
        batch_op.create_unique_constraint(
            "uq_chats_account_platform_id",
            ["account_id", "platform_chat_id"],
        )
    op.execute(
        sa.text(
            "UPDATE chats SET telegram_chat_id = platform_chat_id "
            "WHERE platform = 'telegram'"
        )
    )
