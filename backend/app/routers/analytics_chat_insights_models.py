from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime


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
    sender_id: str | None
    is_outgoing: bool | None
    sender_name: str | None
    message_type: str
    message_date: datetime | None


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
