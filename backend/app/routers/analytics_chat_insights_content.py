from collections import Counter
from typing import Any

from app.constants import (
    EMOJI_START_PATTERN,
    ORDINARY_MESSAGE_TYPE,
    RANKING_LIMIT,
    STOP_WORDS,
)
from app.schemas.analytics import EmojiFrequency, WordFrequency


def _is_emoji_base(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x27BF
        or 0x2300 <= codepoint <= 0x23FF
    )


def _is_emoji_modifier(character: str) -> bool:
    return 0x1F3FB <= ord(character) <= 0x1F3FF


def _is_regional_indicator(character: str) -> bool:
    return 0x1F1E6 <= ord(character) <= 0x1F1FF


def _emoji_end(text: str, start: int) -> int | None:
    character = text[start]

    if character in "#*0123456789":
        cursor = start + 1
        if cursor < len(text) and text[cursor] == "\ufe0f":
            cursor += 1
        return cursor + 1 if cursor < len(text) and text[cursor] == "\u20e3" else None

    if _is_regional_indicator(character):
        if start + 1 < len(text) and _is_regional_indicator(text[start + 1]):
            return start + 2
        return start + 1

    if not _is_emoji_base(character):
        return None

    cursor = start + 1
    while cursor < len(text):
        current = text[cursor]
        if current in ("\ufe0e", "\ufe0f") or _is_emoji_modifier(current):
            cursor += 1
            continue
        if 0xE0020 <= ord(current) <= 0xE007F:
            cursor += 1
            continue
        if (
            current == "\u200d"
            and cursor + 1 < len(text)
            and _is_emoji_base(text[cursor + 1])
        ):
            cursor += 2
            continue
        break
    return cursor


def extract_emojis(text: str) -> list[str]:
    """Return emoji grapheme sequences without requiring a language-specific package."""
    emojis: list[str] = []
    consumed_through = 0
    for candidate in EMOJI_START_PATTERN.finditer(text):
        start = candidate.start()
        if start < consumed_through:
            continue
        end = _emoji_end(text, start)
        if end is None:
            continue
        emojis.append(text[start:end])
        consumed_through = end
    return emojis


def _rank_words(counter: Counter[str]) -> list[WordFrequency]:
    return [
        WordFrequency(word=word, count=count)
        for word, count in sorted(
            (
                (word, count)
                for word, count in counter.items()
                if word not in STOP_WORDS
            ),
            key=lambda item: (-item[1], item[0]),
        )[:RANKING_LIMIT]
    ]


def _rank_emojis(counter: Counter[str]) -> list[EmojiFrequency]:
    return [
        EmojiFrequency(emoji=emoji, count=count)
        for emoji, count in sorted(
            counter.items(), key=lambda item: (-item[1], item[0])
        )[:RANKING_LIMIT]
    ]


def _reaction_records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    reactions = payload.get("reactions")
    if not isinstance(reactions, list):
        return []
    return [reaction for reaction in reactions if isinstance(reaction, dict)]


def _positive_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(value, 0)


def _clean_display_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _message_category(payload: Any, message_type: str, text: str) -> str:
    if message_type == "service":
        return "Service event"
    if message_type != ORDINARY_MESSAGE_TYPE:
        return "Other message type"
    if not isinstance(payload, dict):
        return "Text" if text else "Unclassified"

    media_type = payload.get("media_type")
    normalized_media_type = (
        media_type.casefold().replace("-", "_").replace(" ", "_")
        if isinstance(media_type, str)
        else ""
    )
    media_type_categories = {
        "photo": "Photo",
        "video": "Video",
        "video_file": "Video",
        "video_message": "Video",
        "voice": "Voice message",
        "voice_message": "Voice message",
        "audio": "Audio",
        "audio_file": "Audio",
        "sticker": "Sticker",
        "animation": "Animation / GIF",
        "gif": "Animation / GIF",
        "file": "File",
        "document": "File",
        "location": "Location",
        "live_location": "Location",
        "venue": "Location",
        "poll": "Poll",
        "contact": "Contact",
    }
    if normalized_media_type in media_type_categories:
        return media_type_categories[normalized_media_type]
    if normalized_media_type:
        return "Other media"

    field_categories = (
        (("sticker_emoji", "sticker"), "Sticker"),
        (("animation", "animation_file", "gif"), "Animation / GIF"),
        (("voice_message", "voice_file"), "Voice message"),
        (("audio_file", "audio"), "Audio"),
        (("video", "video_file", "video_message"), "Video"),
        (("photo", "photo_file"), "Photo"),
        (("location", "live_location", "venue"), "Location"),
        (("poll",), "Poll"),
        (("contact_information",), "Contact"),
    )
    for fields, category in field_categories:
        if any(field_name in payload for field_name in fields):
            return category

    mime_type = payload.get("mime_type")
    if isinstance(mime_type, str):
        if mime_type.startswith("image/"):
            return "Photo"
        if mime_type.startswith("video/"):
            return "Video"
        if mime_type.startswith("audio/"):
            return "Audio"

    if "file" in payload:
        return "File"
    return "Text" if text else "Unclassified"
