from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import atan2, cos, hypot, pi, sin
from statistics import mean, median
from typing import Any, Callable

from app.constants import (
    CONVERSATION_GAP,
    EMOJI_START_PATTERN,
    ORDINARY_MESSAGE_TYPE,
    RANKING_LIMIT,
    STOP_WORDS,
)
from app.schemas.analytics import (
    ChatInsightSender,
    ChatInsightsStatistics,
    ActivityPeriodCount,
    ConversationActivityStatistics,
    ConversationHandoffCount,
    ConversationParticipantCount,
    EmojiFrequency,
    MessageTypeCount,
    ReactionAuthorPair,
    ReactionReactor,
    ReplyTempoStatistics,
    WordFrequency,
)

__all__ = [
    "_ChatCounts",
    "_ConversationMessage",
    "_MessageTypeSenderCounts",
    "_PairCounts",
    "_ReactorCounts",
    "_SenderCounts",
    "_build_chat_statistics",
    "_build_conversation_activity",
    "_build_reply_tempo",
    "_as_utc",
    "_clean_display_name",
    "_message_category",
    "_positive_count",
    "_rank_emojis",
    "_rank_words",
    "_reaction_records",
    "extract_emojis",
]


@dataclass
class _SenderCounts:
    sender_id: str | None
    name: str | None
    message_count: int = 0
    text_length: int = 0
    activity_times: list[datetime] = field(default_factory=list)
    words: Counter[str] = field(default_factory=Counter)
    emojis: Counter[str] = field(default_factory=Counter)


@dataclass
class _ReactorCounts:
    sender_id: str
    name: str | None
    reaction_count: int = 0
    emojis: Counter[str] = field(default_factory=Counter)


@dataclass
class _PairCounts:
    reactor_id: str
    reactor_name: str | None
    author_id: str
    author_name: str | None
    reaction_count: int = 0
    message_ids: set[int] = field(default_factory=set)


@dataclass
class _ConversationMessage:
    message_id: int
    source_message_id: str | None
    sender_id: str | None
    sender_name: str | None
    message_type: str
    message_date: datetime | None
    reply_to_message_id: str | None


@dataclass
class _MessageTypeSenderCounts:
    sender_id: str | None
    name: str
    count: int = 0


@dataclass
class _ChatCounts:
    chat_id: int
    account_id: int
    platform: str
    source_account_label: str
    title: str | None
    chat_type: str
    message_count: int = 0
    text_length: int = 0
    words: Counter[str] = field(default_factory=Counter)
    emojis: Counter[str] = field(default_factory=Counter)
    senders: dict[str | tuple[str, str] | None, _SenderCounts] = field(
        default_factory=dict
    )
    reactions: Counter[str] = field(default_factory=Counter)
    reactors: dict[str, _ReactorCounts] = field(default_factory=dict)
    pairs: dict[tuple[str, str], _PairCounts] = field(default_factory=dict)
    sender_message_counts: Counter[str] = field(default_factory=Counter)
    message_type_counts: Counter[str] = field(default_factory=Counter)
    with_text_counts: Counter[str] = field(default_factory=Counter)
    message_type_senders: dict[
        str, dict[str | tuple[str, str] | None, _MessageTypeSenderCounts]
    ] = field(default_factory=dict)
    messages: list[_ConversationMessage] = field(default_factory=list)


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
        for emoji, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[
            :RANKING_LIMIT
        ]
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


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _average_activity_time(dates: list[datetime]) -> str | None:
    if not dates:
        return None

    angles = [
        2 * pi * (
            (date.hour * 3600 + date.minute * 60 + date.second)
            / 86400
        )
        for date in dates
    ]
    mean_sine = sum(sin(angle) for angle in angles) / len(angles)
    mean_cosine = sum(cos(angle) for angle in angles) / len(angles)
    if hypot(mean_sine, mean_cosine) < 1e-12:
        return None

    minutes = round(
        (atan2(mean_sine, mean_cosine) % (2 * pi)) * 1440 / (2 * pi)
    ) % 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _build_activity_periods(
    messages: list[_ConversationMessage],
    *,
    labels: tuple[str, ...],
    get_period: Callable[[datetime], int],
) -> list[ActivityPeriodCount]:
    counts = [0] * len(labels)
    for message in messages:
        if (
            message.message_type == ORDINARY_MESSAGE_TYPE
            and message.message_date is not None
        ):
            counts[get_period(_as_utc(message.message_date))] += 1
    return [
        ActivityPeriodCount(period=label, count=count)
        for label, count in zip(labels, counts)
    ]


def _build_reply_tempo(messages: list[_ConversationMessage]) -> ReplyTempoStatistics:
    ordinary_messages = [
        message
        for message in messages
        if message.message_type == ORDINARY_MESSAGE_TYPE
    ]
    by_source_id = {
        message.source_message_id: message
        for message in messages
        if message.source_message_id is not None
    }
    reply_reference_count = 0
    response_times: list[float] = []

    for reply in ordinary_messages:
        if reply.reply_to_message_id is None:
            continue
        reply_reference_count += 1
        original = by_source_id.get(reply.reply_to_message_id)
        if (
            original is None
            or original.message_type != ORDINARY_MESSAGE_TYPE
            or original.sender_id is None
            or reply.sender_id is None
            or original.sender_id == reply.sender_id
            or original.message_date is None
            or reply.message_date is None
        ):
            continue
        elapsed_seconds = (
            _as_utc(reply.message_date) - _as_utc(original.message_date)
        ).total_seconds()
        if elapsed_seconds >= 0:
            response_times.append(elapsed_seconds)

    return ReplyTempoStatistics(
        reply_reference_count=reply_reference_count,
        measured_reply_count=len(response_times),
        average_response_seconds=(
            float(mean(response_times)) if response_times else None
        ),
        longest_response_seconds=max(response_times) if response_times else None,
        median_response_seconds=(
            float(median(response_times)) if response_times else None
        ),
    )


def _build_conversation_activity(
    messages: list[_ConversationMessage],
) -> ConversationActivityStatistics:
    ordinary_messages = [
        message
        for message in messages
        if message.message_type == ORDINARY_MESSAGE_TYPE
    ]
    dated_messages: list[tuple[_ConversationMessage, datetime]] = []
    for message in ordinary_messages:
        message_date = message.message_date
        if message_date is not None:
            dated_messages.append((message, _as_utc(message_date)))
    dated_messages.sort(key=lambda item: (item[1], item[0].message_id))
    undated_count = len(ordinary_messages) - len(dated_messages)
    sessions: list[list[_ConversationMessage]] = []
    previous_message_date: datetime | None = None
    for message, message_date in dated_messages:
        if (
            not sessions
            or previous_message_date is None
            or message_date - previous_message_date >= CONVERSATION_GAP
        ):
            sessions.append([message])
        else:
            sessions[-1].append(message)
        previous_message_date = message_date

    names: dict[str, str] = {}
    for message in ordinary_messages:
        if message.sender_id and message.sender_name:
            names.setdefault(message.sender_id, message.sender_name)

    opening_counts: Counter[str | None] = Counter()
    closing_counts: Counter[str | None] = Counter()
    handoff_counts: Counter[tuple[str, str]] = Counter()
    unattributed_handoff_count = 0
    sender_transition_count = 0
    sender_switch_count = 0
    longest_turn_taking_streak = 0

    for session in sessions:
        opening_counts[session[0].sender_id] += 1
        closing_counts[session[-1].sender_id] += 1
        previous_sender: str | None = None
        current_streak = 0
        for message in session:
            sender_id = message.sender_id
            if sender_id is None:
                previous_sender = None
                current_streak = 0
                continue
            if previous_sender is None:
                current_streak = 1
            else:
                sender_transition_count += 1
                if sender_id != previous_sender:
                    sender_switch_count += 1
                    current_streak += 1
                    longest_turn_taking_streak = max(
                        longest_turn_taking_streak,
                        current_streak,
                    )
                else:
                    current_streak = 1
            previous_sender = sender_id

    for previous_session, next_session in zip(sessions, sessions[1:]):
        previous_closer_id = previous_session[-1].sender_id
        next_opener_id = next_session[0].sender_id
        if previous_closer_id is None or next_opener_id is None:
            unattributed_handoff_count += 1
            continue
        handoff_counts[(previous_closer_id, next_opener_id)] += 1

    def participants(
        counts: Counter[str | None],
    ) -> list[ConversationParticipantCount]:
        return [
            ConversationParticipantCount(
                sender_id=sender_id,
                display_name=(
                    names.get(sender_id, sender_id)
                    if sender_id is not None
                    else "Unknown sender"
                ),
                count=count,
            )
            for sender_id, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0] or ""),
            )
        ]

    handoffs = [
        ConversationHandoffCount(
            previous_closer_id=previous_closer_id,
            previous_closer_name=names.get(previous_closer_id, previous_closer_id),
            next_opener_id=next_opener_id,
            next_opener_name=names.get(next_opener_id, next_opener_id),
            count=count,
        )
        for (previous_closer_id, next_opener_id), count in sorted(
            handoff_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    return ConversationActivityStatistics(
        session_gap_hours=int(CONVERSATION_GAP.total_seconds() / 3600),
        session_count=len(sessions),
        messages_without_timestamp_count=undated_count,
        sender_transition_count=sender_transition_count,
        sender_switch_count=sender_switch_count,
        sender_switch_percentage=(
            100 * sender_switch_count / sender_transition_count
            if sender_transition_count
            else 0
        ),
        longest_turn_taking_streak=longest_turn_taking_streak,
        attributed_handoff_count=sum(handoff_counts.values()),
        unattributed_handoff_count=unattributed_handoff_count,
        opening_senders=participants(opening_counts),
        closing_senders=participants(closing_counts),
        handoffs=handoffs,
    )


def _build_chat_statistics(counts: _ChatCounts) -> ChatInsightsStatistics:
    senders = [
        ChatInsightSender(
            sender_id=sender.sender_id,
            display_name=sender.name or (
                sender.sender_id if sender.sender_id is not None else "Unknown sender"
            ),
            message_count=sender.message_count,
            average_activity_time=_average_activity_time(sender.activity_times),
            text_length=sender.text_length,
            popular_words=_rank_words(sender.words),
            popular_emojis=_rank_emojis(sender.emojis),
        )
        for sender in counts.senders.values()
    ]
    senders.sort(key=lambda sender: (-sender.message_count, sender.display_name.casefold()))

    reactors = [
        ReactionReactor(
            reactor_id=reactor.sender_id,
            display_name=reactor.name or reactor.sender_id,
            reaction_count=reactor.reaction_count,
            popular_emojis=_rank_emojis(reactor.emojis),
        )
        for reactor in counts.reactors.values()
    ]
    reactors.sort(key=lambda reactor: (-reactor.reaction_count, reactor.display_name.casefold()))

    pairs: list[ReactionAuthorPair] = []
    for pair in counts.pairs.values():
        author_message_count = counts.sender_message_counts[pair.author_id]
        observed_message_count = len(pair.message_ids)
        pairs.append(
            ReactionAuthorPair(
                reactor_id=pair.reactor_id,
                reactor_name=pair.reactor_name or pair.reactor_id,
                author_id=pair.author_id,
                author_name=pair.author_name or pair.author_id,
                observed_reaction_count=pair.reaction_count,
                messages_with_observed_reaction_count=observed_message_count,
                author_message_count=author_message_count,
                observed_message_percentage=(
                    100 * observed_message_count / author_message_count
                    if author_message_count
                    else 0
                ),
            )
        )
    pairs.sort(
        key=lambda pair: (
            -pair.observed_message_percentage,
            -pair.messages_with_observed_reaction_count,
            -pair.observed_reaction_count,
            pair.reactor_name.casefold(),
            pair.author_name.casefold(),
        )
    )

    return ChatInsightsStatistics(
        chat_id=counts.chat_id,
        account_id=counts.account_id,
        platform=counts.platform,
        source_account_label=counts.source_account_label,
        title=counts.title,
        chat_type=counts.chat_type,
        ordinary_message_count=counts.message_count,
        average_activity_time=_average_activity_time(
            [
                _as_utc(message.message_date)
                for message in counts.messages
                if message.message_type == ORDINARY_MESSAGE_TYPE
                and message.message_date is not None
            ]
        ),
        weekday_activity=_build_activity_periods(
            counts.messages,
            labels=(
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ),
            get_period=lambda message_date: message_date.weekday(),
        ),
        month_activity=_build_activity_periods(
            counts.messages,
            labels=(
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ),
            get_period=lambda message_date: message_date.month - 1,
        ),
        text_length=counts.text_length,
        popular_words=_rank_words(counts.words),
        popular_emojis=_rank_emojis(counts.emojis),
        senders=senders,
        reaction_count=sum(counts.reactions.values()),
        reaction_emojis=_rank_emojis(counts.reactions),
        reactors=reactors,
        reactor_author_pairs=pairs,
        message_type_breakdown=[
            MessageTypeCount(
                category=category,
                count=count,
                with_text_count=counts.with_text_counts[category],
                senders=[
                    ConversationParticipantCount(
                        sender_id=sender.sender_id,
                        display_name=sender.name,
                        count=sender.count,
                    )
                    for sender in sorted(
                        counts.message_type_senders.get(category, {}).values(),
                        key=lambda sender: (
                            -sender.count,
                            sender.name.casefold(),
                        ),
                    )[:5]
                ]
                if category.casefold() != "text"
                else [],
            )
            for category, count in sorted(
                counts.message_type_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        reply_tempo=_build_reply_tempo(counts.messages),
        conversation_activity=_build_conversation_activity(counts.messages),
    )
