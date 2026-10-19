from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import Chat, Contact, ImportSession, Message, TelegramAccount
from app.telegram_parser import parse_telegram_export

logger = logging.getLogger(__name__)


def get_or_create_account(session, owner_telegram_id: str | None, account_name: str) -> TelegramAccount:
    if owner_telegram_id is None:
        raise ValueError("Missing or invalid Telegram account owner ID in personal_information.user_id")

    existing_accounts = session.scalars(
        select(TelegramAccount).where(TelegramAccount.telegram_user_id == owner_telegram_id)
    ).all()

    if len(existing_accounts) > 1:
        raise ValueError(f"Found multiple Telegram accounts for owner ID {owner_telegram_id}; import cannot continue safely.")

    if existing_accounts:
        return existing_accounts[0]

    account = TelegramAccount(name=account_name, telegram_user_id=owner_telegram_id)
    session.add(account)
    session.flush()
    return account


def ensure_chat(session, account_id: int, parsed_chat) -> Chat:
    chat = session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.telegram_chat_id == parsed_chat.telegram_chat_id,
        )
    )
    if chat is not None:
        return chat

    stmt = insert(Chat).values(
        account_id=account_id,
        telegram_chat_id=parsed_chat.telegram_chat_id,
        chat_type=parsed_chat.chat_type or "unknown",
        title=parsed_chat.title,
    ).on_conflict_do_nothing(index_elements=["account_id", "telegram_chat_id"])
    session.execute(stmt)
    session.flush()
    return session.scalar(
        select(Chat).where(
            Chat.account_id == account_id,
            Chat.telegram_chat_id == parsed_chat.telegram_chat_id,
        )
    )


def get_or_create_contact(session, account_id: int, sender_telegram_id: str, sender_name: str | None) -> Contact | None:
    if not sender_telegram_id:
        return None

    stmt = insert(Contact).values(
        account_id=account_id,
        telegram_user_id=sender_telegram_id,
        display_name=sender_name,
    ).on_conflict_do_nothing(index_elements=["account_id", "telegram_user_id"])
    session.execute(stmt)
    session.flush()
    return session.scalar(
        select(Contact).where(
            Contact.account_id == account_id,
            Contact.telegram_user_id == sender_telegram_id,
        )
    )


def insert_message(session, chat: Chat, payload: dict[str, Any], account_id: int) -> bool:
    message_id = payload.get("telegram_message_id")
    if message_id is None:
        return False

    existing_message = session.scalar(
        select(Message).where(
            Message.chat_id == chat.id,
            Message.telegram_message_id == message_id,
        )
    )
    if existing_message is not None:
        return False

    sender_telegram_id = payload.get("sender_telegram_id")
    sender_contact_id = None
    if sender_telegram_id:
        contact = get_or_create_contact(session, account_id, sender_telegram_id, payload.get("sender_name"))
        if contact is not None:
            sender_contact_id = contact.id

    stmt = insert(Message).values(
        chat_id=chat.id,
        telegram_message_id=str(message_id),
        sender_telegram_id=sender_telegram_id,
        sender_contact_id=sender_contact_id,
        sender_name=payload.get("sender_name"),
        is_outgoing=payload.get("is_outgoing"),
        message_date=payload.get("message_date"),
        message_type=payload.get("message_type") or "message",
        text_content=payload.get("text_content"),
        reply_to_telegram_message_id=payload.get("reply_to_telegram_message_id"),
        raw_payload=payload.get("raw_payload") or {},
    ).on_conflict_do_nothing(index_elements=["chat_id", "telegram_message_id"]) \
      .returning(Message.id)
    inserted = session.execute(stmt).first()
    return inserted is not None


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
        account = get_or_create_account(session, parsed_export.owner_telegram_id, parsed_export.account_name)

        file_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        import_session = ImportSession(
            account_id=account.id,
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

        for chat_index, parsed_chat in enumerate(parsed_export.chats, start=1):
            logger.info(
                "Processing chat %d/%d (%d messages)",
                chat_index,
                chat_count,
                len(parsed_chat.messages),
            )
            chat = ensure_chat(session, account.id, parsed_chat)
            for message_payload in parsed_chat.messages:
                total_messages += 1
                if insert_message(session, chat, message_payload, account.id):
                    inserted_messages += 1
                else:
                    skipped_messages += 1
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
            "owner_telegram_id": account.telegram_user_id,
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
