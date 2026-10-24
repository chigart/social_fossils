"""add platform-aware import fields

Revision ID: 8d9af4113e72
Revises: 4d79c1a02e37
Create Date: 2026-10-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8d9af4113e72"
down_revision: Union[str, Sequence[str], None] = "4d79c1a02e37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in (
        "telegram_accounts",
        "contacts",
        "chats",
        "messages",
        "import_sessions",
        "upload_jobs",
    ):
        op.add_column(
            table,
            sa.Column(
                "platform",
                sa.String(length=50),
                server_default="telegram",
                nullable=False,
            ),
        )
    for table in (
        "telegram_accounts",
        "contacts",
        "chats",
        "messages",
        "import_sessions",
        "upload_jobs",
    ):
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "platform",
                existing_type=sa.String(length=50),
                existing_nullable=False,
                existing_server_default="telegram",
                server_default=None,
            )

    op.add_column(
        "telegram_accounts",
        sa.Column("platform_user_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "contacts",
        sa.Column("platform_user_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "chats",
        sa.Column("platform_chat_id", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("source_message_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("source_record_key", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("sender_platform_user_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("source_reply_id", sa.String(length=200), nullable=True),
    )

    op.execute(
        sa.text(
            "UPDATE telegram_accounts SET platform_user_id = telegram_user_id "
            "WHERE platform = 'telegram'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE contacts SET platform_user_id = telegram_user_id "
            "WHERE platform = 'telegram'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE chats SET platform_chat_id = telegram_chat_id "
            "WHERE platform = 'telegram'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE messages SET source_message_id = telegram_message_id "
            "WHERE platform = 'telegram'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE messages SET sender_platform_user_id = sender_telegram_id "
            "WHERE platform = 'telegram'"
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE messages
            SET source_reply_id = reply_to_telegram_message_id
            WHERE platform = 'telegram'
            """
        )
    )

    with op.batch_alter_table("contacts") as batch_op:
        batch_op.alter_column(
            "telegram_user_id",
            existing_type=sa.String(length=100),
            nullable=True,
        )
        batch_op.create_unique_constraint(
            "uq_contacts_account_platform_id",
            ["account_id", "platform_user_id"],
        )
    with op.batch_alter_table("chats") as batch_op:
        batch_op.alter_column(
            "telegram_chat_id",
            existing_type=sa.String(length=100),
            nullable=True,
        )
        batch_op.create_unique_constraint(
            "uq_chats_account_platform_id",
            ["account_id", "platform_chat_id"],
        )
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "telegram_message_id",
            existing_type=sa.String(length=100),
            nullable=True,
        )
        batch_op.create_unique_constraint(
            "uq_messages_chat_source_id",
            ["chat_id", "source_message_id"],
        )
        batch_op.create_unique_constraint(
            "uq_messages_chat_source_record_key",
            ["chat_id", "source_record_key"],
        )
    op.create_index(
        "ix_telegram_accounts_platform",
        "telegram_accounts",
        ["platform"],
    )


def downgrade() -> None:
    has_instagram_accounts = op.get_bind().execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM telegram_accounts WHERE platform = 'instagram'"
            ")"
        )
    ).scalar_one()
    if has_instagram_accounts:
        raise RuntimeError(
            "Cannot downgrade platform import fields while Instagram data exists."
        )

    op.drop_index("ix_telegram_accounts_platform", table_name="telegram_accounts")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("uq_messages_chat_source_record_key", type_="unique")
        batch_op.drop_constraint("uq_messages_chat_source_id", type_="unique")
        batch_op.alter_column(
            "telegram_message_id",
            existing_type=sa.String(length=100),
            nullable=False,
        )
    with op.batch_alter_table("chats") as batch_op:
        batch_op.drop_constraint("uq_chats_account_platform_id", type_="unique")
        batch_op.alter_column(
            "telegram_chat_id",
            existing_type=sa.String(length=100),
            nullable=False,
        )
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.drop_constraint("uq_contacts_account_platform_id", type_="unique")
        batch_op.alter_column(
            "telegram_user_id",
            existing_type=sa.String(length=100),
            nullable=False,
        )
    for table, column in (
        ("messages", "source_reply_id"),
        ("messages", "sender_platform_user_id"),
        ("messages", "source_record_key"),
        ("messages", "source_message_id"),
        ("chats", "platform_chat_id"),
        ("contacts", "platform_user_id"),
        ("telegram_accounts", "platform_user_id"),
        ("upload_jobs", "platform"),
        ("import_sessions", "platform"),
        ("messages", "platform"),
        ("chats", "platform"),
        ("contacts", "platform"),
        ("telegram_accounts", "platform"),
    ):
        op.drop_column(table, column)
