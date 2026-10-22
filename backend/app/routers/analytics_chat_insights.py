from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics_stop_words import STOP_WORDS
from app.db import get_db
from app.models import Chat, Message, TelegramAccount
from app.schemas.analytics import (
    ChatInsightsResponse,
    ChatInsightsStatistics,
    ChatInsightSender,
    EmojiFrequency,
    ReactionAuthorPair,
    ReactionReactor,
    WordFrequency,
)
from app.telegram_parser import normalize_user_id

router = APIRouter()

SUPPORTED_CHAT_TYPES = ("personal_chat", "private_group", "private_supergroup")
ORDINARY_MESSAGE_TYPE = "message"
RANKING_LIMIT = 10
WORD_PATTERN = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)


@dataclass
class _SenderCounts:
    sender_id: str | None
    name: str | None
    message_count: int = 0
    text_length: int = 0
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
class _ChatCounts:
    chat_id: int
    account_id: int
    source_account_label: str
    title: str | None
    chat_type: str
    message_count: int = 0
    text_length: int = 0
    words: Counter[str] = field(default_factory=Counter)
    emojis: Counter[str] = field(default_factory=Counter)
    senders: dict[str | None, _SenderCounts] = field(default_factory=dict)
    reactions: Counter[str] = field(default_factory=Counter)
    reactors: dict[str, _ReactorCounts] = field(default_factory=dict)
    pairs: dict[tuple[str, str], _PairCounts] = field(default_factory=dict)
    sender_message_counts: Counter[str] = field(default_factory=Counter)


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
    index = 0
    while index < len(text):
        end = _emoji_end(text, index)
        if end is None:
            index += 1
            continue
        emojis.append(text[index:end])
        index = end
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


def _build_chat_statistics(counts: _ChatCounts) -> ChatInsightsStatistics:
    senders = [
        ChatInsightSender(
            sender_telegram_id=sender.sender_id,
            display_name=sender.name or (
                sender.sender_id if sender.sender_id is not None else "Unknown sender"
            ),
            message_count=sender.message_count,
            text_length=sender.text_length,
            popular_words=_rank_words(sender.words),
            popular_emojis=_rank_emojis(sender.emojis),
        )
        for sender in counts.senders.values()
    ]
    senders.sort(key=lambda sender: (-sender.message_count, sender.display_name.casefold()))

    reactors = [
        ReactionReactor(
            reactor_telegram_id=reactor.sender_id,
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
                reactor_telegram_id=pair.reactor_id,
                reactor_name=pair.reactor_name or pair.reactor_id,
                author_telegram_id=pair.author_id,
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
        source_account_label=counts.source_account_label,
        title=counts.title,
        chat_type=counts.chat_type,
        ordinary_message_count=counts.message_count,
        text_length=counts.text_length,
        popular_words=_rank_words(counts.words),
        popular_emojis=_rank_emojis(counts.emojis),
        senders=senders,
        reaction_count=sum(counts.reactions.values()),
        reaction_emojis=_rank_emojis(counts.reactions),
        reactors=reactors,
        reactor_author_pairs=pairs,
    )


@router.get(
    "/chat-insights",
    response_model=ChatInsightsResponse,
    summary="Get text and reaction analytics for private chats and groups",
    description=(
        "Returns per-chat message, text, word, emoji, and reaction statistics "
        "for personal chats, private groups, and private supergroups. Reaction "
        "totals use each message's full reaction count. Per-reactor and "
        "reactor-to-author statistics use only Telegram's recent reactor list "
        "and therefore represent observed coverage, not complete totals."
    ),
)
def get_chat_insights(db: Session = Depends(get_db)) -> ChatInsightsResponse:
    statement = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id,
            Chat.title,
            Chat.chat_type,
            TelegramAccount.username.label("account_username"),
            TelegramAccount.name.label("account_name"),
            Message.id.label("message_id"),
            Message.sender_telegram_id,
            Message.sender_name,
            Message.message_type,
            Message.text_content,
            Message.raw_payload,
        )
        .select_from(Chat)
        .join(TelegramAccount, TelegramAccount.id == Chat.account_id)
        .outerjoin(Message, Message.chat_id == Chat.id)
        .where(Chat.chat_type.in_(SUPPORTED_CHAT_TYPES))
        .order_by(Chat.id, Message.id)
    )

    chats: dict[int, _ChatCounts] = {}
    for row in db.execute(statement).yield_per(1000):
        chat = chats.get(row.chat_id)
        if chat is None:
            account_label = (
                f"@{row.account_username}" if row.account_username else row.account_name
            )
            chat = _ChatCounts(
                chat_id=row.chat_id,
                account_id=row.account_id,
                source_account_label=account_label,
                title=row.title,
                chat_type=row.chat_type,
            )
            chats[row.chat_id] = chat

        if row.message_id is None or row.message_type != ORDINARY_MESSAGE_TYPE:
            continue

        sender_id = row.sender_telegram_id
        sender = chat.senders.get(sender_id)
        if sender is None:
            sender = _SenderCounts(
                sender_id=sender_id,
                name=_clean_display_name(row.sender_name),
            )
            chat.senders[sender_id] = sender
        elif not sender.name:
            sender.name = _clean_display_name(row.sender_name)

        text = row.text_content or ""
        words = [word.casefold() for word in WORD_PATTERN.findall(text)]
        emojis = extract_emojis(text)
        chat.message_count += 1
        chat.text_length += len(text)
        chat.words.update(words)
        chat.emojis.update(emojis)
        sender.message_count += 1
        sender.text_length += len(text)
        sender.words.update(words)
        sender.emojis.update(emojis)

        if sender_id is not None:
            chat.sender_message_counts[sender_id] += 1

        for reaction in _reaction_records(row.raw_payload):
            if reaction.get("type") != "emoji":
                continue
            emoji = reaction.get("emoji")
            if not isinstance(emoji, str) or not emoji:
                continue
            count = _positive_count(reaction.get("count"))
            if count:
                chat.reactions[emoji] += count
            recent = reaction.get("recent")
            if not isinstance(recent, list):
                continue
            for recent_reaction in recent:
                if not isinstance(recent_reaction, dict):
                    continue
                reactor_id = normalize_user_id(recent_reaction.get("from_id"))
                if reactor_id is None:
                    continue
                reactor_name = _clean_display_name(recent_reaction.get("from"))
                reactor = chat.reactors.get(reactor_id)
                if reactor is None:
                    reactor = _ReactorCounts(
                        sender_id=reactor_id,
                        name=reactor_name,
                    )
                    chat.reactors[reactor_id] = reactor
                elif not reactor.name:
                    reactor.name = reactor_name
                reactor.reaction_count += 1
                reactor.emojis[emoji] += 1

                if sender_id is None:
                    continue
                pair_key = (reactor_id, sender_id)
                pair = chat.pairs.get(pair_key)
                if pair is None:
                    pair = _PairCounts(
                        reactor_id=reactor_id,
                        reactor_name=reactor.name,
                        author_id=sender_id,
                        author_name=sender.name,
                    )
                    chat.pairs[pair_key] = pair
                pair.reaction_count += 1
                pair.message_ids.add(row.message_id)

    return ChatInsightsResponse(
        chats=[_build_chat_statistics(chat) for chat in chats.values()]
    )
