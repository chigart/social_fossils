from __future__ import annotations

from typing import Any

from app.vk_parser_helpers import (
    DATE_WITH_MONTH_PATTERN,
    NUMERIC_DATE_PATTERN,
    OWNER_SENDER_LABELS,
    _platform_id_from_href,
    _source_id,
    _stable_record_key,
    _timestamp_from_header,
)
from app.vk_parser_html import _Element, _classes, _elements, _element_text


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
    source_sender_name = sender_name

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

    if (
        is_outgoing is True
        and isinstance(sender_name, str)
        and sender_name.strip().casefold() in OWNER_SENDER_LABELS
    ):
        sender_name = account_name

    source_sender_id = sender_id
    if is_outgoing is True and owner_platform_user_id is not None:
        sender_id = owner_platform_user_id

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
    source_payload = {
        **normalized_payload,
        "sender_id": source_sender_id,
        "sender_name": source_sender_name,
    }
    source_record_key = _stable_record_key(
        chat_id,
        {"source_id": source_id, **source_payload},
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
