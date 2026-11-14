from datetime import datetime
from typing import Any, Literal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform_user_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CanonicalIdentity(Base):
    __tablename__ = "canonical_identities"

    __table_args__ = (
        UniqueConstraint(
            "platform",
            "platform_user_id",
            name="uq_canonical_identities_platform_user",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(50))
    platform_user_id: Mapped[str] = mapped_column(String(100))
    identity_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("canonical_identity_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CanonicalIdentityGroup(Base):
    __tablename__ = "canonical_identity_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class IdentityLinkEvent(Base):
    __tablename__ = "identity_link_events"

    __table_args__ = (
        CheckConstraint(
            "action IN ('linked', 'unlinked')",
            name="ck_identity_link_events_action",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    identity_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_identities.id", ondelete="RESTRICT"),
        index=True,
    )
    peer_identity_id: Mapped[int | None] = mapped_column(
        ForeignKey("canonical_identities.id", ondelete="RESTRICT"),
        nullable=True,
    )
    action: Mapped[Literal["linked", "unlinked"]] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class AnalyticsCacheEntry(Base):
    __tablename__ = "analytics_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision: Mapped[str] = mapped_column(Text, nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)


class Contact(Base):
    __tablename__ = "contacts"

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "platform_user_id",
            name="uq_contacts_account_platform_id",
        ),
        UniqueConstraint(
            "account_id",
            "source_contact_key",
            name="uq_contacts_account_source_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"),
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(50))
    platform_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_contact_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canonical_identity_id: Mapped[int | None] = mapped_column(
        ForeignKey("canonical_identities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(300))
    username: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Chat(Base):
    __tablename__ = "chats"

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "chat_id",
            name="uq_chats_account_chat_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"),
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(50))
    chat_id: Mapped[str] = mapped_column(String(500))
    chat_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Message(Base):
    __tablename__ = "messages"

    __table_args__ = (
        UniqueConstraint(
            "chat_id",
            "message_id",
            name="uq_messages_chat_message_id",
        ),
        UniqueConstraint(
            "chat_id",
            "source_record_key",
            name="uq_messages_chat_source_record_key",
        ),
        Index("ix_messages_chat_date", "chat_id", "message_date"),
        Index("ix_messages_sender", "sender_contact_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
    )
    platform: Mapped[str] = mapped_column(String(50))
    message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_record_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sender_id: Mapped[str | None] = mapped_column(String(100))
    sender_contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    sender_name: Mapped[str | None] = mapped_column(String(300))
    is_outgoing: Mapped[bool | None] = mapped_column(Boolean)
    message_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    message_type: Mapped[str] = mapped_column(
        String(50),
        default="message",
        server_default=text("'message'"),
    )
    text_content: Mapped[str | None] = mapped_column(Text)
    reply_to_telegram_message_id: Mapped[str | None] = mapped_column(
        String(100),
    )
    source_reply_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ImportSession(Base):
    __tablename__ = "import_sessions"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_import_sessions_status",
        ),
        Index(
            "ix_import_sessions_account_hash",
            "account_id",
            "file_sha256",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"),
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(50))
    source_filename: Mapped[str] = mapped_column(String(500))
    file_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default=text("'pending'"),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    total_messages: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
    )
    inserted_messages: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
    )
    updated_messages: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
    )
    skipped_messages: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class UploadJob(Base):
    __tablename__ = "upload_jobs"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_upload_jobs_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(500))
    platform: Mapped[str] = mapped_column(String(50))
    file_sha256: Mapped[str] = mapped_column(String(64))
    file_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default=text("'pending'"),
    )
    source_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    import_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    airflow_dag_run_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )