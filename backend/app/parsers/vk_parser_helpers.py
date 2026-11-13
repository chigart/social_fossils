from __future__ import annotations

import base64
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from app.constants import (
    VK_DATE_WITH_MONTH_PATTERN as DATE_WITH_MONTH_PATTERN,
    VK_MAX_PROFILE_FILE_BYTES as MAX_PROFILE_FILE_BYTES,
    VK_MONTH_NUMBERS as MONTH_NUMBERS,
    VK_NUMERIC_DATE_PATTERN as NUMERIC_DATE_PATTERN,
    VK_OWNER_SENDER_LABELS as OWNER_SENDER_LABELS,
)
from app.parsers.vk_parser_html import _Element, _elements, _element_text, _parse_document

__all__ = [
    "OWNER_SENDER_LABELS",
    "_account_details",
    "_archive_sha256",
    "_chat_type",
    "_platform_id_from_href",
    "_stable_record_key",
    "_timestamp_from_header",
]


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


def _archive_sha256(archive_path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(archive_path).open("rb") as source_file:
        while chunk := source_file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_owner_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("owner_id", "ownerId", "user_id", "userId", "id"):
            owner_id = _source_id(value.get(key))
            if owner_id is not None:
                return owner_id
        for child in value.values():
            owner_id = _metadata_owner_id(child)
            if owner_id is not None:
                return owner_id
    elif isinstance(value, list):
        for child in value:
            owner_id = _metadata_owner_id(child)
            if owner_id is not None:
                return owner_id
    return None


def _owner_id_from_metadata(root: _Element) -> str | None:
    for element in _elements(root):
        if element.tag != "meta" or element.attrs.get("name", "").casefold() != "jd":
            continue
        encoded = element.attrs.get("content", "").strip()
        if not encoded:
            continue
        padded = encoded + "=" * (-len(encoded) % 4)
        try:
            payload = json.loads(
                base64.b64decode(
                    padded,
                    altchars=b"-_",
                    validate=True,
                )
            )
        except (ValueError, UnicodeDecodeError):
            continue
        owner_id = _metadata_owner_id(payload)
        if owner_id is not None:
            return owner_id
    return None


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
    owner_platform_user_id = _owner_id_from_metadata(root)
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

    return account_name, account_username, owner_platform_user_id
