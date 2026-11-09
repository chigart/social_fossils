from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.facebook_parser import (
    ParsedFacebookChat,
    parse_facebook_archive,
)
from app.models import Account, CanonicalIdentity, Chat, Contact, ImportSession, Message
from app.platforms import FACEBOOK_PLATFORM_ID

logger = logging.getLogger(__name__)
MESSAGE_INSERT_BATCH_SIZE = 50


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
    owner_platform_user_id: str,
) -> Account:
    accounts = session.scalars(
        select(Account).where(
            Account.platform == FACEBOOK_PLATFORM_ID,
            Account.platform_user_id == owner_platform_user_id,
        )
    ).all()
    if len(accounts) > 1:
        raise ValueError("Multiple Facebook source accounts match this export.")
    if accounts:
        account = accounts[0]
        account.name = account_name
        account.username = account_username
        session.flush()
        return account

    account = Account(
        platform=FACEBOOK_PLATFORM_ID,
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
    parsed_chat: ParsedFacebookChat,
) -> Chat:
    chat = session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.platform == FACEBOOK_PLATFORM_ID,
            Chat.chat_id == parsed_chat.platform_chat_id,
        )
    )
    if chat is not None:
        chat.title = parsed_chat.title or chat.title
        chat.chat_type = parsed_chat.chat_type
        session.flush()
        return chat

    statement = (
        insert(Chat)
        .values(
            account_id=account_id,
            platform=FACEBOOK_PLATFORM_ID,
            chat_id=parsed_chat.platform_chat_id,
            chat_type=parsed_chat.chat_type,
            title=parsed_chat.title,
        )
        .on_conflict_do_nothing(index_elements=["account_id", "chat_id"])
    )
    session.execute(statement)
    session.flush()
    chat = session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.platform == FACEBOOK_PLATFORM_ID,
            Chat.chat_id == parsed_chat.platform_chat_id,
        )
    )
    if chat is None:
        raise RuntimeError("Facebook conversation could not be created.")
    return chat


def _contact_identity(name: str, chat_id: str) -> str:
    normalized_name = " ".join(name.casefold().split())
    scoped_name = f"{chat_id}:{normalized_name}"
    return f"name:{hashlib.sha256(scoped_name.encode('utf-8')).hexdigest()}"


def _get_or_create_contact(
    session: Session,
    account_id: int,
    platform_user_id: str,
    display_name: str | None,
) -> tuple[Contact, bool]:
    existing_contact = session.scalar(
        select(Contact).where(
            Contact.account_id == account_id,
            Contact.platform == FACEBOOK_PLATFORM_ID,
            Contact.platform_user_id == platform_user_id,
        )
    )
    if existing_contact is not None:
        previous_display_name = existing_contact.display_name
        if (
            display_name is not None
            and (
                previous_display_name is None
                or (
                    "\ufffd" in previous_display_name
                    and "\ufffd" not in display_name
                )
            )
        ):
            existing_contact.display_name = display_name
            if previous_display_name is not None:
                session.execute(
                    update(Message)
                    .where(
                        Message.sender_contact_id == existing_contact.id,
                        Message.sender_name == previous_display_name,
                    )
                    .values(sender_name=display_name)
                )
            session.flush()
        return existing_contact, False

    session.execute(
        insert(CanonicalIdentity)
        .values(
            platform=FACEBOOK_PLATFORM_ID,
            platform_user_id=platform_user_id,
        )
        .on_conflict_do_nothing(index_elements=["platform", "platform_user_id"])
    )
    identity = session.scalar(
        select(CanonicalIdentity).where(
            CanonicalIdentity.platform == FACEBOOK_PLATFORM_ID,
            CanonicalIdentity.platform_user_id == platform_user_id,
        )
    )
    if identity is None:
        raise RuntimeError("Facebook contact identity could not be created.")
    session.execute(
        insert(Contact)
        .values(
            account_id=account_id,
            platform=FACEBOOK_PLATFORM_ID,
            platform_user_id=platform_user_id,
            canonical_identity_id=identity.id,
            display_name=display_name,
        )
        .on_conflict_do_nothing(index_elements=["account_id", "platform_user_id"])
    )
    session.flush()
    contact = session.scalar(
        select(Contact).where(
            Contact.account_id == account_id,
            Contact.platform == FACEBOOK_PLATFORM_ID,
            Contact.platform_user_id == platform_user_id,
        )
    )
    if contact is None:
        raise RuntimeError("Facebook contact could not be created.")
    return contact, True


def _ensure_owner_contact(
    session: Session,
    account: Account,
) -> tuple[Contact, bool]:
    if account.platform_user_id is None:
        raise ValueError("Facebook account does not have a platform user ID.")
    return _get_or_create_contact(
        session,
        account.id,
        account.platform_user_id,
        account.name,
    )


def _contact_for_chat(
    session: Session,
    account_id: int,
    parsed_chat: ParsedFacebookChat,
) -> tuple[Contact | None, bool]:
    platform_user_id = parsed_chat.correspondent_platform_user_id
    if platform_user_id is None and parsed_chat.correspondent_name:
        platform_user_id = _contact_identity(
            parsed_chat.correspondent_name,
            parsed_chat.platform_chat_id,
        )
    if platform_user_id is None:
        return None, False
    return _get_or_create_contact(
        session,
        account_id,
        platform_user_id,
        parsed_chat.correspondent_name or parsed_chat.title,
    )


def _message_values(
    session: Session,
    chat: Chat,
    payload: dict[str, Any],
    account: Account,
    owner_contact: Contact,
    chat_contact: Contact | None,
    contact_cache: dict[str, Contact],
    has_owner_identity: bool,
) -> tuple[dict[str, Any], bool]:
    sender_id = payload.get("sender_id")
    sender_name = payload.get("sender_name")
    normalized_name = (
        sender_name.strip().casefold() if isinstance(sender_name, str) else None
    )
    owner_names = (
        {
            name.strip().casefold()
            for name in (account.name, account.username)
            if name
        }
        if has_owner_identity
        else set()
    )
    is_owner = payload.get("is_outgoing") is True or (
        sender_id is not None and sender_id == account.platform_user_id
    ) or (normalized_name is not None and normalized_name in owner_names)
    is_outgoing = payload.get("is_outgoing")
    if is_owner:
        sender_id = sender_id or account.platform_user_id
        is_outgoing = True
    elif (
        has_owner_identity
        and is_outgoing is None
        and (sender_id is not None or sender_name)
    ):
        is_outgoing = False

    sender_contact_id = None
    contact_inserted = False
    if is_owner:
        sender_contact_id = owner_contact.id
    elif is_outgoing is False:
        if sender_id is None and isinstance(sender_name, str) and sender_name.strip():
            if (
                chat_contact is not None
                and chat_contact.display_name is not None
                and sender_name.strip().casefold()
                == chat_contact.display_name.strip().casefold()
            ):
                sender_id = chat_contact.platform_user_id
            else:
                sender_id = _contact_identity(sender_name, chat.chat_id)
        if sender_id is not None:
            contact = contact_cache.get(sender_id)
            if contact is None:
                contact, contact_inserted = _get_or_create_contact(
                    session,
                    account.id,
                    sender_id,
                    sender_name,
                )
                contact_cache[sender_id] = contact
            sender_contact_id = contact.id
        elif chat_contact is not None:
            sender_id = chat_contact.platform_user_id
            sender_contact_id = chat_contact.id

    return (
        {
            "chat_id": chat.id,
            "platform": FACEBOOK_PLATFORM_ID,
            "message_id": payload["message_id"],
            "source_record_key": payload["source_record_key"],
            "sender_id": sender_id,
            "sender_contact_id": sender_contact_id,
            "sender_name": sender_name,
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


def _insert_message_batch(session: Session, values: list[dict[str, Any]]) -> int:
    statement = (
        insert(Message)
        .values(values)
        .on_conflict_do_nothing()
        .returning(Message.id)
    )
    return len(session.execute(statement).scalars().all())


def _insert_messages_for_chat(
    session: Session,
    chat: Chat,
    messages: list[dict[str, Any]],
    account: Account,
    owner_contact: Contact,
    chat_contact: Contact | None,
    contact_cache: dict[str, Contact],
    has_owner_identity: bool,
) -> tuple[int, int, int]:
    inserted_count = 0
    skipped_count = 0
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
                has_owner_identity,
            )
            values.append(message_values)
            inserted_contacts += int(contact_inserted)
        inserted = _insert_message_batch(session, values)
        inserted_count += inserted
        skipped_count += len(values) - inserted
    return inserted_count, skipped_count, inserted_contacts


def import_facebook_export(
    export_path: str | Path,
    *,
    session: Session | None = None,
) -> dict[str, Any]:
    source_path = Path(export_path)
    logger.info("Reading and parsing Facebook export")
    try:
        parsed_export = parse_facebook_archive(source_path)
    except Exception as exc:
        logger.error("Unable to parse Facebook export (%s)", type(exc).__name__)
        raise

    chat_count = len(parsed_export.chats)
    parsed_message_count = sum(len(chat.messages) for chat in parsed_export.chats)
    logger.info(
        "Parsed Facebook export: %d conversations, %d messages",
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
            platform=FACEBOOK_PLATFORM_ID,
            source_filename=source_path.name,
            file_sha256=_file_sha256(source_path),
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
        inserted_contacts = int(owner_contact_inserted)
        total_messages = 0
        inserted_messages = 0
        skipped_messages = 0
        owner_platform_user_id = owner_contact.platform_user_id
        if owner_platform_user_id is None:
            raise RuntimeError("Facebook account contact does not have a platform ID.")
        contact_cache: dict[str, Contact] = {owner_platform_user_id: owner_contact}
        for parsed_chat in parsed_export.chats:
            persisted_chat = _ensure_chat(session, account.id, parsed_chat)
            chat_contact, contact_inserted = _contact_for_chat(
                session,
                account.id,
                parsed_chat,
            )
            if contact_inserted:
                inserted_contacts += 1
            total_messages += len(parsed_chat.messages)
            (
                chat_inserted,
                chat_skipped,
                message_contacts_inserted,
            ) = _insert_messages_for_chat(
                session,
                persisted_chat,
                parsed_chat.messages,
                account,
                owner_contact,
                chat_contact,
                contact_cache,
                parsed_export.has_owner_identity,
            )
            inserted_messages += chat_inserted
            skipped_messages += chat_skipped
            inserted_contacts += message_contacts_inserted

        import_session.total_messages = total_messages
        import_session.inserted_messages = inserted_messages
        import_session.skipped_messages = skipped_messages
        import_session.finished_at = datetime.now(timezone.utc)
        import_session.status = "completed"
        session.commit()
        logger.info(
            "Facebook import completed: %d messages processed, %d inserted, %d skipped",
            total_messages,
            inserted_messages,
            skipped_messages,
        )
        return {
            "platform": FACEBOOK_PLATFORM_ID,
            "account_id": account.id,
            "account_name": account.name,
            "total_messages": total_messages,
            "inserted_messages": inserted_messages,
            "skipped_messages": skipped_messages,
            "inserted_contacts": inserted_contacts,
            "session_id": import_session.id,
        }
    except Exception as exc:
        session.rollback()
        logger.error(
            "Facebook import failed; transaction rolled back (%s)",
            type(exc).__name__,
        )
        raise
    finally:
        if should_close:
            session.close()
