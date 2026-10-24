import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text


def add_account(
    db_session,
    account_id: int,
    telegram_user_id: str | None,
    *,
    name: str | None = None,
    username: str | None = None,
):
    db_session.execute(
        text(
            "INSERT INTO account "
            "(id, name, username, platform_user_id) "
            "VALUES (:id, :name, :username, :user_id)"
        ),
        {
            "id": account_id,
            "name": name or f"Account {account_id}",
            "username": username,
            "user_id": telegram_user_id,
        },
    )


def add_chat(
    db_session,
    chat_id: int,
    account_id: int,
    telegram_chat_id: str,
    title: str | None = None,
    chat_type: str = "private",
):
    db_session.execute(
        text(
            "INSERT INTO chats (id, account_id, chat_id, title, chat_type) "
            "VALUES (:id, :account_id, :telegram_id, :title, :chat_type)"
        ),
        {
            "id": chat_id,
            "account_id": account_id,
            "telegram_id": telegram_chat_id,
            "title": title,
            "chat_type": chat_type,
        },
    )


def add_contact(
    db_session,
    contact_id: int,
    account_id: int,
    telegram_user_id: str,
    display_name: str,
):
    identity_id = db_session.scalar(
        text(
            "SELECT id FROM canonical_identities "
            "WHERE platform = 'telegram' AND platform_user_id = :telegram_user_id"
        ),
        {"telegram_user_id": telegram_user_id},
    )
    if identity_id is None:
        db_session.execute(
            text(
                "INSERT INTO canonical_identities (platform, platform_user_id) "
                "VALUES ('telegram', :telegram_user_id)"
            ),
            {"telegram_user_id": telegram_user_id},
        )
        identity_id = db_session.scalar(
            text(
                "SELECT id FROM canonical_identities "
                "WHERE platform = 'telegram' AND platform_user_id = :telegram_user_id"
            ),
            {"telegram_user_id": telegram_user_id},
        )
    db_session.execute(
        text(
            "INSERT INTO contacts "
            "(id, account_id, telegram_user_id, canonical_identity_id, display_name) "
            "VALUES (:id, :account_id, :telegram_user_id, :identity_id, :display_name)"
        ),
        {
            "id": contact_id,
            "account_id": account_id,
            "telegram_user_id": telegram_user_id,
            "identity_id": identity_id,
            "display_name": display_name,
        },
    )


def add_message(
    db_session,
    message_id: int,
    chat_id: int,
    message_type: str,
    sender_id: str | None,
    message_date: datetime | None = None,
    is_outgoing: bool | None = None,
    sender_contact_id: int | None = None,
    text_content: str | None = None,
    raw_payload: dict[str, Any] | None = None,
    telegram_message_id: str | None = None,
    reply_to_telegram_message_id: str | None = None,
):
    db_session.execute(
        text(
            "INSERT INTO messages "
            "(id, chat_id, message_id, message_type, sender_id, "
            "message_date, is_outgoing, sender_contact_id, text_content, "
            "reply_to_telegram_message_id, raw_payload) "
            "VALUES (:id, :chat_id, :message_id, :message_type, "
            ":sender_id, :message_date, :is_outgoing, :contact_id, :text_content, "
            ":reply_to_telegram_message_id, :raw_payload)"
        ),
        {
            "id": message_id,
            "chat_id": chat_id,
            "message_id": telegram_message_id or str(message_id),
            "message_type": message_type,
            "sender_id": sender_id,
            "message_date": message_date,
            "is_outgoing": is_outgoing,
            "contact_id": sender_contact_id,
            "text_content": text_content,
            "reply_to_telegram_message_id": reply_to_telegram_message_id,
            "raw_payload": json.dumps(raw_payload or {}),
        },
    )
    db_session.flush()


FORGOTTEN_AS_OF = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
HISTORICAL_ACTIVITY_DATES = [
    datetime(2026, 1, 10, tzinfo=timezone.utc),
    datetime(2026, 2, 10, tzinfo=timezone.utc),
    datetime(2026, 3, 10, tzinfo=timezone.utc),
    datetime(2026, 4, 10, tzinfo=timezone.utc),
    datetime(2026, 6, 10, tzinfo=timezone.utc),
]


def add_forgotten_candidate(
    db_session,
    contact_id: int,
    *,
    account_id: int = 1,
    peer_id: str | None = None,
    name: str | None = None,
    chat_type: str = "personal_chat",
) -> tuple[int, str]:
    peer_id = peer_id or f"user-contact-{contact_id}"
    chat_id = account_id * 10_000 + contact_id
    add_contact(
        db_session,
        contact_id,
        account_id,
        peer_id,
        name or f"Contact {contact_id}",
    )
    add_chat(
        db_session,
        chat_id,
        account_id,
        f"telegram-chat-{chat_id}",
        chat_type=chat_type,
    )
    return chat_id, peer_id


def add_exchanges(
    db_session,
    contact_id: int,
    chat_id: int,
    peer_id: str,
    dates: list[datetime | None],
    *,
    exchanges_per_day: int = 5,
    message_id_start: int = 1,
    owner_id: str = "user-owner",
    owner_text: str | None = "owner",
    contact_text: str | None = "contact",
) -> int:
    message_id = contact_id * 10_000 + message_id_start
    for message_date in dates:
        for _ in range(exchanges_per_day):
            add_message(
                db_session,
                message_id,
                chat_id,
                "message",
                owner_id,
                message_date=message_date,
                is_outgoing=True,
                text_content=owner_text,
            )
            message_id += 1
            add_message(
                db_session,
                message_id,
                chat_id,
                "message",
                peer_id,
                message_date=message_date,
                is_outgoing=False,
                sender_contact_id=contact_id,
                text_content=contact_text,
            )
            message_id += 1
    return message_id - contact_id * 10_000
