from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from app.vk_parser_html import _Element, _elements, _element_text, _parse_document

MAX_PROFILE_FILE_BYTES = 5 * 1024 * 1024
OWNER_SENDER_LABELS = {"me", "you", "you (you)", "я", "вы"}
CYRILLIC_USERNAME_TRANSLITERATION = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

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


def _source_id(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    normalized = str(value).strip()
    return normalized if normalized and len(normalized) <= 100 else None


def _username_from_name(name: str) -> str | None:
    words = re.findall(r"[^\W_]+", name.casefold(), flags=re.UNICODE)
    username = "".join(
        "".join(
            CYRILLIC_USERNAME_TRANSLITERATION.get(
                character,
                character if character.isascii() else "",
            )
            for character in word
        ).capitalize()
        for word in words
    )
    return username[:100] or None


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
        if "item" not in element.attrs.get("class", "").split():
            continue
        label = next(
            (
                _element_text(child)
                for child in _elements(element)
                if "item__tertiary" in child.attrs.get("class", "").split()
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
            account_username = value.strip().lstrip("@").strip()[:100] or None
        elif label in id_labels and owner_platform_user_id is None:
            owner_platform_user_id = _source_id(value)

    if account_username is None and account_name is not None:
        account_username = _username_from_name(account_name)

    return account_name, account_username, owner_platform_user_id
