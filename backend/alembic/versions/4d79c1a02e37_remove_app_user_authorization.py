"""remove app user authorization

Revision ID: 4d79c1a02e37
Revises: 31a0448c49e
Create Date: 2026-10-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d79c1a02e37"
down_revision: Union[str, Sequence[str], None] = "31a0448c49e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_upload_jobs_user_created", table_name="upload_jobs")
    op.drop_constraint(
        "upload_jobs_user_id_fkey",
        "upload_jobs",
        type_="foreignkey",
    )
    op.drop_column("upload_jobs", "user_id")
    op.drop_table("users")


def downgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.add_column(
        "upload_jobs",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "upload_jobs_user_id_fkey",
        "upload_jobs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_upload_jobs_user_created",
        "upload_jobs",
        ["user_id", "created_at"],
    )
