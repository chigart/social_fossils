"""allow multiple identities per platform in a group

Revision ID: 7a31c9e4b2f0
Revises: c9f47a61d2e8
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op


revision: str = "7a31c9e4b2f0"
down_revision: Union[str, Sequence[str], None] = "c9f47a61d2e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("canonical_identities") as batch_op:
        batch_op.drop_constraint(
            "uq_canonical_identities_group_platform",
            type_="unique",
        )


def downgrade() -> None:
    with op.batch_alter_table("canonical_identities") as batch_op:
        batch_op.create_unique_constraint(
            "uq_canonical_identities_group_platform",
            ["identity_group_id", "platform"],
        )
