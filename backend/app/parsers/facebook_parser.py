from __future__ import annotations

import hashlib
import json
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from app.constants import (
    FACEBOOK_MAX_MESSAGE_DATA_BYTES as MAX_MESSAGE_DATA_BYTES,
    FACEBOOK_MAX_MESSAGE_FILE_BYTES as MAX_MESSAGE_FILE_BYTES,
    FACEBOOK_MAX_PROFILE_FILE_BYTES as MAX_PROFILE_FILE_BYTES,
    FACEBOOK_MESSAGE_FILE_PATTERN as MESSAGE_FILE_PATTERN,
    FACEBOOK_USER_FOLDER_PATTERN as USER_FOLDER_PATTERN,
)
from app.parsers.parser_utils import (
    source_id as _source_id,
    stable_record_key as _stable_record_key,
    timestamp_from_message as _timestamp_from_message,
)


@dataclass
class ParsedFacebookChat:
    platform_chat_id: str
    title: str | None
    chat_type: str
    correspondent_platform_user_id: str | None
    correspondent_name: str | None
    messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedFacebookExport:
    account_name: str
    account_username: str | None
    owner_platform_user_id: str
    has_owner_identity: bool
    chats: list[ParsedFacebookChat] = field(default_factory=list)


def _message_files(
    archive: zipfile.ZipFile,
) -> list[tuple[zipfile.ZipInfo, str]]:
    files: list[tuple[zipfile.ZipInfo, str]] = []
    for member in archive.infolist():
        if member.is_dir():
            continue
        path = PurePosixPath(member.filename)
        parts = path.parts
        try:
            messages_index = next(
                index
                for index, part in enumerate(parts)
                if part.casefold() == "messages"
            )
        except StopIteration:
            continue
        if (
            messages_index + 2 >= len(parts)
            or not MESSAGE_FILE_PATTERN.fullmatch(path.name)
        ):
            continue
        thread_path = "/".join(parts[messages_index + 1 : -1])
        files.append((member, thread_path))

    def sort_key(item: tuple[zipfile.ZipInfo, str]) -> tuple[str, int, str]:
        member, thread_path = item
        match = MESSAGE_FILE_PATTERN.fullmatch(PurePosixPath(member.filename).name)
        file_number = int(match.group(1) or 1) if match is not None else 1
        return thread_path, file_number, member.filename

    return sorted(files, key=sort_key)


def _normalize_text(value: str) -> str:
    if not (
        any(
            marker in value
            for marker in (
                "Ã",
                "Ð",
                "Ñ",
                "ð",
                "à",
                "á",
                "Â",
                "\x80",
                "\x81",
                "\x83",
                "\x8d",
                "\x9f",
            )
        )
        or any("\u00e3" <= character <= "\u00ef" for character in value)
    ):
        return value
    try:
        encoded = value.encode("latin-1")
    except UnicodeEncodeError:
        return value
    try:
        decoded = encoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        if exc.reason != "unexpected end of data" or exc.end != len(encoded):
            return value
        try:
            decoded_prefix = encoded[: exc.start].decode("utf-8")
        except UnicodeDecodeError:
            return value
        if not any(not character.isascii() for character in decoded_prefix):
            return value
        decoded = encoded.decode("utf-8", errors="replace")
    return decoded if decoded != value else value


def _folder_user_id(thread_path: str) -> str | None:
    folder_name = thread_path.rsplit("/", 1)[-1]
    match = USER_FOLDER_PATTERN.fullmatch(folder_name)
    return match.group("user_id") if match is not None else None


def _message_payload(
    chat_id: str,
    raw_message: dict[str, Any],
    occurrence: int,
) -> dict[str, Any]:
    sender_name = raw_message.get("sender_name")
    if not isinstance(sender_name, str) or not sender_name.strip():
        sender_name = None

    content = raw_message.get("content")
    if not isinstance(content, str):
        content = None

    message_type = raw_message.get("type")
    if not isinstance(message_type, str) or not message_type.strip():
        message_type = "message"
    else:
        message_type = message_type.strip()
        if message_type.casefold() == "generic":
            message_type = "message"

    is_outgoing = raw_message.get("is_outgoing")
    if not isinstance(is_outgoing, bool):
        is_outgoing = raw_message.get("is_sent_by_you")
    if not isinstance(is_outgoing, bool):
        is_outgoing = None

    normalized_sender_name = (
        _normalize_text(sender_name).strip() if sender_name else None
    )

    return {
        "source_record_key": _stable_record_key(chat_id, raw_message, occurrence),
        "sender_id": _source_id(
            raw_message.get("sender_id", raw_message.get("sender_user_id"))
        ),
        "sender_name": normalized_sender_name,
        "is_outgoing": is_outgoing,
        "message_date": _timestamp_from_message(raw_message),
        "message_type": message_type[:50],
        "text_content": _normalize_text(content) if content is not None else None,
        "source_reply_id": _source_id(
            raw_message.get("reply_to_message_id")
        ),
        "raw_payload": raw_message,
    }


def _is_owner_participant(
    participant: dict[str, Any],
    account_details: dict[str, str],
) -> bool:
    participant_name = _profile_value(participant.get("name"))
    participant_id = _source_id(
        participant.get("user_id", participant.get("id"))
    )
    owner_names = {
        value.casefold()
        for value in (account_details.get("name"), account_details.get("username"))
        if value
    }
    owner_ids = {
        value
        for value in (account_details.get("user_id"), account_details.get("username"))
        if value
    }
    return (
        participant_name is not None
        and participant_name.casefold() in owner_names
    ) or (participant_id is not None and participant_id in owner_ids)


def _chat_type(participants: Any, account_details: dict[str, str]) -> str:
    if not isinstance(participants, list):
        return "unknown"

    identities: set[tuple[str, str] | tuple[str, int]] = set()
    for index, participant in enumerate(participants):
        if isinstance(participant, dict):
            if _is_owner_participant(participant, account_details):
                identities.add(("owner", ""))
                continue
            participant_id = _source_id(
                participant.get("user_id", participant.get("id"))
            )
            if participant_id is not None:
                identities.add(("id", participant_id))
                continue
            participant_name = _profile_value(participant.get("name"))
            if participant_name is not None:
                identities.add(("name", participant_name.casefold()))
                continue
        identities.add(("unknown", index))

    if len(identities) < 2:
        return "unknown"
    return "private_group" if len(identities) > 2 else "personal_chat"


def _message_participant_identities(
    messages: list[Any],
    account_details: dict[str, str],
) -> set[tuple[str, str]]:
    owner_names = {
        value.casefold()
        for value in (account_details.get("name"), account_details.get("username"))
        if value
    }
    owner_ids = {
        value
        for value in (account_details.get("user_id"), account_details.get("username"))
        if value
    }
    identities: set[tuple[str, str]] = set()
    for message in messages:
        if not isinstance(message, dict):
            continue
        sender_id = _source_id(
            message.get("sender_id", message.get("sender_user_id"))
        )
        sender_name = _profile_value(message.get("sender_name"))
        is_outgoing = message.get("is_outgoing", message.get("is_sent_by_you"))
        if (
            is_outgoing is True
            or (sender_id is not None and sender_id in owner_ids)
            or (
                sender_name is not None
                and sender_name.casefold() in owner_names
            )
        ):
            identities.add(("owner", ""))
        elif sender_name is not None:
            identities.add(("name", sender_name.casefold()))
        elif sender_id is not None:
            identities.add(("id", sender_id))
    return identities


def _profile_value(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("value", value.get("full_name"))
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        normalized = _normalize_text(str(value)).strip()
        return normalized or None
    return None


def _profile_fields(payload: Any) -> dict[str, str]:
    fields: dict[str, str] = {}
    key_map = {
        "name": "name",
        "full name": "name",
        "username": "username",
        "user name": "username",
        "user id": "user_id",
        "user id number": "user_id",
        "profile id": "user_id",
        "facebook id": "user_id",
        "facebook user id": "user_id",
    }

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized_key = key.casefold().replace("_", " ").strip()
                target = key_map.get(normalized_key)
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
            {"profile_information", "personal_information", "account_information"}
        ):
            continue
        if member.file_size > MAX_PROFILE_FILE_BYTES:
            continue
        try:
            with archive.open(member) as profile_file:
                payload = json.loads(profile_file.read(MAX_PROFILE_FILE_BYTES + 1))
        except (UnicodeDecodeError, json.JSONDecodeError, OSError, zipfile.BadZipFile):
            continue
        for key, value in _profile_fields(payload).items():
            details.setdefault(key, value)
    return details


def _archive_sha256(archive_path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(archive_path).open("rb") as source_file:
        while chunk := source_file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_facebook_archive(
    archive_path: str | Path,
) -> ParsedFacebookExport:
    try:
        archive = zipfile.ZipFile(archive_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("Facebook export must be a valid ZIP archive.") from exc

    with archive:
        account_details = _account_details(archive)
        message_files = _message_files(archive)
        if not message_files:
            raise ValueError("Facebook export contains no supported message JSON files.")

        total_size = sum(member.file_size for member, _ in message_files)
        if total_size > MAX_MESSAGE_DATA_BYTES:
            raise ValueError(
                "Facebook message data exceeds the supported limit of "
                f"{MAX_MESSAGE_DATA_BYTES} bytes."
            )

        chats_by_id: dict[str, ParsedFacebookChat] = {}
        identical_message_counts: dict[str, Counter[str]] = {}
        observed_participants: dict[str, set[tuple[str, str]]] = {}
        for member, chat_id in message_files:
            if member.file_size > MAX_MESSAGE_FILE_BYTES:
                raise ValueError(
                    "Facebook message JSON file exceeds the supported limit of "
                    f"{MAX_MESSAGE_FILE_BYTES} bytes."
                )
            try:
                with archive.open(member) as message_file:
                    raw_json = message_file.read(MAX_MESSAGE_FILE_BYTES + 1)
                    if len(raw_json) > MAX_MESSAGE_FILE_BYTES:
                        raise ValueError(
                            "Facebook message JSON file exceeds the supported limit of "
                            f"{MAX_MESSAGE_FILE_BYTES} bytes."
                        )
                    payload = json.loads(raw_json.decode("utf-8"))
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                OSError,
                zipfile.BadZipFile,
            ) as exc:
                raise ValueError("Facebook message JSON file is malformed.") from exc

            if not isinstance(payload, dict):
                raise ValueError("Facebook conversation JSON must be an object.")
            raw_messages = payload.get("messages")
            if not isinstance(raw_messages, list):
                raise ValueError("Facebook conversation must contain a messages list.")

            participants = payload.get("participants")
            chat_type = _chat_type(participants, account_details)
            chat_participants = observed_participants.setdefault(chat_id, set())
            chat_participants.update(
                _message_participant_identities(raw_messages, account_details)
            )
            if chat_type == "unknown":
                if len(chat_participants) == 2:
                    chat_type = "personal_chat"
                elif len(chat_participants) > 2:
                    chat_type = "private_group"
            correspondent = (
                next(
                    (
                        participant
                        for participant in participants
                        if isinstance(participant, dict)
                        and not _is_owner_participant(
                            participant,
                            account_details,
                        )
                    ),
                    None,
                )
                if isinstance(participants, list) and account_details
                else None
            )
            correspondent_id = (
                _source_id(
                    correspondent.get(
                        "user_id",
                        correspondent.get("id"),
                    )
                )
                if correspondent is not None
                else None
            )
            chat = chats_by_id.get(chat_id)
            folder_user_id = (
                _folder_user_id(chat_id)
                if chat_type == "personal_chat"
                or (chat is not None and chat.chat_type == "personal_chat")
                else None
            )
            if chat is None:
                title = payload.get("title")
                correspondent_name = (
                    _profile_value(correspondent.get("name"))
                    if correspondent is not None
                    else None
                )
                chat = ParsedFacebookChat(
                    platform_chat_id=chat_id,
                    title=_profile_value(title),
                    chat_type=chat_type,
                    correspondent_platform_user_id=folder_user_id or correspondent_id,
                    correspondent_name=correspondent_name,
                )
                chats_by_id[chat_id] = chat
                identical_message_counts[chat_id] = Counter()
            elif chat_type != "unknown":
                chat.chat_type = (
                    "private_group"
                    if "private_group" in (chat.chat_type, chat_type)
                    else "personal_chat"
                )

            occurrences = identical_message_counts[chat_id]
            for raw_message in raw_messages:
                if not isinstance(raw_message, dict):
                    raise ValueError("Facebook message entries must be JSON objects.")
                serialized = json.dumps(
                    raw_message,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                occurrence = occurrences[serialized]
                occurrences[serialized] += 1
                message = _message_payload(chat_id, raw_message, occurrence)
                if (
                    folder_user_id is not None
                    and (
                        message["sender_id"] == correspondent_id
                        or (
                            chat.correspondent_name is not None
                            and message["sender_name"] is not None
                            and message["sender_name"].casefold()
                            == chat.correspondent_name.casefold()
                        )
                    )
                ):
                    message["sender_id"] = folder_user_id
                message["message_id"] = f"facebook:{message['source_record_key']}"
                chat.messages.append(message)

    account_name = (
        account_details.get("name")
        or account_details.get("username")
        or "Facebook account"
    )
    account_username = account_details.get("username")
    owner_platform_user_id = (
        account_details.get("user_id")
        or account_username
        or f"archive:{_archive_sha256(archive_path)}"
    )
    named_chats = [
        chat
        for chat in chats_by_id.values()
        if chat.title is not None and chat.title.strip()
    ]
    return ParsedFacebookExport(
        account_name=account_name,
        account_username=account_username,
        owner_platform_user_id=owner_platform_user_id,
        has_owner_identity=bool(account_details),
        chats=named_chats,
    )
