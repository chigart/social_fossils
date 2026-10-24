"""drop unused chat_members table

Revision ID: 2d91a5c7e4b0
Revises: 4cba6d2e901f
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2d91a5c7e4b0"
down_revision: Union[str, Sequence[str], None] = "4cba6d2e901f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("chat_members")


def downgrade() -> None:
    op.create_table(
        "chat_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.String(length=100), nullable=False),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        sa.Column("display_name", sa.String(length=300), nullable=True),
        sa.Column(
            "is_self",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            ["chats.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chat_id",
            "telegram_user_id",
            name="uq_chat_members_chat_telegram_user",
        ),
    )
    op.create_index(
        "ix_chat_members_chat_id",
        "chat_members",
        ["chat_id"],
    )
