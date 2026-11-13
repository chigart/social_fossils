from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.constants import MESSAGE_INSERT_BATCH_SIZE, VK_PLATFORM_ID
from app.importers.import_utils import file_sha256, insert_message_batch
from app.models import Account, CanonicalIdentity, Chat, Contact, ImportSession, Message
from app.parsers.vk_parser import ParsedVkChat, parse_vk_archive

logger = logging.getLogger(__name__)
def _get_or_create_account(
    session: Session,
    account_name: str,
    account_username: str | None,
    owner_platform_user_id: str | None,
) -> Account:
    identity_filter = (
        Account.platform_user_id == owner_platform_user_id
        if owner_platform_user_id is not None
        else (
            Account.platform_user_id.is_(None)
            & (Account.name == account_name)
        )
    )
    if session.get_bind().dialect.name == "postgresql":
        identity = owner_platform_user_id or account_name.casefold()
        session.execute(
            select(
                func.pg_advisory_xact_lock(
                    func.hashtext(f"vk-account:{identity}")
                )
            )
        )

    accounts = session.scalars(
        select(Account).where(
            Account.platform == VK_PLATFORM_ID,
            identity_filter,
        )
    ).all()
    if len(accounts) > 1:
        raise ValueError("Multiple VK source accounts match this export.")
    if accounts:
        account = accounts[0]
        account.name = account_name
        if account_username is not None:
            account.username = account_username
        session.flush()
        return account

    account = Account(
        platform=VK_PLATFORM_ID,
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
    parsed_chat: ParsedVkChat,
) -> Chat:
    chat = session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.platform == VK_PLATFORM_ID,
            Chat.chat_id == parsed_chat.platform_chat_id,
        )
    )
    if chat is not None:
        if parsed_chat.title is not None:
            chat.title = parsed_chat.title
        chat.chat_type = parsed_chat.chat_type
        session.flush()
        return chat

    session.execute(
        insert(Chat)
        .values(
            account_id=account_id,
            platform=VK_PLATFORM_ID,
            chat_id=parsed_chat.platform_chat_id,
            chat_type=parsed_chat.chat_type,
            title=parsed_chat.title,
        )
        .on_conflict_do_nothing(index_elements=["account_id", "chat_id"])
    )
    session.flush()
    chat = session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.platform == VK_PLATFORM_ID,
            Chat.chat_id == parsed_chat.platform_chat_id,
        )
    )
    if chat is None:
        raise RuntimeError("VK conversation could not be created.")
    return chat


def _source_contact_key(name: str, chat_id: str) -> str:
    normalized_name = " ".join(name.casefold().split())
    return hashlib.sha256(
        f"{chat_id}:{normalized_name}".encode("utf-8")
    ).hexdigest()


def _get_or_create_contact(
    session: Session,
    account_id: int,
    platform_user_id: str | None,
    display_name: str | None,
    chat_id: str,
) -> tuple[Contact | None, bool]:
    source_key = (
        _source_contact_key(display_name, chat_id)
        if platform_user_id is None and display_name
        else None
    )
    if platform_user_id is None and source_key is None:
        return None, False

    identity_filter = (
        Contact.platform_user_id == platform_user_id
        if platform_user_id is not None
        else Contact.source_contact_key == source_key
    )
    contact = session.scalar(
        select(Contact).where(
            Contact.account_id == account_id,
            Contact.platform == VK_PLATFORM_ID,
            identity_filter,
        )
    )
    if contact is not None:
        if contact.display_name is None and display_name is not None:
            contact.display_name = display_name
            session.flush()
        return contact, False

    canonical_identity_id = None
    if platform_user_id is not None:
        session.execute(
            insert(CanonicalIdentity)
            .values(
                platform=VK_PLATFORM_ID,
                platform_user_id=platform_user_id,
            )
            .on_conflict_do_nothing(
                index_elements=["platform", "platform_user_id"]
            )
        )
        canonical_identity = session.scalar(
            select(CanonicalIdentity).where(
                CanonicalIdentity.platform == VK_PLATFORM_ID,
                CanonicalIdentity.platform_user_id == platform_user_id,
            )
        )
        if canonical_identity is None:
            raise RuntimeError("VK contact identity could not be created.")
        canonical_identity_id = canonical_identity.id

    session.execute(
        insert(Contact)
        .values(
            account_id=account_id,
            platform=VK_PLATFORM_ID,
            platform_user_id=platform_user_id,
            source_contact_key=source_key,
            canonical_identity_id=canonical_identity_id,
            display_name=display_name,
        )
        .on_conflict_do_nothing()
    )
    session.flush()
    contact = session.scalar(
        select(Contact).where(
            Contact.account_id == account_id,
            Contact.platform == VK_PLATFORM_ID,
            identity_filter,
        )
    )
    if contact is None:
        raise RuntimeError("VK contact could not be created.")
    return contact, True


def _contact_for_chat(
    session: Session,
    account_id: int,
    parsed_chat: ParsedVkChat,
) -> tuple[Contact | None, bool]:
    if parsed_chat.chat_type != "personal_chat":
        return None, False
    return _get_or_create_contact(
        session,
        account_id,
        parsed_chat.correspondent_platform_user_id,
        parsed_chat.correspondent_name or parsed_chat.title,
        parsed_chat.platform_chat_id,
    )


def _message_values(
    session: Session,
    chat: Chat,
    payload: dict[str, Any],
    account: Account,
    owner_contact: Contact | None,
    chat_contact: Contact | None,
    contact_cache: dict[str, Contact],
) -> tuple[dict[str, Any], bool]:
    sender_id = payload.get("sender_id")
    is_outgoing = payload.get("is_outgoing")
    if (
        account.platform_user_id is not None
        and sender_id == account.platform_user_id
    ):
        is_outgoing = True
    elif sender_id is not None and is_outgoing is None:
        is_outgoing = False

    sender_contact = None
    contact_inserted = False
    if is_outgoing is True:
        sender_contact = owner_contact
    elif is_outgoing is False:
        if (
            chat_contact is not None
            and sender_id == chat_contact.platform_user_id
        ):
            sender_contact = chat_contact
        elif sender_id is not None:
            sender_contact = contact_cache.get(sender_id)
            if sender_contact is None:
                sender_contact, contact_inserted = _get_or_create_contact(
                    session,
                    account.id,
                    sender_id,
                    payload.get("sender_name"),
                    chat.chat_id,
                )
                if sender_contact is not None:
                    contact_cache[sender_id] = sender_contact
        elif chat_contact is not None:
            sender_contact = chat_contact
        elif isinstance(payload.get("sender_name"), str):
            sender_contact, contact_inserted = _get_or_create_contact(
                session,
                account.id,
                None,
                payload["sender_name"],
                chat.chat_id,
            )

    return (
        {
            "chat_id": chat.id,
            "platform": VK_PLATFORM_ID,
            "message_id": payload["message_id"],
            "source_record_key": payload["source_record_key"],
            "sender_id": sender_id,
            "sender_contact_id": (
                sender_contact.id if sender_contact is not None else None
            ),
            "sender_name": payload.get("sender_name"),
            "is_outgoing": is_outgoing,
            "message_date": payload.get("message_date"),
            "message_type": payload.get("message_type") or "message",
            "text_content": payload.get("text_content"),
            "reply_to_telegram_message_id": None,
            "source_reply_id": payload.get("source_reply_id"),
            "raw_payload": payload.get("raw_payload") or {},
        },
        contact_inserted,
    )


def _update_existing_outgoing_sender_names(
    session: Session,
    chat: Chat,
    messages: list[dict[str, Any]],
    account_name: str,
) -> None:
    source_record_keys = {
        message["source_record_key"]
        for message in messages
        if message.get("is_outgoing") is True
        and isinstance(message.get("source_record_key"), str)
    }
    if not source_record_keys:
        return

    session.execute(
        update(Message)
        .where(
            Message.chat_id == chat.id,
            Message.platform == VK_PLATFORM_ID,
            Message.source_record_key.in_(source_record_keys),
            Message.is_outgoing.is_(True),
            Message.sender_name.is_distinct_from(account_name),
        )
        .values(sender_name=account_name)
    )


def _insert_messages_for_chat(
    session: Session,
    chat: Chat,
    messages: list[dict[str, Any]],
    account: Account,
    owner_contact: Contact | None,
    chat_contact: Contact | None,
    contact_cache: dict[str, Contact],
) -> tuple[int, int, int]:
    inserted_messages = 0
    skipped_messages = 0
    inserted_contacts = 0
    for start in range(0, len(messages), MESSAGE_INSERT_BATCH_SIZE):
        batch = messages[start : start + MESSAGE_INSERT_BATCH_SIZE]
        values = []
        for message in batch:
            message_values, contact_inserted = _message_values(
                session,
                chat,
                message,
                account,
                owner_contact,
                chat_contact,
                contact_cache,
            )
            values.append(message_values)
            inserted_contacts += int(contact_inserted)
        _update_existing_outgoing_sender_names(
            session,
            chat,
            batch,
            account.name,
        )
        inserted = insert_message_batch(session, values)
        inserted_messages += inserted
        skipped_messages += len(values) - inserted
    return inserted_messages, skipped_messages, inserted_contacts


def import_vk_export(
    export_path: str | Path,
    *,
    session: Session | None = None,
) -> dict[str, Any]:
    source_path = Path(export_path)
    logger.info("Reading and parsing VK export")
    try:
        parsed_export = parse_vk_archive(source_path)
    except Exception as exc:
        logger.error("Unable to parse VK export (%s)", type(exc).__name__)
        raise

    chat_count = len(parsed_export.chats)
    parsed_message_count = sum(len(chat.messages) for chat in parsed_export.chats)
    logger.info(
        "Parsed VK export: %d conversations, %d messages",
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
        import_session = ImportSession(
            account_id=account.id,
            platform=VK_PLATFORM_ID,
            source_filename=source_path.name,
            file_sha256=file_sha256(source_path),
            status="running",
            started_at=datetime.now(timezone.utc),
            total_messages=0,
            inserted_messages=0,
            updated_messages=0,
            skipped_messages=0,
        )
        session.add(import_session)
        session.flush()

        owner_contact = None
        inserted_contacts = 0
        if account.platform_user_id is not None:
            owner_contact, owner_inserted = _get_or_create_contact(
                session,
                account.id,
                account.platform_user_id,
                account.name,
                "",
            )
            inserted_contacts += int(owner_inserted)

        total_messages = 0
        inserted_messages = 0
        skipped_messages = 0
        contact_cache: dict[str, Contact] = {}
        for parsed_chat in parsed_export.chats:
            chat = _ensure_chat(session, account.id, parsed_chat)
            chat_contact, contact_inserted = _contact_for_chat(
                session,
                account.id,
                parsed_chat,
            )
            inserted_contacts += int(contact_inserted)
            total_messages += len(parsed_chat.messages)
            (
                inserted_for_chat,
                skipped_for_chat,
                inserted_for_chat_contacts,
            ) = _insert_messages_for_chat(
                session,
                chat,
                parsed_chat.messages,
                account,
                owner_contact,
                chat_contact,
                contact_cache,
            )
            inserted_messages += inserted_for_chat
            skipped_messages += skipped_for_chat
            inserted_contacts += inserted_for_chat_contacts

        import_session.total_messages = total_messages
        import_session.inserted_messages = inserted_messages
        import_session.skipped_messages = skipped_messages
        import_session.finished_at = datetime.now(timezone.utc)
        import_session.status = "completed"
        session.commit()
        logger.info(
            "VK import completed: %d messages processed, %d inserted, %d skipped",
            total_messages,
            inserted_messages,
            skipped_messages,
        )
        return {
            "platform": VK_PLATFORM_ID,
            "account_id": account.id,
            "total_messages": total_messages,
            "inserted_messages": inserted_messages,
            "skipped_messages": skipped_messages,
            "inserted_contacts": inserted_contacts,
            "session_id": import_session.id,
        }
    except Exception as exc:
        session.rollback()
        logger.error(
            "VK import failed; transaction rolled back (%s)",
            type(exc).__name__,
        )
        raise
    finally:
        if should_close:
            session.close()
