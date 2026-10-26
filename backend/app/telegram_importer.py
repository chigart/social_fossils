from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import (
    CanonicalIdentity,
    Chat,
    Contact,
    ImportSession,
    Message,
    Account,
)
from app.platforms import PLATFORM_CONFIGS, TELEGRAM_PLATFORM_ID
from app.telegram_parser import parse_telegram_export

logger = logging.getLogger(__name__)
MESSAGE_INSERT_BATCH_SIZE = 50


def get_or_create_account(
    session,
    owner_telegram_id: str | None,
    account_name: str,
    account_username: str | None = None,
) -> Account:
    if owner_telegram_id is None:
        raise ValueError("Missing or invalid Telegram account owner ID in personal_information.user_id")

    existing_accounts = session.scalars(
        select(Account).where(
            Account.platform == TELEGRAM_PLATFORM_ID,
            Account.platform_user_id == owner_telegram_id,
        )
    ).all()

    if len(existing_accounts) > 1:
        raise ValueError(f"Found multiple Telegram accounts for owner ID {owner_telegram_id}; import cannot continue safely.")

    if existing_accounts:
        account = existing_accounts[0]
        if account_username is not None:
            account.username = account_username
            session.flush()
        return account

    account = Account(
        platform=TELEGRAM_PLATFORM_ID,
        name=account_name,
        username=account_username,
        platform_user_id=owner_telegram_id,
    )
    session.add(account)
    session.flush()
    return account


def ensure_chat(session, account_id: int, parsed_chat) -> Chat:
    chat = session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.platform == TELEGRAM_PLATFORM_ID,
            Chat.chat_id == parsed_chat.telegram_chat_id,
        )
    )
    if chat is not None:
        return chat

    stmt = insert(Chat).values(
        account_id=account_id,
        platform=TELEGRAM_PLATFORM_ID,
        chat_id=parsed_chat.telegram_chat_id,
        chat_type=parsed_chat.chat_type or "unknown",
        title=parsed_chat.title,
    ).on_conflict_do_nothing(index_elements=["account_id", "chat_id"])
    session.execute(stmt)
    session.flush()
    return session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.platform == TELEGRAM_PLATFORM_ID,
            Chat.chat_id == parsed_chat.telegram_chat_id,
        )
    )


def get_or_create_contact(session, account_id: int, sender_telegram_id: str, sender_name: str | None) -> Contact | None:
    if not sender_telegram_id:
        return None

    identity_statement = insert(CanonicalIdentity).values(
        platform=TELEGRAM_PLATFORM_ID,
        platform_user_id=sender_telegram_id,
    ).on_conflict_do_nothing(
        index_elements=["platform", "platform_user_id"]
    )
    session.execute(identity_statement)
    canonical_identity = session.scalar(
        select(CanonicalIdentity).where(
            CanonicalIdentity.platform == TELEGRAM_PLATFORM_ID,
            CanonicalIdentity.platform_user_id == sender_telegram_id,
        )
    )
    if canonical_identity is None:
        raise RuntimeError("Canonical Telegram identity could not be created.")

    stmt = insert(Contact).values(
        account_id=account_id,
        platform=TELEGRAM_PLATFORM_ID,
        platform_user_id=sender_telegram_id,
        canonical_identity_id=canonical_identity.id,
        display_name=sender_name,
    ).on_conflict_do_nothing(index_elements=["account_id", "platform_user_id"])
    session.execute(stmt)
    session.flush()
    contact = session.scalar(
        select(Contact).where(
            Contact.account_id == account_id,
            Contact.platform == TELEGRAM_PLATFORM_ID,
            Contact.platform_user_id == sender_telegram_id,
        )
    )
    if contact is None:
        raise RuntimeError("Telegram contact could not be created.")
    if contact.canonical_identity_id != canonical_identity.id:
        contact.canonical_identity_id = canonical_identity.id
        session.flush()
    return contact


def _message_values(
    session,
    chat: Chat,
    payload: dict[str, Any],
    account_id: int,
    contact_cache: dict[str, Contact],
) -> dict[str, Any] | None:
    message_id = payload.get("telegram_message_id")
    if message_id is None:
        return None

    sender_telegram_id = payload.get("sender_telegram_id")
    sender_contact_id = None
    if sender_telegram_id:
        contact = contact_cache.get(sender_telegram_id)
        if contact is None:
            contact = get_or_create_contact(
                session,
                account_id,
                sender_telegram_id,
                payload.get("sender_name"),
            )
            if contact is not None:
                contact_cache[sender_telegram_id] = contact
        if contact is not None:
            sender_contact_id = contact.id

    return {
        "chat_id": chat.id,
        "platform": TELEGRAM_PLATFORM_ID,
        "message_id": str(message_id),
        "source_record_key": hashlib.sha256(
            f"{TELEGRAM_PLATFORM_ID}:{message_id}".encode("utf-8")
        ).hexdigest(),
        "sender_id": sender_telegram_id,
        "sender_contact_id": sender_contact_id,
        "sender_name": payload.get("sender_name"),
        "is_outgoing": payload.get("is_outgoing"),
        "message_date": payload.get("message_date"),
        "message_type": payload.get("message_type") or "message",
        "text_content": payload.get("text_content"),
        "reply_to_telegram_message_id": payload.get(
            "reply_to_telegram_message_id"
        ),
        "source_reply_id": payload.get("reply_to_telegram_message_id"),
        "raw_payload": payload.get("raw_payload") or {},
    }


def _insert_message_batch(session, values: list[dict[str, Any]]) -> int:
    statement = (
        insert(Message)
        .values(values)
        .on_conflict_do_nothing(index_elements=["chat_id", "message_id"])
        .returning(Message.id)
    )
    return len(session.execute(statement).scalars().all())


def _existing_message_ids(session, chat: Chat, message_ids: list[str]) -> set[str]:
    if not message_ids:
        return set()
    statement = select(Message.message_id).where(
        Message.chat_id == chat.id,
        Message.platform == TELEGRAM_PLATFORM_ID,
        Message.message_id.in_(message_ids),
    )
    return set(session.scalars(statement))


def insert_messages(
    session,
    chat: Chat,
    payloads: Iterable[dict[str, Any]],
    account_id: int,
    contact_cache: dict[str, Contact] | None = None,
) -> int:
    cache = contact_cache if contact_cache is not None else {}
    inserted_count = 0
    payload_iterator = iter(payloads)
    while batch := list(islice(payload_iterator, MESSAGE_INSERT_BATCH_SIZE)):
        message_ids = [
            str(payload["telegram_message_id"])
            for payload in batch
            if payload.get("telegram_message_id") is not None
        ]
        existing_message_ids = _existing_message_ids(session, chat, message_ids)
        pending_values = []
        for payload in batch:
            message_id = payload.get("telegram_message_id")
            if message_id is None or str(message_id) in existing_message_ids:
                continue
            values = _message_values(session, chat, payload, account_id, cache)
            if values is not None:
                pending_values.append(values)
        if pending_values:
            inserted_count += _insert_message_batch(session, pending_values)
    return inserted_count


def insert_message(session, chat: Chat, payload: dict[str, Any], account_id: int) -> bool:
    return insert_messages(session, chat, (payload,), account_id) == 1


def import_telegram_export(export_path: str | Path, *, session=None) -> dict[str, Any]:
    source_path = Path(export_path)
    logger.info("Reading and parsing Telegram export")
    try:
        export_payload = json.loads(source_path.read_text(encoding="utf-8"))
        parsed_export = parse_telegram_export(export_payload)
    except Exception as exc:
        logger.error("Unable to read or parse Telegram export (%s)", type(exc).__name__)
        raise

    chat_count = len(parsed_export.chats)
    parsed_message_count = sum(len(chat.messages) for chat in parsed_export.chats)
    logger.info(
        "Parsed Telegram export: %d chats, %d messages",
        chat_count,
        parsed_message_count,
    )

    if session is None:
        session = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        account = get_or_create_account(
            session,
            parsed_export.owner_telegram_id,
            parsed_export.account_name,
            parsed_export.account_username,
        )

        file_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        import_session = ImportSession(
            account_id=account.id,
            platform=TELEGRAM_PLATFORM_ID,
            source_filename=str(source_path.name),
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
        logger.info("Import session started")

        total_messages = 0
        inserted_messages = 0
        skipped_messages = 0
        contact_cache: dict[str, Contact] = {}

        for chat_index, parsed_chat in enumerate(parsed_export.chats, start=1):
            logger.info(
                "Processing chat %d/%d (%d messages)",
                chat_index,
                chat_count,
                len(parsed_chat.messages),
            )
            chat = ensure_chat(session, account.id, parsed_chat)
            total_messages += len(parsed_chat.messages)
            inserted_for_chat = insert_messages(
                session,
                chat,
                parsed_chat.messages,
                account.id,
                contact_cache,
            )
            inserted_messages += inserted_for_chat
            skipped_messages += len(parsed_chat.messages) - inserted_for_chat
            logger.info(
                "Processed chat %d/%d: %d/%d messages inserted, %d skipped",
                chat_index,
                chat_count,
                inserted_messages,
                total_messages,
                skipped_messages,
            )

        session.flush()
        import_session.total_messages = total_messages
        import_session.inserted_messages = inserted_messages
        import_session.skipped_messages = skipped_messages
        import_session.finished_at = datetime.now(timezone.utc)
        import_session.status = "completed"
        session.commit()
        logger.info(
            "Import completed: %d messages processed, %d inserted, %d skipped",
            total_messages,
            inserted_messages,
            skipped_messages,
        )

        return {
            "account_id": account.id,
            "account_name": account.name,
            "owner_telegram_id": account.platform_user_id,
            "total_messages": total_messages,
            "inserted_messages": inserted_messages,
            "skipped_messages": skipped_messages,
            "session_id": import_session.id,
        }
    except Exception as exc:
        if session is not None:
            session.rollback()
        logger.error("Import failed; transaction rolled back (%s)", type(exc).__name__)
        raise
    finally:
        if should_close:
            session.close()


def import_source_export(
    platform: str,
    export_path: str | Path,
    *,
    session=None,
) -> dict[str, Any]:
    platform_config = PLATFORM_CONFIGS.get(platform)
    if platform_config is None:
        raise ValueError(f"Unsupported import platform: {platform}")

    module_name, function_name = platform_config.importer.split(":", maxsplit=1)
    importer_module = importlib.import_module(module_name)
    importer_function = getattr(importer_module, function_name)
    return importer_function(export_path, session=session)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Import a Telegram Desktop JSON export into the Social Fossils database.")
    parser.add_argument("export_path", help="Path to the Telegram JSON export file")
    args = parser.parse_args()

    result = import_telegram_export(args.export_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
