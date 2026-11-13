from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.constants import INSTAGRAM_PLATFORM_ID, MESSAGE_INSERT_BATCH_SIZE
from app.importers.import_utils import file_sha256, insert_message_batch
from app.parsers.instagram_parser import (
    ParsedInstagramChat,
    normalize_instagram_text,
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

logger = logging.getLogger(__name__)
def _is_placeholder_contact_name(name: str | None) -> bool:
    return (
        isinstance(name, str)
        and normalize_instagram_text(name).strip().casefold() == "instagram user"
    )


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
    *,
    username: str | None = None,
) -> Contact | None:
    if not platform_user_id:
        return None
    if _is_placeholder_contact_name(display_name):
        existing_contact = session.scalar(
            select(Contact).where(
                Contact.account_id == account_id,
                Contact.platform == INSTAGRAM_PLATFORM_ID,
                Contact.platform_user_id == platform_user_id,
            )
        )
        return existing_contact

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
            platform_user_id=platform_user_id,
            canonical_identity_id=canonical_identity.id,
            display_name=display_name,
            username=username,
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
    if contact.display_name is None and display_name is not None:
        contact.display_name = display_name
    elif display_name is not None and contact.display_name is not None:
        contact.display_name = normalize_instagram_text(contact.display_name)
    if username is not None:
        contact.username = username
    if session.is_modified(contact):
        session.flush()
    return contact


def _ensure_owner_contact(
    session: Session,
    account: Account,
) -> tuple[Contact, bool]:
    if account.platform_user_id is None:
        raise ValueError("Instagram account does not have a platform user ID.")
    existed = session.scalar(
        select(Contact.id).where(
            Contact.account_id == account.id,
            Contact.platform == INSTAGRAM_PLATFORM_ID,
            Contact.platform_user_id == account.platform_user_id,
        )
    ) is not None
    contact = _get_or_create_contact(
        session,
        account.id,
        account.platform_user_id,
        account.name,
        username=account.username,
    )
    if contact is None:
        raise RuntimeError("Instagram account contact could not be created.")
    return contact, not existed


def _ensure_folder_contact(
    session: Session,
    account_id: int,
    parsed_chat: ParsedInstagramChat,
) -> tuple[Contact | None, bool]:
    if parsed_chat.correspondent_platform_user_id is None:
        return None, False
    existed = session.scalar(
        select(Contact.id).where(
            Contact.account_id == account_id,
            Contact.platform == INSTAGRAM_PLATFORM_ID,
            Contact.platform_user_id == parsed_chat.correspondent_platform_user_id,
        )
    ) is not None
    contact = _get_or_create_contact(
        session,
        account_id,
        parsed_chat.correspondent_platform_user_id,
        parsed_chat.title or parsed_chat.correspondent_username,
        username=parsed_chat.correspondent_username,
    )
    if contact is None:
        return None, False
    return contact, not existed


def _message_values(
    session: Session,
    chat: Chat,
    payload: dict[str, Any],
    contact: Contact | None,
    owner_contact: Contact,
    account: Account,
) -> dict[str, Any]:
    sender_id = payload.get("sender_id")
    is_outgoing = payload.get("is_outgoing")
    sender_name = payload.get("sender_name")
    normalized_sender_name = (
        normalize_instagram_text(sender_name).strip().casefold()
        if isinstance(sender_name, str)
        else None
    )
    owner_names = {
        normalize_instagram_text(value).strip().casefold()
        for value in (account.username, account.name)
        if value
    }
    is_owner = is_outgoing is True or (
        sender_id is not None and sender_id == account.platform_user_id
    ) or (
        normalized_sender_name is not None
        and normalized_sender_name in owner_names
    )
    if is_owner:
        sender_id = sender_id or account.platform_user_id
        is_outgoing = True
    elif (
        sender_id is None
        and is_outgoing is not True
        and contact is not None
        and (
            chat.chat_type == "personal_chat"
            or is_outgoing is False
            or (
                isinstance(sender_name, str)
                and any(
                    normalize_instagram_text(sender_name).strip().casefold()
                    == normalize_instagram_text(name).strip().casefold()
                    for name in (contact.username, contact.display_name)
                    if name
                )
            )
        )
    ):
        sender_id = sender_id or contact.platform_user_id
        if is_outgoing is None:
            is_outgoing = False

    sender_contact_id = None
    if is_owner:
        sender_contact_id = owner_contact.id
    elif is_outgoing is not True:
        if contact is not None and sender_id == contact.platform_user_id:
            sender_contact_id = contact.id
        elif sender_id is not None:
            sender_contact = _get_or_create_contact(
                session,
                account.id,
                sender_id,
                sender_name,
            )
            if sender_contact is not None:
                sender_contact_id = sender_contact.id
    return {
        "chat_id": chat.id,
        "platform": INSTAGRAM_PLATFORM_ID,
        "message_id": payload["message_id"],
        "source_record_key": payload["source_record_key"],
        "sender_id": sender_id,
        "sender_contact_id": sender_contact_id,
        "sender_name": payload.get("sender_name"),
        "is_outgoing": is_outgoing,
        "message_date": payload.get("message_date"),
        "message_type": payload.get("message_type") or "message",
        "text_content": payload.get("text_content"),
        "reply_to_telegram_message_id": None,
        "source_reply_id": payload.get("source_reply_id"),
        "raw_payload": payload.get("raw_payload") or {},
    }


def _update_existing_message(
    session: Session,
    existing_message: Message,
    values: dict[str, Any],
) -> None:
    if existing_message.sender_name is not None:
        existing_message.sender_name = normalize_instagram_text(
            existing_message.sender_name
        )
    if existing_message.text_content is not None:
        existing_message.text_content = normalize_instagram_text(
            existing_message.text_content
        )
    if values["sender_id"] is not None and existing_message.sender_id is None:
        existing_message.sender_id = values["sender_id"]
    if (
        values["sender_contact_id"] is not None
        and existing_message.sender_contact_id is None
    ):
        existing_message.sender_contact_id = values["sender_contact_id"]
    if existing_message.message_id is None:
        existing_message.message_id = values["message_id"]
    if existing_message.is_outgoing is None and values["is_outgoing"] is not None:
        existing_message.is_outgoing = values["is_outgoing"]
    if session.is_modified(existing_message):
        session.flush()


def _existing_messages(
    session: Session,
    chat: Chat,
    payloads: list[dict[str, Any]],
) -> dict[str, Message]:
    source_keys = [
        payload["source_record_key"]
        for payload in payloads
        if isinstance(payload.get("source_record_key"), str)
    ]
    if not source_keys:
        return {}
    statement = select(Message).where(
        Message.chat_id == chat.id,
        Message.platform == INSTAGRAM_PLATFORM_ID,
        Message.source_record_key.in_(source_keys),
    )
    return {
        message.source_record_key: message
        for message in session.scalars(statement)
        if message.source_record_key is not None
    }


def _insert_messages_for_chat(
    session: Session,
    chat: Chat,
    messages: list[dict[str, Any]],
    contact: Contact | None,
    owner_contact: Contact,
    account: Account,
) -> tuple[int, int]:
    inserted_count = 0
    skipped_count = 0
    for start in range(0, len(messages), MESSAGE_INSERT_BATCH_SIZE):
        batch = messages[start : start + MESSAGE_INSERT_BATCH_SIZE]
        eligible_messages = [
            message
            for message in batch
            if not _is_placeholder_contact_name(message.get("sender_name"))
            and not _is_placeholder_contact_name(chat.title)
        ]
        skipped_count += len(batch) - len(eligible_messages)
        existing_messages = _existing_messages(
            session,
            chat,
            eligible_messages,
        )
        pending_values: list[dict[str, Any]] = []
        for message in eligible_messages:
            values = _message_values(
                session,
                chat,
                message,
                contact,
                owner_contact,
                account,
            )
            existing_message = existing_messages.get(values["source_record_key"])
            if existing_message is not None:
                _update_existing_message(session, existing_message, values)
                skipped_count += 1
            else:
                pending_values.append(values)

        if pending_values:
            inserted = insert_message_batch(session, pending_values)
            inserted_count += inserted
            skipped_count += len(pending_values) - inserted

    return inserted_count, skipped_count


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
    folder_contacts = {
        chat.correspondent_platform_user_id
        for chat in parsed_export.chats
        if chat.correspondent_platform_user_id is not None
    }
    imported_contact_ids = folder_contacts | {parsed_export.owner_platform_user_id}
    logger.info(
        "Parsed Instagram export: %d conversations, %d messages, %d contacts",
        chat_count,
        parsed_message_count,
        len(imported_contact_ids),
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
        file_digest = file_sha256(source_path)
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

        owner_contact, owner_contact_inserted = _ensure_owner_contact(session, account)
        total_messages = 0
        inserted_messages = 0
        skipped_messages = 0
        inserted_contacts = int(owner_contact_inserted)
        for chat in parsed_export.chats:
            persisted_chat = _ensure_chat(session, account.id, chat)
            folder_contact, contact_inserted = _ensure_folder_contact(
                session,
                account.id,
                chat,
            )
            if contact_inserted:
                inserted_contacts += 1
            total_messages += len(chat.messages)
            chat_inserted, chat_skipped = _insert_messages_for_chat(
                session,
                persisted_chat,
                chat.messages,
                folder_contact,
                owner_contact,
                account,
            )
            inserted_messages += chat_inserted
            skipped_messages += chat_skipped

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
            "total_contacts": len(imported_contact_ids),
            "inserted_contacts": inserted_contacts,
            "skipped_contacts": len(imported_contact_ids) - inserted_contacts,
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
