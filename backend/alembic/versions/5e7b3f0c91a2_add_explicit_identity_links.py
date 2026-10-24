"""add explicit identity links and contact source keys

Revision ID: 5e7b3f0c91a2
Revises: b7f2c4d91a63
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5e7b3f0c91a2"
down_revision: Union[str, Sequence[str], None] = "b7f2c4d91a63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canonical_identity_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    with op.batch_alter_table("canonical_identities") as batch_op:
        batch_op.add_column(
            sa.Column("identity_group_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index(
            "ix_canonical_identities_identity_group_id",
            ["identity_group_id"],
        )
        batch_op.create_foreign_key(
            "fk_canonical_identities_identity_group_id",
            "canonical_identity_groups",
            ["identity_group_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_canonical_identities_group_platform",
            ["identity_group_id", "platform"],
        )

    with op.batch_alter_table("contacts") as batch_op:
        batch_op.add_column(
            sa.Column("source_contact_key", sa.String(length=64), nullable=True)
        )
        batch_op.create_unique_constraint(
            "uq_contacts_account_source_key",
            ["account_id", "source_contact_key"],
        )

    op.create_table(
        "identity_link_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column(
            "identity_id",
            sa.Integer(),
            sa.ForeignKey("canonical_identities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "peer_identity_id",
            sa.Integer(),
            sa.ForeignKey("canonical_identities.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('linked', 'unlinked')",
            name="ck_identity_link_events_action",
        ),
    )
    op.create_index(
        "ix_identity_link_events_group_id",
        "identity_link_events",
        ["group_id"],
    )
    op.create_index(
        "ix_identity_link_events_identity_id",
        "identity_link_events",
        ["identity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_link_events_identity_id",
        table_name="identity_link_events",
    )
    op.drop_index(
        "ix_identity_link_events_group_id",
        table_name="identity_link_events",
    )
    op.drop_table("identity_link_events")

    with op.batch_alter_table("contacts") as batch_op:
        batch_op.drop_constraint(
            "uq_contacts_account_source_key",
            type_="unique",
        )
        batch_op.drop_column("source_contact_key")

    with op.batch_alter_table("canonical_identities") as batch_op:
        batch_op.drop_constraint(
            "uq_canonical_identities_group_platform",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_canonical_identities_identity_group_id",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_canonical_identities_identity_group_id")
        batch_op.drop_column("identity_group_id")
    op.drop_table("canonical_identity_groups")
