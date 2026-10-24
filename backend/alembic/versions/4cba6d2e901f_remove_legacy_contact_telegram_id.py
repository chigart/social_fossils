"""remove legacy Telegram-specific contact ID

Revision ID: 4cba6d2e901f
Revises: 5e7b3f0c91a2
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4cba6d2e901f"
down_revision: Union[str, Sequence[str], None] = "5e7b3f0c91a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE contacts SET platform_user_id = telegram_user_id "
            "WHERE platform = 'telegram' "
            "AND platform_user_id IS NULL AND telegram_user_id IS NOT NULL"
        )
    )
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.drop_constraint(
            "uq_contacts_account_telegram_id",
            type_="unique",
        )
        batch_op.drop_column("telegram_user_id")


def downgrade() -> None:
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.add_column(
            sa.Column("telegram_user_id", sa.String(length=100), nullable=True)
        )
    op.execute(
        sa.text(
            "UPDATE contacts SET telegram_user_id = platform_user_id "
            "WHERE platform = 'telegram' AND platform_user_id IS NOT NULL"
        )
    )
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.create_unique_constraint(
            "uq_contacts_account_telegram_id",
            ["account_id", "telegram_user_id"],
        )
