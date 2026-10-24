from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.instagram_parser import (
    ParsedInstagramChat,
    parse_instagram_archive,
)
from app.models import (
    CanonicalIdentity,
    Chat,
    Contact,
    ImportSession,
    Message,
    Account,
)
from app.platforms import INSTAGRAM_PLATFORM_ID

logger = logging.getLogger(__name__)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        while chunk := source_file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _get_or_create_account(
    session: Session,
    account_name: str,
    account_username: str | None,
    owner_platform_user_id: str | None,
) -> Account:
    statement = select(Account).where(
        Account.platform == INSTAGRAM_PLATFORM_ID,
        Account.platform_user_id == owner_platform_user_id,
    )
    accounts = session.scalars(statement).all()
    if len(accounts) > 1:
        raise ValueError("Multiple Instagram source accounts match this export.")
    if accounts:
        account = accounts[0]
        account.name = account_name
        account.username = account_username
        session.flush()
        return account

    account = Account(
        platform=INSTAGRAM_PLATFORM_ID,
        name=account_name,
        username=account_username,
        platform_user_id=owner_platform_user_id,
    )
    session.add(account)
    session.flush()
    return account


def _ensure_chat(
    session: Session,
    account_id: int,
    parsed_chat: ParsedInstagramChat,
) -> Chat:
    chat = session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.platform == INSTAGRAM_PLATFORM_ID,
            Chat.chat_id == parsed_chat.platform_chat_id,
        )
    )
    if chat is not None:
        if parsed_chat.title is not None:
            chat.title = parsed_chat.title
        chat.chat_type = parsed_chat.chat_type
        session.flush()
        return chat

    statement = (
        insert(Chat)
        .values(
            account_id=account_id,
            platform=INSTAGRAM_PLATFORM_ID,
            chat_id=parsed_chat.platform_chat_id,
            chat_type=parsed_chat.chat_type,
            title=parsed_chat.title,
        )
        .on_conflict_do_nothing(
            index_elements=["account_id", "chat_id"]
        )
    )
    session.execute(statement)
    session.flush()
    chat = session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.platform == INSTAGRAM_PLATFORM_ID,
            Chat.chat_id == parsed_chat.platform_chat_id,
        )
    )
    if chat is None:
        raise RuntimeError("Instagram conversation could not be created.")
    return chat


def _get_or_create_contact(
    session: Session,
    account_id: int,
    platform_user_id: str | None,
    display_name: str | None,
) -> Contact | None:
    if not platform_user_id:
        return None

    identity_statement = (
        insert(CanonicalIdentity)
        .values(platform=INSTAGRAM_PLATFORM_ID, platform_user_id=platform_user_id)
        .on_conflict_do_nothing(
            index_elements=["platform", "platform_user_id"]
        )
    )
    session.execute(identity_statement)
    canonical_identity = session.scalar(
        select(CanonicalIdentity).where(
            CanonicalIdentity.platform == INSTAGRAM_PLATFORM_ID,
            CanonicalIdentity.platform_user_id == platform_user_id,
        )
    )
    if canonical_identity is None:
        raise RuntimeError("Instagram contact identity could not be created.")

    contact_statement = (
        insert(Contact)
        .values(
            account_id=account_id,
            platform=INSTAGRAM_PLATFORM_ID,
            telegram_user_id=None,
            platform_user_id=platform_user_id,
            canonical_identity_id=canonical_identity.id,
            display_name=display_name,
        )
        .on_conflict_do_nothing(
            index_elements=["account_id", "platform_user_id"]
        )
    )
    session.execute(contact_statement)
    contact = session.scalar(
        select(Contact).where(
            Contact.account_id == account_id,
            Contact.platform == INSTAGRAM_PLATFORM_ID,
            Contact.platform_user_id == platform_user_id,
        )
    )
    if contact is None:
        raise RuntimeError("Instagram contact could not be created.")
    if contact.canonical_identity_id != canonical_identity.id:
        contact.canonical_identity_id = canonical_identity.id
        session.flush()
    return contact


def _insert_message(
    session: Session,
    chat: Chat,
    payload: dict[str, Any],
    account_id: int,
) -> bool:
    source_record_key = payload["source_record_key"]
    source_message_id = payload["source_message_id"]
    duplicate_conditions = [Message.source_record_key == source_record_key]
    if source_message_id is not None:
        duplicate_conditions.append(Message.source_message_id == source_message_id)
    existing_message = session.scalar(
        select(Message).where(
            Message.chat_id == chat.id,
            Message.platform == INSTAGRAM_PLATFORM_ID,
            or_(*duplicate_conditions),
        )
    )
    if existing_message is not None:
        return False

    sender_platform_user_id = payload.get("sender_platform_user_id")
    contact = _get_or_create_contact(
        session,
        account_id,
        sender_platform_user_id,
        payload.get("sender_name"),
    )
    statement = (
        insert(Message)
        .values(
            chat_id=chat.id,
            platform=INSTAGRAM_PLATFORM_ID,
            message_id=None,
            source_message_id=source_message_id,
            source_record_key=source_record_key,
            sender_id=None,
            sender_platform_user_id=sender_platform_user_id,
            sender_contact_id=contact.id if contact is not None else None,
            sender_name=payload.get("sender_name"),
            is_outgoing=payload.get("is_outgoing"),
            message_date=payload.get("message_date"),
            message_type=payload.get("message_type") or "message",
            text_content=payload.get("text_content"),
            reply_to_telegram_message_id=None,
            source_reply_id=payload.get("source_reply_id"),
            raw_payload=payload.get("raw_payload") or {},
        )
        .on_conflict_do_nothing()
        .returning(Message.id)
    )
    return session.execute(statement).first() is not None


def import_instagram_export(
    export_path: str | Path,
    *,
    session: Session | None = None,
) -> dict[str, Any]:
    source_path = Path(export_path)
    logger.info("Reading and parsing Instagram export")
    try:
        parsed_export = parse_instagram_archive(source_path)
    except Exception as exc:
        logger.error("Unable to parse Instagram export (%s)", type(exc).__name__)
        raise
    if parsed_export.owner_platform_user_id is None:
        raise ValueError(
            "Instagram export does not contain a profile username or user ID."
        )

    chat_count = len(parsed_export.chats)
    parsed_message_count = sum(len(chat.messages) for chat in parsed_export.chats)
    logger.info(
        "Parsed Instagram export: %d conversations, %d messages",
        chat_count,
        parsed_message_count,
    )

    if session is None:
        session = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        account = _get_or_create_account(
            session,
            parsed_export.account_name,
            parsed_export.account_username,
            parsed_export.owner_platform_user_id,
        )
        file_digest = _file_sha256(source_path)
        import_session = ImportSession(
            account_id=account.id,
            platform=INSTAGRAM_PLATFORM_ID,
            source_filename=source_path.name,
            file_sha256=file_digest,
            status="running",
            started_at=datetime.now(timezone.utc),
            total_messages=0,
            inserted_messages=0,
            updated_messages=0,
            skipped_messages=0,
        )
        session.add(import_session)
        session.flush()

        total_messages = 0
        inserted_messages = 0
        skipped_messages = 0
        for chat in parsed_export.chats:
            persisted_chat = _ensure_chat(session, account.id, chat)
            for message in chat.messages:
                total_messages += 1
                if _insert_message(session, persisted_chat, message, account.id):
                    inserted_messages += 1
                else:
                    skipped_messages += 1

        import_session.total_messages = total_messages
        import_session.inserted_messages = inserted_messages
        import_session.skipped_messages = skipped_messages
        import_session.finished_at = datetime.now(timezone.utc)
        import_session.status = "completed"
        session.commit()
        logger.info(
            "Instagram import completed: %d messages processed, %d inserted, %d skipped",
            total_messages,
            inserted_messages,
            skipped_messages,
        )
        return {
            "platform": INSTAGRAM_PLATFORM_ID,
            "account_id": account.id,
            "account_name": account.name,
            "total_messages": total_messages,
            "inserted_messages": inserted_messages,
            "skipped_messages": skipped_messages,
            "session_id": import_session.id,
        }
    except Exception as exc:
        session.rollback()
        logger.error(
            "Instagram import failed; transaction rolled back (%s)",
            type(exc).__name__,
        )
        raise
    finally:
        if should_close:
            session.close()
