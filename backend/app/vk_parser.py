from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from app.vk_parser_helpers import (
    _account_details,
    _chat_type,
)
from app.vk_parser_html import _Element, _classes, _elements, _element_text, _parse_document
from app.vk_parser_messages import _message_elements, _message_payload

MESSAGE_FILE_PATTERN = re.compile(r"messages(?P<offset>\d+)\.html", re.IGNORECASE)
MAX_MESSAGE_FILE_BYTES = 8 * 1024 * 1024
MAX_MESSAGE_DATA_BYTES = 1024 * 1024 * 1024


@dataclass
class ParsedVkChat:
    platform_chat_id: str
    title: str | None
    chat_type: str
    correspondent_platform_user_id: str | None
    correspondent_name: str | None
    messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedVkExport:
    account_name: str
    account_username: str | None
    owner_platform_user_id: str | None
    chats: list[ParsedVkChat] = field(default_factory=list)


def _message_files(
    archive: zipfile.ZipFile,
) -> list[tuple[zipfile.ZipInfo, str, int]]:
    files: list[tuple[zipfile.ZipInfo, str, int]] = []
    for member in archive.infolist():
        if member.is_dir():
            continue
        path = PurePosixPath(member.filename)
        parts = path.parts
        if len(parts) != 3 or parts[0].casefold() != "messages":
            continue
        match = MESSAGE_FILE_PATTERN.fullmatch(path.name)
        if match is None:
            continue
        files.append((member, parts[1], int(match.group("offset"))))
    return sorted(files, key=lambda item: (item[1], item[2], item[0].filename))


def _page_title(root: _Element) -> str | None:
    crumbs = [
        _element_text(element)
        for element in _elements(root)
        if "ui_crumb" in _classes(element)
    ]
    for title in reversed(crumbs):
        if title:
            return title[:300]
    return None


def parse_vk_archive(archive_path: str | Path) -> ParsedVkExport:
    try:
        archive = zipfile.ZipFile(archive_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("VK export must be a valid ZIP archive.") from exc

    with archive:
        message_files = _message_files(archive)
        if not message_files:
            raise ValueError("VK export contains no supported message HTML files.")

        total_size = sum(member.file_size for member, _, _ in message_files)
        if total_size > MAX_MESSAGE_DATA_BYTES:
            raise ValueError(
                "VK message data exceeds the supported limit of "
                f"{MAX_MESSAGE_DATA_BYTES} bytes."
            )

        account_name, account_username, owner_platform_user_id = _account_details(
            archive
        )
        account_name = account_name or "VK account"
        chats_by_id: dict[str, ParsedVkChat] = {}
        identical_message_counts: dict[str, Counter[str]] = {}

        for member, chat_id, _ in message_files:
            if len(chat_id) > 500:
                raise ValueError(
                    "VK conversation identifier exceeds the supported size."
                )
            if member.file_size > MAX_MESSAGE_FILE_BYTES:
                raise ValueError(
                    "VK message HTML file exceeds the supported limit of "
                    f"{MAX_MESSAGE_FILE_BYTES} bytes."
                )
            try:
                with archive.open(member) as message_file:
                    raw_html = message_file.read(MAX_MESSAGE_FILE_BYTES + 1)
            except (OSError, zipfile.BadZipFile) as exc:
                raise ValueError("VK message HTML file could not be read.") from exc
            if len(raw_html) > MAX_MESSAGE_FILE_BYTES:
                raise ValueError(
                    "VK message HTML file exceeds the supported limit of "
                    f"{MAX_MESSAGE_FILE_BYTES} bytes."
                )

            root = _parse_document(raw_html)
            chat = chats_by_id.get(chat_id)
            if chat is None:
                chat = ParsedVkChat(
                    platform_chat_id=chat_id,
                    title=_page_title(root),
                    chat_type=_chat_type(chat_id),
                    correspondent_platform_user_id=(
                        chat_id if _chat_type(chat_id) == "personal_chat" else None
                    ),
                    correspondent_name=None,
                )
                chats_by_id[chat_id] = chat
                identical_message_counts[chat_id] = Counter()
            elif chat.title is None:
                chat.title = _page_title(root)

            occurrences = identical_message_counts[chat_id]
            for raw_message in _message_elements(root):
                serialized = json.dumps(
                    {
                        "data_id": raw_message.attrs.get("data-id"),
                        "text": _element_text(raw_message),
                        "attrs": raw_message.attrs,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                occurrence = occurrences[serialized]
                occurrences[serialized] += 1
                message = _message_payload(
                    chat_id,
                    raw_message,
                    account_name,
                    owner_platform_user_id,
                    occurrence,
                )
                chat.messages.append(message)

                if (
                    chat.correspondent_name is None
                    and message["sender_id"] == chat.correspondent_platform_user_id
                    and isinstance(message["sender_name"], str)
                ):
                    chat.correspondent_name = message["sender_name"]

        if not any(chat.messages for chat in chats_by_id.values()):
            raise ValueError("VK export contains no supported messages.")

    return ParsedVkExport(
        account_name=account_name,
        account_username=account_username,
        owner_platform_user_id=owner_platform_user_id,
        chats=list(chats_by_id.values()),
    )
