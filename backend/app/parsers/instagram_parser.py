from __future__ import annotations

import json
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from app.constants import (
    INSTAGRAM_MAX_MESSAGE_DATA_BYTES as MAX_MESSAGE_DATA_BYTES,
    INSTAGRAM_MAX_MESSAGE_FILE_BYTES as MAX_MESSAGE_FILE_BYTES,
    INSTAGRAM_MESSAGE_FILE_PATTERN as MESSAGE_FILE_PATTERN,
    INSTAGRAM_USER_FOLDER_PATTERN as USER_FOLDER_PATTERN,
)
from app.parsers.parser_utils import (
    chat_type as _chat_type,
    source_id as _source_id,
    stable_record_key as _stable_record_key,
    timestamp_from_message as _timestamp_from_message,
)


@dataclass
class ParsedInstagramChat:
    platform_chat_id: str
    correspondent_platform_user_id: str | None
    correspondent_username: str | None
    title: str | None
    chat_type: str
    messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedInstagramExport:
    account_name: str
    account_username: str | None
    owner_platform_user_id: str | None
    chats: list[ParsedInstagramChat] = field(default_factory=list)
    owner_only_chat_ids: set[str] = field(default_factory=set)


def _message_files(archive: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, str]]:
    files: list[tuple[zipfile.ZipInfo, str]] = []
    for member in archive.infolist():
        if member.is_dir():
            continue
        path = PurePosixPath(member.filename)
        parts = path.parts
        try:
            messages_index = parts.index("messages")
        except ValueError:
            continue
        if (
            messages_index + 2 >= len(parts)
            or not MESSAGE_FILE_PATTERN.fullmatch(path.name)
        ):
            continue
        thread_path = "/".join(parts[messages_index + 1 : -1])
        if not thread_path:
            continue
        files.append((member, thread_path))

    def sort_key(item: tuple[zipfile.ZipInfo, str]) -> tuple[str, int, str]:
        member, thread_path = item
        match = MESSAGE_FILE_PATTERN.fullmatch(PurePosixPath(member.filename).name)
        file_number = int(match.group(1) or 1) if match is not None else 1
        return thread_path, file_number, member.filename

    return sorted(files, key=sort_key)


def normalize_instagram_text(value: str) -> str:
    if not any(
        marker in value
        for marker in ("Ã", "Ð", "Ñ", "ð", "\x80", "\x81", "\x8d", "\x9f")
    ):
        return value
    try:
        decoded = value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return decoded if decoded != value else value


def _folder_identity(thread_path: str) -> tuple[str, str | None, str | None]:
    folder_name = thread_path.rsplit("/", 1)[-1]
    match = USER_FOLDER_PATTERN.fullmatch(folder_name)
    if match is None:
        return thread_path, normalize_instagram_text(folder_name), None
    return (
        match.group("user_id"),
        normalize_instagram_text(match.group("username")),
        match.group("user_id"),
    )





def _message_payload(
    chat_id: str,
    raw_message: dict[str, Any],
    occurrence: int,
) -> dict[str, Any]:
    sender_name = raw_message.get("sender_name")
    if not isinstance(sender_name, str) or not sender_name.strip():
        sender_name = None

    text_content = raw_message.get("content")
    if not isinstance(text_content, str):
        text_content = None

    message_type = raw_message.get("type")
    if not isinstance(message_type, str) or not message_type.strip():
        message_type = "message"
    else:
        message_type = message_type.strip()
        if message_type.casefold() == "generic":
            message_type = "message"
    message_type = message_type[:50]

    is_outgoing = raw_message.get("is_outgoing")
    if not isinstance(is_outgoing, bool):
        is_outgoing = raw_message.get("is_sent_by_you")
    if not isinstance(is_outgoing, bool):
        is_outgoing = None

    return {
        "source_record_key": _stable_record_key(chat_id, raw_message, occurrence),
        "sender_id": _source_id(
            raw_message.get("sender_id", raw_message.get("sender_user_id"))
        ),
        "sender_name": (
            normalize_instagram_text(sender_name.strip()) if sender_name else None
        ),
        "is_outgoing": is_outgoing,
        "message_date": _timestamp_from_message(raw_message),
        "message_type": message_type,
        "text_content": (
            normalize_instagram_text(text_content) if text_content is not None else None
        ),
        "source_reply_id": _source_id(raw_message.get("reply_to_message_id")),
        "raw_payload": raw_message,
    }


def _profile_value(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        normalized = normalize_instagram_text(str(value).strip())
        return normalized or None
    return None


def _profile_fields(payload: Any) -> dict[str, str]:
    fields: dict[str, str] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized_key = key.casefold().replace("_", " ").strip()
                target = {
                    "username": "username",
                    "user name": "username",
                    "profile username": "username",
                    "name": "name",
                    "full name": "name",
                    "first name": "first_name",
                    "last name": "last_name",
                    "user id": "user_id",
                    "user id number": "user_id",
                    "user id (numeric)": "user_id",
                    "user_id": "user_id",
                    "profile user id": "user_id",
                    "instagram user id": "user_id",
                    "instagram id": "user_id",
                }.get(normalized_key)
                candidate = _profile_value(child)
                if target is not None and candidate is not None:
                    fields.setdefault(target, candidate)
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return fields


def _account_details(archive: zipfile.ZipFile) -> dict[str, str]:
    details: dict[str, str] = {}
    for member in sorted(archive.infolist(), key=lambda item: item.filename):
        if member.is_dir() or not member.filename.casefold().endswith(".json"):
            continue
        path_parts = {part.casefold() for part in PurePosixPath(member.filename).parts}
        if not path_parts.intersection(
            {"personal_information", "account_information", "profile"}
        ):
            continue
        if member.file_size > 5 * 1024 * 1024:
            continue
        try:
            with archive.open(member) as account_file:
                payload = json.loads(account_file.read(5 * 1024 * 1024 + 1))
        except (UnicodeDecodeError, json.JSONDecodeError, OSError, zipfile.BadZipFile):
            continue
        for key, candidate in _profile_fields(payload).items():
            details.setdefault(key, candidate)
    return details


def parse_instagram_archive(
    archive_path: str | Path,
) -> ParsedInstagramExport:
    try:
        archive = zipfile.ZipFile(archive_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("Instagram export must be a valid ZIP archive.") from exc

    with archive:
        account_details = _account_details(archive)
        message_files = _message_files(archive)
        if not message_files:
            raise ValueError(
                "Instagram export contains no supported message JSON files."
            )

        total_size = sum(member.file_size for member, _ in message_files)
        if total_size > MAX_MESSAGE_DATA_BYTES:
            raise ValueError("Instagram message data exceeds the supported archive size.")

        chats_by_id: dict[str, ParsedInstagramChat] = {}
        identical_message_counts: dict[str, Counter[str]] = {}
        owner_participant_chat_ids: set[str] = set()
        non_owner_participant_chat_ids: set[str] = set()
        owner_names = {
            value.strip().casefold()
            for value in (account_details.get("name"), account_details.get("username"))
            if value
        }
        owner_ids = {
            value
            for value in (account_details.get("user_id"), account_details.get("username"))
            if value
        }
        for member, chat_id in message_files:
            if member.file_size > MAX_MESSAGE_FILE_BYTES:
                raise ValueError("Instagram message JSON file exceeds the supported size.")

            try:
                with archive.open(member) as message_file:
                    raw_json = message_file.read(MAX_MESSAGE_FILE_BYTES + 1)
                    if len(raw_json) > MAX_MESSAGE_FILE_BYTES:
                        raise ValueError(
                            "Instagram message JSON file exceeds the supported size."
                        )
                    payload = json.loads(raw_json.decode("utf-8"))
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                OSError,
                zipfile.BadZipFile,
            ) as exc:
                raise ValueError("Instagram message JSON file is malformed.") from exc

            if not isinstance(payload, dict):
                raise ValueError("Instagram conversation JSON must be an object.")
            raw_messages = payload.get("messages")
            if not isinstance(raw_messages, list):
                raise ValueError("Instagram conversation must contain a messages list.")
            platform_chat_id, correspondent_username, correspondent_user_id = (
                _folder_identity(chat_id)
            )
            if platform_chat_id in owner_ids:
                owner_participant_chat_ids.add(platform_chat_id)
            participants = payload.get("participants")
            if isinstance(participants, list) and participants:
                participant_is_owner = []
                for participant in participants:
                    if not isinstance(participant, dict):
                        participant_is_owner.append(False)
                        continue
                    participant_id = _source_id(
                        participant.get(
                            "user_id",
                            participant.get("id", participant.get("participant_id")),
                        )
                    )
                    participant_name = participant.get("name")
                    if isinstance(participant_name, dict):
                        participant_name = participant_name.get(
                            "value",
                            participant_name.get("full_name"),
                        )
                    participant_is_owner.append(
                        (participant_id is not None and participant_id in owner_ids)
                        or (
                            isinstance(participant_name, str)
                            and participant_name.strip().casefold() in owner_names
                        )
                    )
                if all(participant_is_owner):
                    owner_participant_chat_ids.add(platform_chat_id)
                else:
                    non_owner_participant_chat_ids.add(platform_chat_id)
            chat = chats_by_id.get(platform_chat_id)
            if chat is None:
                title = payload.get("title")
                parsed_chat_type = _chat_type(payload.get("participants"))
                if parsed_chat_type == "private_group":
                    correspondent_username = None
                    correspondent_user_id = None
                chat = ParsedInstagramChat(
                    platform_chat_id=platform_chat_id,
                    correspondent_platform_user_id=correspondent_user_id,
                    correspondent_username=correspondent_username,
                    title=(
                        normalize_instagram_text(title.strip())
                        if isinstance(title, str) and title.strip()
                        else None
                    ),
                    chat_type=parsed_chat_type,
                )
                chats_by_id[platform_chat_id] = chat
                identical_message_counts[platform_chat_id] = Counter()
            else:
                parsed_chat_type = _chat_type(payload.get("participants"))
                if parsed_chat_type != "unknown":
                    chat.chat_type = parsed_chat_type
                if chat.chat_type == "private_group":
                    chat.correspondent_platform_user_id = None
                    chat.correspondent_username = None

            occurrences = identical_message_counts[platform_chat_id]
            for raw_message in raw_messages:
                if not isinstance(raw_message, dict):
                    raise ValueError("Instagram message entries must be JSON objects.")
                serialized = json.dumps(
                    raw_message,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                occurrence = occurrences[serialized]
                occurrences[serialized] += 1
                message = _message_payload(chat_id, raw_message, occurrence)
                message["message_id"] = str(len(chat.messages) + 1)
                chat.messages.append(message)

    account_username = account_details.get("username")
    owner_platform_user_id = account_details.get("user_id") or account_username
    owner_only_chat_ids = owner_participant_chat_ids - non_owner_participant_chat_ids
    account_name = (
        account_details.get("name")
        or account_username
        or (
            f"Instagram {owner_platform_user_id}"
            if owner_platform_user_id
            else "Instagram account"
        )
    )

    return ParsedInstagramExport(
        account_name=account_name,
        account_username=account_username,
        owner_platform_user_id=owner_platform_user_id,
        chats=[
            chat
            for chat in chats_by_id.values()
            if chat.platform_chat_id not in owner_only_chat_ids
        ],
        owner_only_chat_ids=owner_only_chat_ids,
    )
