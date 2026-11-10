from __future__ import annotations

import codecs
import hashlib
import json
import re
import zipfile
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit


MESSAGE_FILE_PATTERN = re.compile(r"messages(?P<offset>\d+)\.html", re.IGNORECASE)
MAX_MESSAGE_FILE_BYTES = 8 * 1024 * 1024
MAX_MESSAGE_DATA_BYTES = 1024 * 1024 * 1024
MAX_PROFILE_FILE_BYTES = 5 * 1024 * 1024
OWNER_SENDER_LABELS = {"me", "you", "you (you)", "я", "вы"}

MONTH_NUMBERS = {
    "января": 1,
    "янв": 1,
    "февраля": 2,
    "февраль": 2,
    "фев": 2,
    "марта": 3,
    "март": 3,
    "мар": 3,
    "апреля": 4,
    "апрель": 4,
    "апр": 4,
    "мая": 5,
    "май": 5,
    "июня": 6,
    "июнь": 6,
    "июн": 6,
    "июля": 7,
    "июль": 7,
    "июл": 7,
    "августа": 8,
    "август": 8,
    "авг": 8,
    "сентября": 9,
    "сентябрь": 9,
    "сен": 9,
    "сент": 9,
    "октября": 10,
    "октябрь": 10,
    "окт": 10,
    "ноября": 11,
    "ноябрь": 11,
    "ноя": 11,
    "нояб": 11,
    "декабря": 12,
    "декабрь": 12,
    "дек": 12,
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

DATE_WITH_MONTH_PATTERN = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month>[^\W\d_]+)\s+"
    r"(?P<year>\d{4})\D{0,12}(?P<hour>\d{1,2}):(?P<minute>\d{2})"
    r"(?::(?P<second>\d{2}))?",
    re.IGNORECASE,
)
NUMERIC_DATE_PATTERN = re.compile(
    r"(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{4})"
    r"\D{0,12}(?P<hour>\d{1,2}):(?P<minute>\d{2})"
    r"(?::(?P<second>\d{2}))?"
)


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


@dataclass
class _Element:
    tag: str
    attrs: dict[str, str]
    children: list[_Element | str] = field(default_factory=list)


class _DocumentParser(HTMLParser):
    _VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = _Element(
            tag,
            {key: value or "" for key, value in attrs},
        )
        self.stack[-1].children.append(element)
        if tag not in self._VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.stack[-1].children.append(
            _Element(tag, {key: value or "" for key, value in attrs})
        )

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self.stack[-1].tag not in {"script", "style"}:
            self.stack[-1].children.append(data)


def _elements(root: _Element) -> Iterator[_Element]:
    pending = [root]
    while pending:
        element = pending.pop()
        yield element
        pending.extend(
            child
            for child in reversed(element.children)
            if isinstance(child, _Element)
        )


def _classes(element: _Element) -> set[str]:
    return set(element.attrs.get("class", "").split())


def _element_text(
    element: _Element,
    *,
    excluded_classes: set[str] | None = None,
) -> str:
    excluded = excluded_classes or set()
    pieces: list[str] = []
    pending: list[_Element | str] = [element]
    while pending:
        child = pending.pop()
        if isinstance(child, str):
            pieces.append(child)
            continue
        if _classes(child) & excluded:
            continue
        if child.tag == "br":
            pieces.append("\n")
        else:
            pending.extend(reversed(child.children))

    lines = [
        re.sub(r"[^\S\n]+", " ", line).strip()
        for line in "".join(pieces).replace("\r", "\n").split("\n")
    ]
    return "\n".join(line for line in lines if line)


def _decode_html(raw_html: bytes) -> str:
    declaration = re.search(
        rb"<meta\b[^>]*\bcharset\s*=\s*[\"']?\s*([A-Za-z0-9._-]+)",
        raw_html[:8192],
        re.IGNORECASE,
    )
    encoding = declaration.group(1).decode("ascii") if declaration else "utf-8"
    try:
        codec = codecs.lookup(encoding).name
    except LookupError as exc:
        raise ValueError("VK export declares an unsupported HTML encoding.") from exc
    return raw_html.decode(codec, errors="replace")


def _parse_document(raw_html: bytes) -> _Element:
    parser = _DocumentParser()
    parser.feed(_decode_html(raw_html))
    parser.close()
    return parser.root


def _source_id(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    normalized = str(value).strip()
    return normalized if normalized and len(normalized) <= 100 else None


def _platform_id_from_href(href: str) -> str | None:
    path = urlsplit(href).path.strip("/")
    match = re.fullmatch(r"(?:id|club|public)(-?\d+)", path, re.IGNORECASE)
    if match is not None:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{1,99}", path):
        if path.casefold() not in {
            "feed",
            "friends",
            "im",
            "messages",
            "profile",
            "settings",
            "wall",
        }:
            return path
    return None


def _timestamp_from_header(header: _Element) -> datetime | None:
    header_text = _element_text(header)
    match = NUMERIC_DATE_PATTERN.search(header_text)
    if match is not None:
        day = int(match.group("day"))
        month = int(match.group("month"))
        year = int(match.group("year"))
    else:
        match = DATE_WITH_MONTH_PATTERN.search(header_text)
        if match is None:
            return None
        month = MONTH_NUMBERS.get(match.group("month").casefold())
        if month is None:
            return None
        day = int(match.group("day"))
        year = int(match.group("year"))

    try:
        return datetime(
            year,
            month,
            day,
            int(match.group("hour")),
            int(match.group("minute")),
            int(match.group("second") or 0),
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None


def _stable_record_key(
    chat_id: str,
    raw_message: dict[str, Any],
    occurrence: int,
) -> str:
    def serialize_value(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(
            "Unsupported source value for VK message key: "
            f"{type(value).__name__}"
        )

    serialized = json.dumps(
        [chat_id, raw_message, occurrence],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=serialize_value,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _chat_type(chat_id: str) -> str:
    try:
        numeric_id = int(chat_id)
    except ValueError:
        return "unknown"
    if numeric_id < 0 or numeric_id >= 2_000_000_000:
        return "private_group"
    return "personal_chat"


def _account_details(
    archive: zipfile.ZipFile,
) -> tuple[str | None, str | None, str | None]:
    profile_member = next(
        (
            member
            for member in archive.infolist()
            if PurePosixPath(member.filename).as_posix().casefold()
            == "profile/page-info.html"
        ),
        None,
    )
    if profile_member is None or profile_member.file_size > MAX_PROFILE_FILE_BYTES:
        return None, None, None

    try:
        with archive.open(profile_member) as profile_file:
            root = _parse_document(
                profile_file.read(MAX_PROFILE_FILE_BYTES + 1)
            )
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("VK profile information file is malformed.") from exc

    account_name = None
    account_username = None
    owner_platform_user_id = None
    name_labels = {"full name", "name", "полное имя", "имя"}
    username_labels = {"username", "user name", "имя пользователя"}
    id_labels = {"user id", "vk id", "id", "ид", "идентификатор"}
    for element in _elements(root):
        if "item" not in _classes(element):
            continue
        label = next(
            (
                _element_text(child)
                for child in _elements(element)
                if "item__tertiary" in _classes(child)
            ),
            "",
        ).casefold()
        value = _element_text(
            element,
            excluded_classes={"item__tertiary"},
        )
        if not value:
            continue
        if label in name_labels and account_name is None:
            account_name = value[:200]
        elif label in username_labels and account_username is None:
            account_username = value.lstrip("@")[:100]
        elif label in id_labels and owner_platform_user_id is None:
            owner_platform_user_id = _source_id(value)

    return account_name, account_username, owner_platform_user_id


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


def _message_elements(root: _Element) -> list[_Element]:
    return [
        element
        for element in _elements(root)
        if "message" in _classes(element)
    ]


def _attachment_metadata(message: _Element) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    for element in _elements(message):
        if "attachment" not in _classes(element):
            continue
        metadata: dict[str, str] = {}
        for child in _elements(element):
            classes = _classes(child)
            if "attachment__description" in classes:
                description = _element_text(child)
                if description:
                    metadata["description"] = description[:500]
            elif "attachment__link" in classes:
                label = _element_text(child)
                if label:
                    metadata["label"] = label[:500]
        attachments.append(metadata)
    return attachments


def _message_payload(
    chat_id: str,
    raw_message: _Element,
    account_name: str,
    owner_platform_user_id: str | None,
    occurrence: int,
) -> dict[str, Any]:
    header = next(
        (
            element
            for element in _elements(raw_message)
            if "message__header" in _classes(element)
        ),
        None,
    )
    sender_link = (
        next(
            (
                element
                for element in _elements(header)
                if element.tag == "a" and element.attrs.get("href")
            ),
            None,
        )
        if header is not None
        else None
    )
    sender_name = _element_text(sender_link) if sender_link is not None else None
    sender_id = (
        _platform_id_from_href(sender_link.attrs["href"])
        if sender_link is not None
        else None
    )
    if sender_name is None and header is not None:
        header_text = _element_text(header)
        date_match = NUMERIC_DATE_PATTERN.search(header_text)
        if date_match is None:
            date_match = DATE_WITH_MONTH_PATTERN.search(header_text)
        if date_match is not None:
            sender_name = header_text[: date_match.start()].strip(" \t\n·,-")
        else:
            sender_name = header_text
        sender_name = sender_name or None
    if sender_name is not None:
        sender_name = sender_name[:300]

    content_parts = [
        _element_text(
            child,
            excluded_classes={"kludges", "attachment"},
        )
        for child in raw_message.children
        if isinstance(child, _Element)
        and not (
            _classes(child)
            & {"message__header", "kludges", "attachment"}
        )
    ]
    text_content = "\n".join(part for part in content_parts if part).strip() or None
    attachments = _attachment_metadata(raw_message)

    is_outgoing: bool | None = None
    if (
        isinstance(sender_name, str)
        and sender_name.strip().casefold() in OWNER_SENDER_LABELS
    ):
        is_outgoing = True
    elif sender_id is not None and owner_platform_user_id is not None:
        is_outgoing = sender_id == owner_platform_user_id
    elif (
        isinstance(sender_name, str)
        and sender_name.strip().casefold() == account_name.strip().casefold()
    ):
        is_outgoing = True
    elif sender_link is not None:
        is_outgoing = False
    else:
        is_outgoing = False if sender_id is not None else None

    source_id = _source_id(raw_message.attrs.get("data-id"))
    normalized_payload = {
        "sender_id": sender_id,
        "sender_name": sender_name,
        "is_outgoing": is_outgoing,
        "message_date": _timestamp_from_header(header) if header is not None else None,
        "message_type": "attachment" if attachments and text_content is None else "message",
        "text_content": text_content,
        "attachments": attachments,
    }
    source_record_key = _stable_record_key(
        chat_id,
        {"source_id": source_id, **normalized_payload},
        occurrence,
    )
    message_id = source_id or f"vk:{source_record_key}"
    return {
        "message_id": message_id,
        "source_record_key": source_record_key,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "is_outgoing": is_outgoing,
        "message_date": normalized_payload["message_date"],
        "message_type": normalized_payload["message_type"],
        "text_content": text_content,
        "source_reply_id": _source_id(
            raw_message.attrs.get("data-reply-to")
        ),
        "raw_payload": {
            "source_id": source_id,
            "attachments": attachments,
        },
    }


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
                raise ValueError("VK conversation identifier exceeds the supported size.")
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
