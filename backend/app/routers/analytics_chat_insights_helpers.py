from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from math import atan2, cos, hypot, pi, sin
from statistics import mean, median
from typing import Callable

from app.constants import (
    CONVERSATION_GAP,
    MINIMUM_REPLY_SAMPLES_FOR_AVERAGE,
    ORDINARY_MESSAGE_TYPE,
)
from app.routers.analytics_chat_insights_content import (
    _message_category,
    _rank_emojis,
    _rank_words,
)
from app.routers.analytics_chat_insights_models import (
    _ChatCounts,
    _ConversationMessage,
    _MessageTypeSenderCounts,
    _PairCounts,
    _ReactorCounts,
    _SenderCounts,
)
from app.schemas.analytics import (
    ActivityPeriodCount,
    ChatInsightSender,
    ChatInsightsStatistics,
    ConversationActivityStatistics,
    ConversationHandoffCount,
    ConversationParticipantCount,
    MessageTypeCount,
    ReactionAuthorPair,
    ReactionReactor,
    ReplyTempoStatistics,
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
    "_message_category",
    "_rank_emojis",
    "_rank_words",
]


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


def _dated_conversation_sessions(
    messages: list[_ConversationMessage],
) -> tuple[list[list[_ConversationMessage]], int]:
    ordinary_messages = [
        message
        for message in messages
        if message.message_type == ORDINARY_MESSAGE_TYPE
    ]
    dated_messages = [
        (message, _as_utc(message.message_date))
        for message in ordinary_messages
        if message.message_date is not None
    ]
    dated_messages.sort(key=lambda item: (item[1], item[0].message_id))
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
    return sessions, len(ordinary_messages) - len(dated_messages)


def _build_reply_tempo(messages: list[_ConversationMessage]) -> ReplyTempoStatistics:
    sessions, _ = _dated_conversation_sessions(messages)
    owner_opened_session_count = 0
    measured_contact_reply_session_count = 0
    response_times: list[float] = []
    message_intervals: list[float] = []

    for session in sessions:
        opening_message = session[0]
        if opening_message.message_date is None:
            continue
        previous_message_date = _as_utc(opening_message.message_date)
        for message in session[1:]:
            if message.message_date is None:
                continue
            message_date = _as_utc(message.message_date)
            interval_seconds = (
                message_date - previous_message_date
            ).total_seconds()
            if interval_seconds >= 0:
                message_intervals.append(interval_seconds)
            previous_message_date = message_date

        if (
            opening_message.is_outgoing is not True
            or opening_message.sender_id is None
        ):
            continue
        owner_opened_session_count += 1
        contact_reply = next(
            (
                message
                for message in session[1:]
                if message.is_outgoing is False
            ),
            None,
        )
        if contact_reply is None or contact_reply.message_date is None:
            continue
        elapsed_seconds = (
            _as_utc(contact_reply.message_date)
            - _as_utc(opening_message.message_date)
        ).total_seconds()
        if 0 <= elapsed_seconds < CONVERSATION_GAP.total_seconds():
            response_times.append(elapsed_seconds)
            measured_contact_reply_session_count += 1

    return ReplyTempoStatistics(
        owner_opened_session_count=owner_opened_session_count,
        measured_contact_reply_session_count=measured_contact_reply_session_count,
        message_interval_count=len(message_intervals),
        average_response_seconds=(
            float(mean(response_times))
            if len(response_times) >= MINIMUM_REPLY_SAMPLES_FOR_AVERAGE
            else None
        ),
        longest_response_seconds=max(response_times) if response_times else None,
        median_message_interval_seconds=(
            float(median(message_intervals)) if message_intervals else None
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
    sessions, undated_count = _dated_conversation_sessions(messages)

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
