from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ParsedChat:
    telegram_chat_id: str
    title: str | None
    chat_type: str | None
    messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedTelegramExport:
    account_name: str
    owner_telegram_id: str | None
    chats: list[ParsedChat] = field(default_factory=list)
    contacts: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def normalize_user_id(value: Any) -> str | None:
    """Normalize Telegram user IDs to the canonical 'user<id>' form."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            return None
        if value < 0:
            return None
        return f"user{int(value)}"

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.lower().startswith("user"):
            candidate = candidate[4:]
        if not candidate:
            return None
        if candidate.isdigit():
            return f"user{candidate}"
        try:
            numeric = int(candidate)
        except ValueError:
            return None
        if numeric < 0:
            return None
        return f"user{numeric}"

    return None


def flatten_message_text(value: Any) -> str | None:
    """Flatten Telegram text variants into a plain string."""
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        pieces: list[str] = []
        for item in value:
            flattened = flatten_message_text(item)
            if flattened:
                pieces.append(flattened)
        return "".join(pieces) or None

    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        if "text" in value:
            return flatten_message_text(value["text"])
        if isinstance(value.get("text_entities"), list):
            return flatten_message_text(value["text_entities"])

    return None


def parse_datetime(value: Any) -> datetime | None:
    """Parse a telegram datetime into a timezone-aware UTC datetime when possible."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            return None
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None

        try:
            number = float(candidate)
        except ValueError:
            number = None
        if number is not None and math.isfinite(number):
            try:
                return datetime.fromtimestamp(number, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                pass

        normalized = candidate.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)

    return None


def parse_message_timestamp(message: dict[str, Any]) -> datetime | None:
    if not isinstance(message, dict):
        return None

    unix_value = message.get("date_unixtime")
    parsed = parse_datetime(unix_value)
    if parsed is not None:
        return parsed

    return parse_datetime(message.get("date"))


def extract_account_name(personal_information: dict[str, Any] | None) -> str:
    if not isinstance(personal_information, dict):
        return "Telegram account"

    first_name = personal_information.get("first_name")
    last_name = personal_information.get("last_name")
    name_parts = [part for part in (first_name, last_name) if isinstance(part, str) and part.strip()]
    if name_parts:
        return " ".join(name_parts).strip()
    return "Telegram account"


def extract_sender_id(message: dict[str, Any]) -> str | None:
    if not isinstance(message, dict):
        return None

    for key in ("from_id", "actor_id", "sender_id"):
        if key in message:
            normalized = normalize_user_id(message.get(key))
            if normalized is not None:
                return normalized
    return None


def extract_sender_name(message: dict[str, Any]) -> str | None:
    if not isinstance(message, dict):
        return None

    for key in ("from", "actor", "sender_name"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def determine_is_outgoing(sender_id: str | None, owner_id: str | None) -> bool | None:
    if sender_id is None or owner_id is None:
        return None
    return sender_id == owner_id


def parse_message_record(message: dict[str, Any], owner_telegram_id: str | None) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return None

    telegram_message_id = message.get("id")
    if telegram_message_id is None:
        return None
    try:
        normalized_message_id = str(int(telegram_message_id))
    except (TypeError, ValueError):
        return None

    sender_id = extract_sender_id(message)
    sender_name = extract_sender_name(message)
    parsed_message = {
        "telegram_message_id": normalized_message_id,
        "sender_telegram_id": sender_id,
        "sender_name": sender_name,
        "is_outgoing": determine_is_outgoing(sender_id, owner_telegram_id),
        "message_date": parse_message_timestamp(message),
        "message_type": str(message.get("type") or "message"),
        "text_content": flatten_message_text(message.get("text")) or flatten_message_text(message.get("text_entities")),
        "reply_to_telegram_message_id": None,
        "raw_payload": message,
    }

    for key in ("reply_to_message_id", "reply_to"):
        value = message.get(key)
        if value is not None:
            try:
                parsed_message["reply_to_telegram_message_id"] = str(int(value))
            except (TypeError, ValueError):
                parsed_message["reply_to_telegram_message_id"] = str(value)
            break

    return parsed_message


def parse_telegram_export(data: dict[str, Any]) -> ParsedTelegramExport:
    if not isinstance(data, dict):
        raise ValueError("Telegram export payload must be a JSON object.")

    personal_info = data.get("personal_information") or {}
    if not isinstance(personal_info, dict):
        raise ValueError("personal_information must be an object.")

    contacts = data.get("contacts") or {}
    if not isinstance(contacts, dict):
        raise ValueError("contacts must be an object when present.")

    chats = data.get("chats") or {}
    if not isinstance(chats, dict):
        raise ValueError("chats must be an object.")

    account_name = extract_account_name(personal_info)
    owner_telegram_id = normalize_user_id(personal_info.get("user_id"))

    parsed_chats: list[ParsedChat] = []
    for chat in chats.get("list") or []:
        if not isinstance(chat, dict):
            continue

        telegram_chat_id = chat.get("id")
        if telegram_chat_id is None:
            continue

        try:
            normalized_chat_id = str(int(telegram_chat_id))
        except (TypeError, ValueError):
            normalized_chat_id = str(telegram_chat_id)

        messages: list[dict[str, Any]] = []
        for message in chat.get("messages") or []:
            if not isinstance(message, dict):
                continue
            parsed_message = parse_message_record(message, owner_telegram_id)
            if parsed_message is not None:
                messages.append(parsed_message)

        parsed_chats.append(
            ParsedChat(
                telegram_chat_id=normalized_chat_id,
                title=chat.get("name") or chat.get("title"),
                chat_type=chat.get("type") or "unknown",
                messages=messages,
            )
        )

    contact_entries = contacts.get("list") or []
    contact_records: list[dict[str, Any]] = []
    for contact in contact_entries:
        if not isinstance(contact, dict):
            continue
        contact_records.append(contact)

    return ParsedTelegramExport(
        account_name=account_name,
        owner_telegram_id=owner_telegram_id,
        chats=parsed_chats,
        contacts=contact_records,
        raw=data,
    )
