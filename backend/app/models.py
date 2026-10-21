from datetime import datetime
from typing import Any

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


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_user_id: Mapped[str | None] = mapped_column(String(100))
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Contact(Base):
    __tablename__ = "contacts"

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "telegram_user_id",
            name="uq_contacts_account_telegram_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"),
        index=True,
    )
    telegram_user_id: Mapped[str] = mapped_column(String(100))
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
            "telegram_chat_id",
            name="uq_chats_account_telegram_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"),
        index=True,
    )
    telegram_chat_id: Mapped[str] = mapped_column(String(100))
    chat_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ChatMember(Base):
    __tablename__ = "chat_members"

    __table_args__ = (
        UniqueConstraint(
            "chat_id",
            "telegram_user_id",
            name="uq_chat_members_chat_telegram_user",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        index=True,
    )
    telegram_user_id: Mapped[str] = mapped_column(String(100))
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(300))
    is_self: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
    )


class Message(Base):
    __tablename__ = "messages"

    __table_args__ = (
        UniqueConstraint(
            "chat_id",
            "telegram_message_id",
            name="uq_messages_chat_telegram_id",
        ),
        Index("ix_messages_chat_date", "chat_id", "message_date"),
        Index("ix_messages_sender", "sender_contact_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
    )
    telegram_message_id: Mapped[str] = mapped_column(String(100))
    sender_telegram_id: Mapped[str | None] = mapped_column(String(100))
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
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"),
        index=True,
    )
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