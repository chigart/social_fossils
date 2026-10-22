"""add user and upload job models

Revision ID: 31a0448c49e
Revises: c1b82e7a3d46
Create Date: 2026-10-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "31a0448c49e"
down_revision: Union[str, Sequence[str], None] = "c1b82e7a3d46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    op.create_table(
        "upload_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("source_account_id", sa.Integer(), nullable=True),
        sa.Column("import_session_id", sa.Integer(), nullable=True),
        sa.Column("airflow_dag_run_id", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="ck_upload_jobs_status"),
        sa.ForeignKeyConstraint(["import_session_id"], ["import_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_account_id"], ["telegram_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_upload_jobs_source_account_id", "upload_jobs", ["source_account_id"])
    op.create_index("ix_upload_jobs_user_created", "upload_jobs", ["user_id", "created_at"])
    op.create_index("ix_upload_jobs_import_session_id", "upload_jobs", ["import_session_id"])


def downgrade() -> None:
    op.drop_index("ix_upload_jobs_import_session_id", table_name="upload_jobs")
    op.drop_index("ix_upload_jobs_user_created", table_name="upload_jobs")
    op.drop_index("ix_upload_jobs_source_account_id", table_name="upload_jobs")
    op.drop_table("upload_jobs")
    op.drop_table("users")
