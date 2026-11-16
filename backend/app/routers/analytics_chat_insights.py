from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.constants import (
    ORDINARY_MESSAGE_TYPE,
    SUPPORTED_CHAT_TYPES,
    WORD_PATTERN,
)
from app.db import get_db
from app.models import Account, Chat, Message
from app.routers.analytics_chat_insights_helpers import (
    _ChatCounts,
    _ConversationMessage,
    _MessageTypeSenderCounts,
    _PairCounts,
    _ReactorCounts,
    _SenderCounts,
    _build_chat_statistics,
    _as_utc,
    _clean_display_name,
    _message_category,
    _positive_count,
    _reaction_records,
    extract_emojis,
)
from app.schemas.analytics import ChatInsightsResponse, SearchOption
from app.parsers.telegram_parser import normalize_user_id

router = APIRouter()


@router.get(
    "/chat-insights",
    response_model=ChatInsightsResponse,
    summary="Get text and reaction analytics for private chats and groups",
    description=(
        "Returns normalized message, text, word, emoji, and reaction statistics "
        "for one selected chat, or the most active eligible chat when no chat is "
        "selected. Lightweight options for all eligible chats are included for "
        "the picker. Statistics cover supported platforms, personal chats, private "
        "groups, and private supergroups. Reaction "
        "totals use each message's full reaction count. Per-reactor and "
        "reactor-to-author statistics use only reaction records present in the "
        "source payload and may not represent complete totals. Reply tempo "
        "requires an in-chat reply reference, two identified senders, and "
        "reliable non-negative timestamps. Average activity times and weekday "
        "and calendar-month counts use dated ordinary messages in UTC. "
        "Conversation sessions use a 12-hour gap between dated ordinary messages."
    ),
)
def get_chat_insights(
    db: Session = Depends(get_db),
    chat_id: Annotated[int | None, Query(gt=0)] = None,
) -> ChatInsightsResponse:
    ordinary_message_count = func.count(
        case((Message.message_type == ORDINARY_MESSAGE_TYPE, Message.id))
    )
    chat_id_page = (
        select(Chat.id)
        .join(Account, Account.id == Chat.account_id)
        .outerjoin(
            Message,
            and_(
                Message.chat_id == Chat.id,
                Message.platform == Chat.platform,
            ),
        )
        .where(
            Chat.platform == Account.platform,
            Chat.chat_type.in_(SUPPORTED_CHAT_TYPES),
        )
        .group_by(Chat.id)
    )
    if chat_id is not None:
        chat_id_page = chat_id_page.where(Chat.id == chat_id)
    else:
        chat_id_page = (
            chat_id_page
            .order_by(
                ordinary_message_count.desc(),
                Chat.title,
                Chat.id,
            )
            .limit(1)
        )
    option_rows = db.execute(
        select(
            Chat.id,
            Chat.platform,
            Chat.title,
            Chat.chat_type,
            Account.username,
            Account.name,
        )
        .join(Account, Account.id == Chat.account_id)
        .where(
            Chat.platform == Account.platform,
            Chat.chat_type.in_(SUPPORTED_CHAT_TYPES),
        )
        .outerjoin(
            Message,
            and_(
                Message.chat_id == Chat.id,
                Message.platform == Chat.platform,
            ),
        )
        .group_by(
            Chat.id,
            Chat.platform,
            Chat.title,
            Chat.chat_type,
            Account.username,
            Account.name,
        )
        .order_by(ordinary_message_count.desc(), Chat.title, Chat.id)
    )
    options = [
        SearchOption(
            value=str(row.id),
            label=row.title or "Untitled chat",
            platforms=[row.platform],
            search_terms=[
                row.chat_type,
                f"@{row.username}" if row.username else row.name,
                str(row.id),
            ],
        )
        for row in option_rows
    ]
    statement = (
        select(
            Chat.id.label("chat_id"),
            Chat.account_id,
            Chat.platform,
            Chat.title,
            Chat.chat_type,
            Account.username.label("account_username"),
            Account.name.label("account_name"),
            Message.id.label("message_id"),
            Message.message_id.label("source_message_id"),
            Message.sender_id,
            Message.sender_name,
            Message.message_type,
            Message.text_content,
            Message.message_date,
            func.coalesce(
                Message.source_reply_id,
                Message.reply_to_telegram_message_id,
            ).label("source_reply_id"),
            Message.raw_payload,
        )
        .select_from(Chat)
        .join(Account, Account.id == Chat.account_id)
        .outerjoin(
            Message,
            and_(
                Message.chat_id == Chat.id,
                Message.platform == Chat.platform,
            ),
        )
        .where(
            Chat.platform == Account.platform,
            Chat.chat_type.in_(SUPPORTED_CHAT_TYPES),
            Chat.id.in_(chat_id_page),
        )
        .order_by(Chat.id, Message.message_date, Message.id)
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
                platform=row.platform,
                source_account_label=account_label,
                title=row.title,
                chat_type=row.chat_type,
            )
            chats[row.chat_id] = chat

        sender_name = _clean_display_name(row.sender_name)
        sender_key: str | tuple[str, str] | None = row.sender_id
        statistics_sender_id = row.sender_id
        if (
            row.platform == "facebook"
            and row.chat_type == "personal_chat"
            and sender_name
        ):
            sender_key = ("facebook_personal_name", sender_name.casefold())
            statistics_sender_id = None
        elif (
            sender_key is None
            and row.platform == "instagram"
            and row.chat_type == "private_group"
            and sender_name
        ):
            sender_key = ("instagram_group_name", sender_name.casefold())

        if row.message_id is None or row.message_type != ORDINARY_MESSAGE_TYPE:
            if row.message_id is None:
                continue
            message_type = row.message_type or "unknown"
            text = row.text_content or ""
            category = _message_category(row.raw_payload, message_type, text)
            chat.message_type_counts[category] += 1
            if text:
                chat.with_text_counts[category] += 1
            type_senders = chat.message_type_senders.setdefault(category, {})
            type_sender = type_senders.get(sender_key)
            if type_sender is None:
                type_sender = _MessageTypeSenderCounts(
                    sender_id=statistics_sender_id,
                    name=(
                        sender_name
                        or row.sender_id
                        or "Unknown sender"
                    ),
                )
                type_senders[sender_key] = type_sender
            type_sender.count += 1
            chat.messages.append(
                _ConversationMessage(
                    message_id=row.message_id,
                    source_message_id=row.source_message_id,
                    sender_id=row.sender_id,
                    sender_name=sender_name,
                    message_type=message_type,
                    message_date=row.message_date,
                    reply_to_message_id=row.source_reply_id,
                )
            )
            continue

        text = row.text_content or ""
        category = _message_category(row.raw_payload, row.message_type, text)
        chat.message_type_counts[category] += 1
        if text:
            chat.with_text_counts[category] += 1
        type_senders = chat.message_type_senders.setdefault(category, {})
        type_sender = type_senders.get(sender_key)
        if type_sender is None:
            type_sender = _MessageTypeSenderCounts(
                sender_id=statistics_sender_id,
                name=(
                    sender_name
                    or row.sender_id
                    or "Unknown sender"
                ),
            )
            type_senders[sender_key] = type_sender
        type_sender.count += 1
        chat.messages.append(
            _ConversationMessage(
                message_id=row.message_id,
                source_message_id=row.source_message_id,
                sender_id=row.sender_id,
                sender_name=sender_name,
                message_type=row.message_type,
                message_date=row.message_date,
                reply_to_message_id=row.source_reply_id,
            )
        )

        sender_id = row.sender_id
        sender = chat.senders.get(sender_key)
        if sender is None:
            sender = _SenderCounts(
                sender_id=statistics_sender_id,
                name=sender_name,
            )
            chat.senders[sender_key] = sender
        elif not sender.name:
            sender.name = sender_name

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
        if row.message_date is not None:
            sender.activity_times.append(_as_utc(row.message_date))

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
        chats=[_build_chat_statistics(chat) for chat in chats.values()],
        options=options,
    )
