"""add canonical contact identities

Revision ID: 9a6f2d1c4b80
Revises: 13efe0f4a972
Create Date: 2026-10-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a6f2d1c4b80"
down_revision: Union[str, Sequence[str], None] = "13efe0f4a972"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canonical_identities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("platform_user_id", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "platform",
            "platform_user_id",
            name="uq_canonical_identities_platform_user",
        ),
    )
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.add_column(
            sa.Column("canonical_identity_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index(
            "ix_contacts_canonical_identity_id",
            ["canonical_identity_id"],
        )
        batch_op.create_foreign_key(
            "fk_contacts_canonical_identity_id_canonical_identities",
            "canonical_identities",
            ["canonical_identity_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.execute(
        sa.text(
            """
            INSERT INTO canonical_identities (platform, platform_user_id)
            SELECT DISTINCT 'telegram', telegram_user_id
            FROM contacts
            WHERE telegram_user_id IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE contacts
            SET canonical_identity_id = canonical_identities.id
            FROM canonical_identities
            WHERE canonical_identities.platform = 'telegram'
              AND canonical_identities.platform_user_id = contacts.telegram_user_id
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.drop_constraint(
            "fk_contacts_canonical_identity_id_canonical_identities",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_contacts_canonical_identity_id")
        batch_op.drop_column("canonical_identity_id")
    op.drop_table("canonical_identities")
